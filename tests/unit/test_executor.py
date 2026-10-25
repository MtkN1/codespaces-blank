import asyncio
import uuid
from typing import cast

import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.context import ServerCallContext
from a2a.server.events import EventQueue
from a2a.types import (
    Message,
    Part,
    Role,
    SendMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from google.protobuf.json_format import MessageToDict

from a2a_claude_agent.executor import ClaudeAgentExecutor
from a2a_claude_agent.session_store import InMemorySessionStore
from tests import fakes

TERMINAL = {
    TaskState.TASK_STATE_COMPLETED,
    TaskState.TASK_STATE_FAILED,
    TaskState.TASK_STATE_CANCELED,
    TaskState.TASK_STATE_REJECTED,
}


class RecordingQueue:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def enqueue_event(self, event: object) -> None:
        self.events.append(event)

    def states(self) -> list[str]:
        out = []
        for event in self.events:
            if isinstance(event, Task):
                out.append("task")
            elif isinstance(event, TaskStatusUpdateEvent):
                out.append(TaskState.Name(event.status.state).removeprefix("TASK_STATE_").lower())
            elif isinstance(event, TaskArtifactUpdateEvent):
                out.append("artifact")
        return out


def make_context(
    text: str = "2+3?",
    *,
    context_id: str = "ctx-1",
    task_id: str | None = None,
    task: Task | None = None,
) -> RequestContext:
    task_id = task_id or str(uuid.uuid4())
    message = Message(
        role=Role.ROLE_USER,
        message_id=str(uuid.uuid4()),
        parts=[Part(text=text)] if text else [Part(url="https://example.com/a.png")],
    )
    return RequestContext(
        call_context=ServerCallContext(),
        request=SendMessageRequest(message=message),
        task_id=task_id,
        context_id=context_id,
        task=task,
    )


async def execute(executor, context):
    queue = RecordingQueue()
    await executor.execute(context, cast(EventQueue, queue))
    return queue


def text_of(event) -> str:
    if isinstance(event, TaskArtifactUpdateEvent):
        return "".join(p.text for p in event.artifact.parts)
    return "".join(p.text for p in event.status.message.parts)


async def test_success_emits_task_working_artifact_completed():
    runner = fakes.FakeRunner(
        [
            fakes.init(),
            fakes.tool_use("Read", {"file_path": "a.txt"}),
            fakes.tool_result("Read"),
            fakes.assistant_text("5"),
            fakes.result("5"),
        ]
    )
    executor = ClaudeAgentExecutor(runner)
    context = make_context("2+3?")

    queue = await execute(executor, context)

    assert queue.states() == ["task", "working", "working", "artifact", "completed"]
    task = queue.events[0]
    assert task.id == context.task_id
    assert task.context_id == "ctx-1"
    assert task.status.state == TaskState.TASK_STATE_SUBMITTED
    assert text_of(queue.events[2]) == "Running tool: Read"
    artifact = queue.events[3]
    assert text_of(artifact) == "5"
    assert artifact.artifact.name == "response"
    assert artifact.last_chunk is True
    assert artifact.append is False
    completed = queue.events[4]
    metadata = MessageToDict(completed.metadata)
    assert metadata["claude"]["model_usage"][fakes.MODEL]["costUSD"] == 0.0003
    assert runner.calls == [("2+3?", None)]
    assert runner.closed == 1


async def test_every_event_belongs_to_the_task():
    executor = ClaudeAgentExecutor(fakes.FakeRunner(fakes.answer("ok")))
    context = make_context(context_id="ctx-x")

    queue = await execute(executor, context)

    for event in queue.events[1:]:
        assert event.task_id == context.task_id
        assert event.context_id == "ctx-x"


async def test_existing_task_is_not_enqueued_again():
    context_task = Task(
        id="task-1",
        context_id="ctx-1",
        status=TaskStatus(state=TaskState.TASK_STATE_INPUT_REQUIRED),
    )
    executor = ClaudeAgentExecutor(fakes.FakeRunner(fakes.answer("ok")))

    queue = await execute(executor, make_context(task_id="task-1", task=context_task))

    assert queue.states() == ["working", "artifact", "completed"]


async def test_error_result_fails_the_task():
    runner = fakes.FakeRunner(
        [fakes.init(), fakes.result(None, subtype="error_max_turns", is_error=True)]
    )

    queue = await execute(ClaudeAgentExecutor(runner), make_context())

    assert queue.states() == ["task", "working", "failed"]
    assert "error_max_turns" in text_of(queue.events[-1])


async def test_runner_exception_fails_the_task_without_raising():
    queue = await execute(ClaudeAgentExecutor(fakes.FailingRunner()), make_context())

    assert queue.states() == ["task", "working", "failed"]
    assert text_of(queue.events[-1]) == "Agent run failed (RuntimeError). See server logs."


async def test_stream_without_result_fails_the_task():
    runner = fakes.FakeRunner([fakes.init(), fakes.assistant_text("partial")])

    queue = await execute(ClaudeAgentExecutor(runner), make_context())

    assert queue.states() == ["task", "working", "working", "failed"]


async def test_non_text_message_is_rejected():
    runner = fakes.FakeRunner(fakes.answer("unused"))

    queue = await execute(ClaudeAgentExecutor(runner), make_context(""))

    assert queue.states() == ["task", "rejected"]
    assert runner.calls == []


async def test_same_context_resumes_the_saved_session():
    sessions = InMemorySessionStore()
    runner = fakes.FakeRunner(lambda _p, _r: fakes.FakeRun(fakes.answer("ok", "session-42")))
    executor = ClaudeAgentExecutor(runner, sessions)

    await execute(executor, make_context("first", context_id="ctx-a"))
    await execute(executor, make_context("second", context_id="ctx-a"))
    await execute(executor, make_context("other", context_id="ctx-b"))

    assert runner.calls == [("first", None), ("second", "session-42"), ("other", None)]
    assert await sessions.get("ctx-a") == "session-42"


async def test_session_is_saved_before_completion_is_reported():
    sessions = InMemorySessionStore()
    seen_at_completion = []

    class Queue(RecordingQueue):
        async def enqueue_event(self, event):
            if (
                isinstance(event, TaskStatusUpdateEvent)
                and event.status.state == TaskState.TASK_STATE_COMPLETED
            ):
                seen_at_completion.append(await sessions.get("ctx-1"))
            await super().enqueue_event(event)

    executor = ClaudeAgentExecutor(fakes.FakeRunner(fakes.answer("ok", "s-1")), sessions)
    await executor.execute(make_context(), cast(EventQueue, Queue()))

    assert seen_at_completion == ["s-1"]


async def test_failed_resume_forgets_the_session():
    sessions = InMemorySessionStore()
    await sessions.set("ctx-1", "stale-session")
    executor = ClaudeAgentExecutor(fakes.FailingRunner(), sessions)

    await execute(executor, make_context())

    assert await sessions.get("ctx-1") is None


async def test_same_context_runs_one_at_a_time_other_contexts_in_parallel():
    release = asyncio.Event()

    def factory(_prompt, _resume):
        run = fakes.FakeRun(fakes.answer("ok"))
        original = run.messages

        async def gated():
            await release.wait()
            async for message in original():
                yield message

        run.messages = gated
        return run

    runner = fakes.FakeRunner(factory)
    executor = ClaudeAgentExecutor(runner)

    same = [
        asyncio.create_task(execute(executor, make_context(context_id="ctx-same")))
        for _ in range(2)
    ]
    other = asyncio.create_task(execute(executor, make_context(context_id="ctx-other")))
    for _ in range(20):
        await asyncio.sleep(0)

    assert runner.active == 2  # one per context
    release.set()
    queues = await asyncio.gather(*same, other)

    assert runner.max_active == 2
    assert all(q.states()[-1] == "completed" for q in queues)


async def test_cancel_interrupts_the_run_and_publishes_canceled_last():
    runner = fakes.FakeRunner(
        lambda _p, _r: fakes.FakeRun([fakes.init(), fakes.assistant_text("counting")], hang=True)
    )
    executor = ClaudeAgentExecutor(runner)
    context = make_context("count to 1000")
    queue = RecordingQueue()

    execution = asyncio.create_task(executor.execute(context, cast(EventQueue, queue)))
    await runner.first_run_waiting()

    cancel_queue = RecordingQueue()
    await executor.cancel(context, cast(EventQueue, cancel_queue))

    assert runner.runs[0].interrupted.is_set()
    assert runner.closed == 1  # cleaned up before cancel() returned
    assert execution.done()
    await execution
    assert cancel_queue.states() == ["canceled"]
    # Nothing from the interrupted run (its error result) reaches the queue...
    assert queue.states() == ["task", "working"]
    # ...but its usage is reported with CANCELED.
    canceled = MessageToDict(cancel_queue.events[0].metadata)
    assert canceled["claude"]["terminal_reason"] == "aborted_streaming"
    assert list(canceled["claude"]["model_usage"]) == [fakes.MODEL]


async def test_cancel_disconnects_when_interrupt_fails():
    class StubbornRun(fakes.FakeRun):
        async def messages(self):
            self.waiting.set()
            while True:
                await asyncio.sleep(0.01)
                yield fakes.assistant_text("still going")

        async def interrupt(self):
            raise RuntimeError("CLI did not answer the interrupt")

    runner = fakes.FakeRunner(lambda _p, _r: StubbornRun([]))
    executor = ClaudeAgentExecutor(runner)
    context = make_context()
    queue = RecordingQueue()

    execution = asyncio.create_task(executor.execute(context, cast(EventQueue, queue)))
    await runner.first_run_waiting()
    cancel_queue = RecordingQueue()
    await executor.cancel(context, cast(EventQueue, cancel_queue))
    await execution

    assert runner.closed == 1
    assert cancel_queue.states() == ["canceled"]
    assert "completed" not in queue.states()


async def test_cancel_when_framework_cancels_execute_first():
    runner = fakes.FakeRunner(lambda _p, _r: fakes.FakeRun([fakes.init()], hang=True))
    executor = ClaudeAgentExecutor(runner)
    context = make_context()
    queue = RecordingQueue()

    execution = asyncio.create_task(executor.execute(context, cast(EventQueue, queue)))
    await runner.first_run_waiting()
    execution.cancel()
    with pytest.raises(asyncio.CancelledError):
        await execution

    cancel_queue = RecordingQueue()
    await executor.cancel(context, cast(EventQueue, cancel_queue))

    assert runner.closed == 1
    assert cancel_queue.states() == ["canceled"]


async def test_cancel_of_idle_task_publishes_canceled():
    executor = ClaudeAgentExecutor(fakes.FakeRunner([]))
    queue = RecordingQueue()

    await executor.cancel(make_context(task_id="idle"), cast(EventQueue, queue))

    assert queue.states() == ["canceled"]
    assert queue.events[0].task_id == "idle"


async def test_cancel_while_waiting_for_the_context_lock():
    release = asyncio.Event()

    def factory(_prompt, _resume):
        run = fakes.FakeRun(fakes.answer("ok"))
        original = run.messages

        async def gated():
            await release.wait()
            async for message in original():
                yield message

        run.messages = gated
        return run

    runner = fakes.FakeRunner(factory)
    executor = ClaudeAgentExecutor(runner)
    first = asyncio.create_task(execute(executor, make_context(context_id="ctx")))
    waiting_context = make_context(context_id="ctx")
    waiting = asyncio.create_task(execute(executor, waiting_context))
    for _ in range(20):
        await asyncio.sleep(0)

    cancel_queue = RecordingQueue()
    await executor.cancel(waiting_context, cast(EventQueue, cancel_queue))
    assert cancel_queue.states() == ["canceled"]

    release.set()
    assert (await first).states()[-1] == "completed"
    waiting_queue = await waiting
    # The cancelled request never started a run and emitted nothing after its Task.
    assert waiting_queue.states() == ["task"]
    assert len(runner.calls) == 1


async def test_finished_runs_are_forgotten():
    executor = ClaudeAgentExecutor(fakes.FakeRunner(fakes.answer("ok")))

    await execute(executor, make_context())

    assert executor._runs == {}


async def test_terminal_state_is_last_and_unique():
    executor = ClaudeAgentExecutor(fakes.FakeRunner(fakes.answer("ok")))

    queue = await execute(executor, make_context())

    terminal = [
        e
        for e in queue.events
        if isinstance(e, TaskStatusUpdateEvent) and e.status.state in TERMINAL
    ]
    assert terminal == [queue.events[-1]]
