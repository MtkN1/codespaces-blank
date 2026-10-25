"""Fixtures for tests that call the real model through the Claude Agent SDK.

Run with ``uv run pytest -m integration``. The tests are skipped when the
Claude CLI is not authenticated. They only use Haiku and Sonnet: every model
name is checked before use and every task's per-model usage is checked after.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import claude_agent_sdk
import httpx
import psutil
import pytest
import uvicorn
from a2a.client import Client, ClientConfig, create_client
from a2a.types import Message, Part, Role, SendMessageRequest, Task, TaskState
from google.protobuf.json_format import MessageToDict

from a2a_claude_agent.config import Settings
from a2a_claude_agent.runner import ClaudeRunner
from a2a_claude_agent.server import create_app

HAIKU = os.environ.get("A2A_TEST_HAIKU_MODEL", "haiku")
SONNET = os.environ.get("A2A_TEST_SONNET_MODEL", "sonnet")
FORBIDDEN_MODEL_FAMILY = "opus"


def guard_model(name: str) -> str:
    """Fail at once if a test is about to use an Opus model."""
    if FORBIDDEN_MODEL_FAMILY in name.lower():
        pytest.fail(f"Refusing to use model {name!r}: integration tests must not use Opus")
    return name


# --- Authentication -----------------------------------------------------------


def _cli_path() -> str | None:
    bundled = Path(claude_agent_sdk.__file__).parent / "_bundled" / "claude"
    if bundled.exists():
        return str(bundled)
    return shutil.which("claude")


def _cli_is_authenticated() -> bool:
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    if any(
        os.environ.get(flag)
        for flag in ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")
    ):
        return True
    cli = _cli_path()
    if cli is None:
        return False
    try:
        out = subprocess.run(
            [cli, "auth", "status"], capture_output=True, text=True, timeout=30, check=False
        )
        return bool(json.loads(out.stdout).get("loggedIn"))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


@pytest.fixture(scope="session", autouse=True)
def _no_opus_configured() -> None:
    guard_model(HAIKU)
    guard_model(SONNET)
    guard_model(os.environ.get("A2A_CLAUDE_MODEL", ""))


@pytest.fixture(scope="session")
def _authenticated() -> bool:
    return _cli_is_authenticated()


@pytest.fixture
def model_auth(_authenticated: bool) -> None:
    """Skip a test that calls the model when the CLI is not authenticated."""
    if not _authenticated:
        pytest.skip("Claude CLI is not authenticated (no API key, provider or login)")


# --- Usage bookkeeping ----------------------------------------------------------


@dataclass
class UsageRecord:
    test: str
    configured_model: str
    task_state: str
    total_cost_usd: float | None
    models: dict[str, Any] = field(default_factory=dict)


USAGE: list[UsageRecord] = []


def claude_metadata(task: Task) -> dict[str, Any]:
    return MessageToDict(task.metadata).get("claude", {})


@pytest.fixture
def record_usage(request) -> Callable[[Task, str], dict[str, Any]]:
    """Record a task's usage and assert that no Opus model served it."""

    def record(task: Task, configured_model: str) -> dict[str, Any]:
        details = claude_metadata(task)
        models = details.get("model_usage", {})
        USAGE.append(
            UsageRecord(
                test=request.node.name,
                configured_model=configured_model,
                task_state=TaskState.Name(task.status.state),
                total_cost_usd=details.get("total_cost_usd"),
                models=models,
            )
        )
        for model_name in models:
            assert FORBIDDEN_MODEL_FAMILY not in model_name.lower(), f"Opus was used: {models}"
        return details

    return record


def pytest_terminal_summary(terminalreporter) -> None:
    if not USAGE:
        return
    terminalreporter.section("model usage (integration)")
    total = 0.0
    for rec in USAGE:
        cost = rec.total_cost_usd or 0.0
        total += cost
        per_model = ", ".join(
            f"{name}: in={u.get('inputTokens')} out={u.get('outputTokens')} "
            f"cache_read={u.get('cacheReadInputTokens')} "
            f"cache_write={u.get('cacheCreationInputTokens')}"
            for name, u in rec.models.items()
        )
        terminalreporter.write_line(
            f"{rec.test}: model={rec.configured_model} state={rec.task_state} "
            f"cost=${cost:.5f} [{per_model}]"
        )
    terminalreporter.write_line(f"total reported cost: ${total:.5f}")
    report = os.environ.get("A2A_TEST_USAGE_FILE")
    if report:
        Path(report).write_text(
            json.dumps([rec.__dict__ for rec in USAGE], indent=2, ensure_ascii=False)
        )


# --- Server ------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@dataclass
class RunningServer:
    base_url: str
    settings: Settings


@pytest.fixture
def make_settings(tmp_path) -> Callable[..., Settings]:
    def make(model: str = HAIKU, **overrides: Any) -> Settings:
        port = _free_port()
        values: dict[str, Any] = {
            "model": guard_model(model),
            "host": "127.0.0.1",
            "port": port,
            "cwd": tmp_path / "workspace",
            "max_turns": 3,
            "max_budget_usd": 0.10,
            "agent_name": "Integration Test Agent",
        }
        values.update(overrides)
        return Settings(**values)

    return make


@pytest.fixture
def start_server() -> Iterator[Callable[..., RunningServer]]:
    """Start uvicorn in a background thread on a free port."""
    servers: list[tuple[uvicorn.Server, threading.Thread]] = []

    def start(settings: Settings, runner: ClaudeRunner | None = None) -> RunningServer:
        app = create_app(settings, runner=runner)
        config = uvicorn.Config(
            app, host=settings.host, port=settings.port, log_level="warning", lifespan="on"
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 15
        while not server.started:
            if time.monotonic() > deadline or not thread.is_alive():
                raise RuntimeError("uvicorn did not start")
            time.sleep(0.05)
        servers.append((server, thread))
        return RunningServer(base_url=f"http://{settings.host}:{settings.port}", settings=settings)

    yield start
    for server, thread in servers:
        server.should_exit = True
        thread.join(timeout=30)


# --- Client ------------------------------------------------------------------------


@pytest.fixture
async def connect() -> Any:
    """Create official a2a-sdk clients for a running server."""
    http_clients: list[httpx.AsyncClient] = []
    a2a_clients: list[Client] = []

    async def make(server: RunningServer, *, streaming: bool = True) -> Client:
        http_client = httpx.AsyncClient(timeout=httpx.Timeout(180.0))
        http_clients.append(http_client)
        client = await create_client(
            server.base_url,
            client_config=ClientConfig(httpx_client=http_client, streaming=streaming),
        )
        a2a_clients.append(client)
        return client

    yield make
    for client in a2a_clients:
        await client.close()
    for http_client in http_clients:
        await http_client.aclose()


def user_message(text: str, context_id: str | None = None) -> SendMessageRequest:
    return SendMessageRequest(
        message=Message(
            role=Role.ROLE_USER,
            message_id=str(uuid.uuid4()),
            parts=[Part(text=text)],
            context_id=context_id or "",
        )
    )


def artifact_text(task: Task) -> str:
    return "\n".join(part.text for artifact in task.artifacts for part in artifact.parts)


# --- Subprocesses ---------------------------------------------------------------------


def claude_children() -> list[int]:
    """PIDs of live Claude CLI processes started by this test process."""
    found = []
    for child in psutil.Process().children(recursive=True):
        try:
            if "claude" in child.name() and child.status() != psutil.STATUS_ZOMBIE:
                found.append(child.pid)
        except psutil.NoSuchProcess:
            continue
    return found


@pytest.fixture(scope="session", autouse=True)
def _no_leftover_subprocesses() -> Iterator[None]:
    yield
    deadline = time.monotonic() + 15
    while claude_children() and time.monotonic() < deadline:
        time.sleep(0.2)
    assert claude_children() == [], "Claude CLI subprocesses were left running"
