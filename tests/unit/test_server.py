"""The whole server (a2a-sdk handler and routes) with a fake runner, over ASGI."""

import uuid

import httpx
import pytest
from a2a.client import ClientConfig, create_client
from a2a.types import (
    CancelTaskRequest,
    GetTaskRequest,
    Message,
    Part,
    Role,
    SendMessageRequest,
    TaskState,
)
from google.protobuf.json_format import MessageToDict

from a2a_claude_agent.config import Settings
from a2a_claude_agent.server import create_app
from tests import fakes

BASE_URL = "http://agent.test"


def settings(tmp_path) -> Settings:
    return Settings(public_url=BASE_URL, cwd=tmp_path / "ws", agent_name="Test Agent")


@pytest.fixture
async def http(tmp_path):
    clients = []

    async def make(app):
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL)
        clients.append(client)
        return client

    yield make
    for client in clients:
        await client.aclose()


async def a2a_client(http_client, *, streaming=True, polling=False, binding="JSONRPC"):
    config = ClientConfig(
        httpx_client=http_client,
        streaming=streaming,
        polling=polling,
        supported_protocol_bindings=[binding],
    )
    return await create_client(BASE_URL, client_config=config)


def user_message(text: str, context_id: str | None = None) -> SendMessageRequest:
    return SendMessageRequest(
        message=Message(
            role=Role.ROLE_USER,
            message_id=str(uuid.uuid4()),
            parts=[Part(text=text)],
            context_id=context_id or "",
        )
    )


def kinds(events) -> list[str]:
    out = []
    for event in events:
        if event.HasField("task"):
            out.append("task")
        elif event.HasField("status_update"):
            name = TaskState.Name(event.status_update.status.state)
            out.append(name.removeprefix("TASK_STATE_").lower())
        elif event.HasField("artifact_update"):
            out.append("artifact")
        elif event.HasField("message"):
            out.append("message")
    return out


async def test_agent_card_is_served(tmp_path, http):
    client = await http(create_app(settings(tmp_path), runner=fakes.FakeRunner([])))

    response = await client.get("/.well-known/agent-card.json")

    assert response.status_code == 200
    card = response.json()
    assert card["name"] == "Test Agent"
    assert card["capabilities"]["streaming"] is True
    assert card["skills"][0]["id"] == "general"
    assert card["supportedInterfaces"][0]["url"] == f"{BASE_URL}/a2a/jsonrpc"


async def test_streaming_send_orders_task_working_artifact_completed(tmp_path, http):
    runner = fakes.FakeRunner(fakes.answer("5"))
    client = await a2a_client(await http(create_app(settings(tmp_path), runner=runner)))

    events = [e async for e in client.send_message(user_message("2+3?"))]

    assert kinds(events) == ["task", "working", "artifact", "completed"]
    assert events[2].artifact_update.artifact.parts[0].text == "5"


@pytest.mark.parametrize("binding", ["JSONRPC", "HTTP+JSON"])
async def test_non_streaming_send_returns_completed_task(tmp_path, http, binding):
    runner = fakes.FakeRunner(fakes.answer("5"))
    app = create_app(settings(tmp_path), runner=runner)
    client = await a2a_client(await http(app), streaming=False, binding=binding)

    events = [e async for e in client.send_message(user_message("2+3?"))]

    assert kinds(events) == ["task"]
    task = events[0].task
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert task.artifacts[0].parts[0].text == "5"
    usage = MessageToDict(task.metadata)["claude"]
    assert list(usage["model_usage"]) == [fakes.MODEL]


async def test_multi_turn_reuses_the_session_for_the_context(tmp_path, http):
    runner = fakes.FakeRunner(lambda _p, _r: fakes.FakeRun(fakes.answer("ok", "session-7")))
    client = await a2a_client(await http(create_app(settings(tmp_path), runner=runner)))

    first = [e async for e in client.send_message(user_message("remember X"))]
    context_id = first[0].task.context_id
    second = [e async for e in client.send_message(user_message("what?", context_id))]

    assert second[0].task.context_id == context_id
    assert second[0].task.id != first[0].task.id
    assert runner.calls == [("remember X", None), ("what?", "session-7")]


async def test_cancel_task(tmp_path, http):
    runner = fakes.FakeRunner(lambda _p, _r: fakes.FakeRun([fakes.init()], hang=True))
    client = await a2a_client(
        await http(create_app(settings(tmp_path), runner=runner)), streaming=False, polling=True
    )

    events = [e async for e in client.send_message(user_message("long job"))]
    task_id = events[0].task.id
    await runner.first_run_waiting()

    canceled = await client.cancel_task(CancelTaskRequest(id=task_id))

    assert canceled.status.state == TaskState.TASK_STATE_CANCELED
    assert runner.runs[0].interrupted.is_set()
    assert runner.closed == 1
    stored = await client.get_task(GetTaskRequest(id=task_id))
    assert stored.status.state == TaskState.TASK_STATE_CANCELED


async def test_runner_failure_fails_the_task(tmp_path, http):
    app = create_app(settings(tmp_path), runner=fakes.FailingRunner())
    client = await a2a_client(await http(app), streaming=False)

    events = [e async for e in client.send_message(user_message("hi"))]

    task = events[0].task
    assert task.status.state == TaskState.TASK_STATE_FAILED
    assert "RuntimeError" in task.status.message.parts[0].text
