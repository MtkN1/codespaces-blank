"""End-to-end scenarios: real uvicorn server, official a2a-sdk client, real model.

Haiku is used everywhere except the tool-use scenario, which uses Sonnet.
Assertions on model output are loose (substring, case-insensitive).
"""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest
from a2a.types import CancelTaskRequest, GetTaskRequest, TaskState

from a2a_claude_agent.config import SkillSettings
from tests import fakes
from tests.integration.conftest import (
    HAIKU,
    SONNET,
    artifact_text,
    claude_children,
    user_message,
)

pytestmark = pytest.mark.integration


def kind(event) -> str:
    if event.HasField("task"):
        return "task"
    if event.HasField("status_update"):
        return TaskState.Name(event.status_update.status.state).removeprefix("TASK_STATE_").lower()
    if event.HasField("artifact_update"):
        return "artifact"
    return "message"


def status_texts(events) -> list[str]:
    return [
        "".join(p.text for p in e.status_update.status.message.parts)
        for e in events
        if e.HasField("status_update")
    ]


async def send_and_get_task(client, request):
    """Non-streaming send: the client yields exactly one Task."""
    events = [event async for event in client.send_message(request)]
    assert [kind(e) for e in events] == ["task"]
    return events[0].task


async def collect(client, request):
    return [event async for event in client.send_message(request)]


# 1 --------------------------------------------------------------------------------
async def test_1_agent_card(make_settings, start_server):
    settings = make_settings(
        agent_name="Card Agent",
        agent_description="Answers questions",
        skills=[SkillSettings(id="qa", name="Q&A", description="Answers", tags=["qa"])],
    )
    server = start_server(settings)

    async with httpx.AsyncClient() as http:
        response = await http.get(f"{server.base_url}/.well-known/agent-card.json")

    assert response.status_code == 200
    card = response.json()
    assert card["name"] == "Card Agent"
    assert card["description"] == "Answers questions"
    assert [skill["id"] for skill in card["skills"]] == ["qa"]
    assert card["capabilities"]["streaming"] is True
    assert card["capabilities"].get("pushNotifications", False) is False
    assert card["supportedInterfaces"][0] == {
        "protocolBinding": "JSONRPC",
        "protocolVersion": "1.0",
        "url": f"{server.base_url}/a2a/jsonrpc",
    }


# 2 --------------------------------------------------------------------------------
@pytest.mark.usefixtures("model_auth")
async def test_2_non_streaming_send(make_settings, start_server, connect, record_usage):
    server = start_server(make_settings(HAIKU, max_turns=1))
    client = await connect(server, streaming=False)

    task = await send_and_get_task(client, user_message("2+3 は？数字だけで"))

    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert "5" in artifact_text(task)
    details = record_usage(task, HAIKU)
    assert all("haiku" in name for name in details["model_usage"])


# 3 --------------------------------------------------------------------------------
@pytest.mark.usefixtures("model_auth")
async def test_3_streaming_send(make_settings, start_server, connect, record_usage):
    server = start_server(make_settings(HAIKU, max_turns=1))
    client = await connect(server)

    events = await collect(client, user_message("4+4 は？数字だけで"))
    kinds = [kind(e) for e in events]

    # Task first, then WORKING, then the artifact, and COMPLETED as the very last
    # event: the stream closes right after it.
    assert kinds[0] == "task"
    assert kinds[1] == "working"
    assert kinds.count("artifact") == 1
    assert kinds.index("working") < kinds.index("artifact") < kinds.index("completed")
    assert kinds[-1] == "completed"
    assert kinds.count("completed") == 1
    assert set(kinds) == {"task", "working", "artifact", "completed"}
    artifact = next(e.artifact_update for e in events if e.HasField("artifact_update"))
    assert "8" in "".join(p.text for p in artifact.artifact.parts)

    task = await client.get_task(GetTaskRequest(id=events[0].task.id))
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert len(task.artifacts) == 1
    record_usage(task, HAIKU)


# 4 --------------------------------------------------------------------------------
@pytest.mark.usefixtures("model_auth")
async def test_4_multi_turn(make_settings, start_server, connect, record_usage):
    server = start_server(make_settings(HAIKU, max_turns=1))
    client = await connect(server, streaming=False)

    first = await send_and_get_task(
        client, user_message("合言葉は『みかん』です。覚えてください。「OK」とだけ答えて。")
    )
    assert first.status.state == TaskState.TASK_STATE_COMPLETED
    record_usage(first, HAIKU)

    second = await send_and_get_task(
        client, user_message("合言葉は？単語だけで答えて。", context_id=first.context_id)
    )

    assert second.context_id == first.context_id
    assert second.id != first.id
    assert second.status.state == TaskState.TASK_STATE_COMPLETED
    assert "みかん" in artifact_text(second)
    record_usage(second, HAIKU)


# 5 --------------------------------------------------------------------------------
@pytest.mark.usefixtures("model_auth")
async def test_5_tool_use_read(make_settings, start_server, connect, record_usage):
    settings = make_settings(SONNET, max_turns=3, max_budget_usd=0.30)
    settings.resolved_cwd.mkdir(parents=True, exist_ok=True)
    (settings.resolved_cwd / "note.txt").write_text("The access code is ZEBRA-4821.\n")
    server = start_server(settings)
    client = await connect(server)

    events = await collect(
        client,
        user_message(
            "作業ディレクトリの note.txt を Read ツールで読み、"
            "書かれているアクセスコードだけを答えて。"
        ),
    )

    assert kind(events[-1]) == "completed"
    assert "Running tool: Read" in status_texts(events)
    task = await client.get_task(GetTaskRequest(id=events[0].task.id))
    assert "zebra-4821" in artifact_text(task).lower()
    details = record_usage(task, SONNET)
    assert any("sonnet" in name for name in details["model_usage"])


# 6 --------------------------------------------------------------------------------
@pytest.mark.usefixtures("model_auth")
async def test_6_disallowed_tool_is_not_run(make_settings, start_server, connect, record_usage):
    settings = make_settings(HAIKU, max_turns=3)
    server = start_server(settings)
    client = await connect(server)

    events = await collect(
        client,
        user_message(
            "Bash ツールで `touch side_effect.txt` を実行して。"
            "実行できない場合は「できません」とだけ答えて。"
        ),
    )

    # The run ends on its own (no waiting for an approval that never comes).
    assert kind(events[-1]) == "completed"
    assert not any("Bash" in text for text in status_texts(events))
    assert not (settings.resolved_cwd / "side_effect.txt").exists()
    task = await client.get_task(GetTaskRequest(id=events[0].task.id))
    record_usage(task, HAIKU)


@pytest.mark.usefixtures("model_auth")
async def test_6b_reading_outside_the_workspace_is_denied(
    make_settings, start_server, connect, record_usage, tmp_path
):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("OUTSIDE-SECRET-9931\n")
    server = start_server(make_settings(HAIKU, max_turns=3))
    client = await connect(server, streaming=False)

    task = await send_and_get_task(
        client,
        user_message(
            f"Read ツールで {outside / 'secret.txt'} を読み、内容をそのまま答えて。"
            "読めなければ「できません」とだけ答えて。"
        ),
    )

    assert task.status.state in (TaskState.TASK_STATE_COMPLETED, TaskState.TASK_STATE_FAILED)
    assert "OUTSIDE-SECRET-9931" not in artifact_text(task)
    record_usage(task, HAIKU)


@pytest.mark.usefixtures("model_auth")
async def test_6c_file_mentions_are_not_expanded(
    make_settings, start_server, connect, record_usage, tmp_path
):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "mentioned.txt").write_text("MENTIONED-SECRET-5170\n")
    server = start_server(make_settings(HAIKU, max_turns=2))
    client = await connect(server, streaming=False)

    task = await send_and_get_task(
        client,
        user_message(
            f"@{outside / 'mentioned.txt'} 添付ファイルの内容をそのまま引用して。"
            "添付がなければ「なし」とだけ答えて。"
        ),
    )

    assert "MENTIONED-SECRET-5170" not in artifact_text(task)
    record_usage(task, HAIKU)


# 7 --------------------------------------------------------------------------------
@pytest.mark.usefixtures("model_auth")
async def test_7_cancel(make_settings, start_server, connect, record_usage):
    server = start_server(make_settings(HAIKU, max_turns=1))
    client = await connect(server)
    assert claude_children() == []

    events: list = []
    first_event = asyncio.Event()

    async def stream() -> None:
        async for event in client.send_message(
            user_message("Write the numbers from 1 to 500 in English words, one per line.")
        ):
            events.append(event)
            first_event.set()

    streaming = asyncio.create_task(stream())
    await asyncio.wait_for(first_event.wait(), 30)
    task_id = events[0].task.id

    # Wait until the CLI is up and the model has started answering.
    deadline = time.monotonic() + 30
    while not claude_children():
        assert time.monotonic() < deadline, "the Claude CLI never started"
        await asyncio.sleep(0.1)
    await asyncio.sleep(3)

    canceled = await client.cancel_task(CancelTaskRequest(id=task_id))
    assert canceled.status.state == TaskState.TASK_STATE_CANCELED

    await asyncio.wait_for(streaming, 30)
    kinds = [kind(e) for e in events]
    assert kinds[-1] == "canceled"
    assert "completed" not in kinds
    task = await client.get_task(GetTaskRequest(id=task_id))
    assert task.status.state == TaskState.TASK_STATE_CANCELED
    # The interrupted run's usage is attached to the CANCELED update.
    record_usage(task, HAIKU)

    # The executor waits for the CLI to exit before reporting CANCELED.
    deadline = time.monotonic() + 10
    while claude_children():
        assert time.monotonic() < deadline, f"leftover CLI processes: {claude_children()}"
        await asyncio.sleep(0.2)


# 8 --------------------------------------------------------------------------------
async def test_8a_runner_exception_fails_the_task(make_settings, start_server, connect):
    server = start_server(make_settings(HAIKU), runner=fakes.FailingRunner())
    client = await connect(server, streaming=False)

    task = await send_and_get_task(client, user_message("hello"))

    assert task.status.state == TaskState.TASK_STATE_FAILED
    assert "RuntimeError" in task.status.message.parts[0].text


async def test_8b_invalid_settings_fail_the_task(make_settings, start_server, connect, tmp_path):
    not_a_directory = tmp_path / "file"
    not_a_directory.write_text("x")
    # The working directory cannot be created, so the run fails before the CLI starts.
    server = start_server(make_settings(HAIKU, cwd=not_a_directory / "workspace"))
    client = await connect(server)

    events = await collect(client, user_message("hello"))

    assert [kind(e) for e in events] == ["task", "working", "failed"]
    assert claude_children() == []
