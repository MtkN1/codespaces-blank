"""``AgentExecutor`` that answers A2A messages with the Claude Agent SDK."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import aclosing, asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, Task, TaskState, TaskStatus

from a2a_claude_agent.event_mapper import (
    Completed,
    EventMapper,
    Failed,
    FinalAnswer,
    Progress,
    Update,
)
from a2a_claude_agent.runner import AgentRun, ClaudeRunner
from a2a_claude_agent.session_store import InMemorySessionStore, SessionStore

logger = logging.getLogger(__name__)

ARTIFACT_NAME = "response"


@dataclass
class _TaskRun:
    """State of one ``execute()`` call, shared with ``cancel()`` for the same task."""

    run: AgentRun | None = None
    started: bool = False
    """The Agent SDK run has been started (it may still be connecting)."""
    cancel_requested: bool = False
    terminal: bool = False
    """A terminal state has been published, by ``execute()`` or ``cancel()``."""
    interrupt_failed: bool = False
    result_metadata: dict[str, Any] | None = None
    """Usage of the run, reported with ``CANCELED`` when the run was interrupted."""
    done: asyncio.Event = field(default_factory=asyncio.Event)
    """``execute()`` has stopped the run and released its resources."""


class _KeyedLocks:
    """One ``asyncio.Lock`` per key, dropped when nobody holds or waits for it."""

    def __init__(self) -> None:
        self._locks: dict[str, tuple[asyncio.Lock, int]] = {}

    @asynccontextmanager
    async def hold(self, key: str) -> AsyncIterator[None]:
        lock, users = self._locks.get(key, (asyncio.Lock(), 0))
        self._locks[key] = (lock, users + 1)
        try:
            async with lock:
                yield
        finally:
            lock, users = self._locks[key]
            if users == 1:
                del self._locks[key]
            else:
                self._locks[key] = (lock, users - 1)


class ClaudeAgentExecutor(AgentExecutor):
    """Runs each A2A message through the Agent SDK and reports it as a task.

    - Every message gets a task. The ``Task`` is enqueued first, then status
      and artifact updates follow, so streaming always uses the
      "Task first" pattern.
    - Messages in the same ``contextId`` continue the same Agent SDK session
      (looked up in ``session_store``) and run one at a time. Different
      contexts run concurrently.
    - ``cancel()`` interrupts the running agent, waits for its subprocess to
      exit and publishes ``CANCELED``.
    """

    def __init__(
        self,
        runner: ClaudeRunner,
        session_store: SessionStore | None = None,
        *,
        interrupt_timeout: float = 5.0,
        cancel_timeout: float = 15.0,
    ) -> None:
        self._runner = runner
        self._sessions = session_store if session_store is not None else InMemorySessionStore()
        self._interrupt_timeout = interrupt_timeout
        self._cancel_timeout = cancel_timeout
        self._runs: dict[str, _TaskRun] = {}
        self._context_locks = _KeyedLocks()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        message = context.message
        task_id = context.task_id
        context_id = context.context_id
        if message is None or not task_id or not context_id:
            raise ValueError("RequestContext must carry a message, a task ID and a context ID")

        if context.current_task is None:
            await event_queue.enqueue_event(
                Task(
                    id=task_id,
                    context_id=context_id,
                    status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
                    history=[message],
                )
            )

        updater = TaskUpdater(event_queue=event_queue, task_id=task_id, context_id=context_id)
        state = _TaskRun()
        self._runs[task_id] = state
        try:
            async with self._context_locks.hold(context_id):
                if not state.cancel_requested:
                    await self._run(context.get_user_input(), context_id, updater, state)
        finally:
            state.done.set()
            if self._runs.get(task_id) is state:
                del self._runs[task_id]

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id
        if not task_id:
            raise ValueError("RequestContext must carry a task ID")
        context_id = context.context_id or (
            context.current_task.context_id if context.current_task else ""
        )

        state = self._runs.get(task_id)
        if state is not None:
            if state.terminal:
                return
            state.cancel_requested = True
            if state.started:
                await self._stop_run(task_id, state)
            if state.terminal:
                return
            state.terminal = True

        updater = TaskUpdater(event_queue=event_queue, task_id=task_id, context_id=context_id)
        await updater.update_status(
            TaskState.TASK_STATE_CANCELED,
            metadata=state.result_metadata if state is not None else None,
        )

    async def _stop_run(self, task_id: str, state: _TaskRun) -> None:
        """Interrupt the agent and wait until ``execute()`` has cleaned up."""
        if state.run is not None:
            try:
                await asyncio.wait_for(state.run.interrupt(), self._interrupt_timeout)
            except Exception:
                logger.warning("Interrupting task %s failed", task_id, exc_info=True)
                # Stop reading so execute() disconnects, which ends the CLI.
                state.interrupt_failed = True
        try:
            await asyncio.wait_for(state.done.wait(), self._cancel_timeout)
        except TimeoutError:
            # The framework cancels execute() next, which still disconnects.
            logger.warning("Task %s did not stop within %.0fs", task_id, self._cancel_timeout)

    async def _run(
        self, prompt: str, context_id: str, updater: TaskUpdater, state: _TaskRun
    ) -> None:
        prompt = prompt.strip()
        if not prompt:
            state.terminal = True
            await updater.reject(
                updater.new_agent_message([Part(text="Only text input is supported.")])
            )
            return

        await updater.start_work()
        mapper = EventMapper()
        resume = await self._sessions.get(context_id)
        saved_session = resume
        try:
            state.started = True
            async with self._runner.start(prompt, resume=resume) as run:
                state.run = run
                if not state.cancel_requested:
                    async with aclosing(run.messages()) as messages:
                        async for sdk_message in messages:
                            updates = mapper.on_message(sdk_message)
                            if mapper.session_id and mapper.session_id != saved_session:
                                # Save before reporting completion, so the next
                                # message in this context can resume.
                                await self._sessions.set(context_id, mapper.session_id)
                                saved_session = mapper.session_id
                            await self._apply(updates, updater, state)
                            if state.cancel_requested and state.interrupt_failed:
                                break
                            # After a successful interrupt the CLI still sends a
                            # (failed) result, which carries the usage so far.
                state.run = None
                state.result_metadata = mapper.result_metadata
            if not state.cancel_requested:
                await self._apply(mapper.on_stream_end(), updater, state)
        except Exception as exc:
            logger.exception("Agent run for context %s failed", context_id)
            if resume is not None and mapper.session_id is None:
                # The session could not be resumed; start afresh next time.
                await self._sessions.delete(context_id)
            await self._apply(
                mapper.on_error(f"Agent run failed ({type(exc).__name__}). See server logs."),
                updater,
                state,
            )

    async def _apply(self, updates: list[Update], updater: TaskUpdater, state: _TaskRun) -> None:
        for update in updates:
            if state.cancel_requested or state.terminal:
                return
            match update:
                case Progress(text=text, metadata=metadata):
                    await updater.start_work(
                        updater.new_agent_message([Part(text=text)], metadata=metadata)
                    )
                case FinalAnswer(text=text):
                    await updater.add_artifact(
                        [Part(text=text)], name=ARTIFACT_NAME, last_chunk=True
                    )
                case Completed(metadata=metadata):
                    state.terminal = True
                    await updater.update_status(
                        TaskState.TASK_STATE_COMPLETED, metadata=metadata or None
                    )
                case Failed(text=text, metadata=metadata):
                    state.terminal = True
                    await updater.update_status(
                        TaskState.TASK_STATE_FAILED,
                        message=updater.new_agent_message([Part(text=text)]),
                        metadata=metadata or None,
                    )
