"""Fake Agent SDK runs and message builders shared by the tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Callable, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    Message,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

MODEL = "claude-haiku-5-5"


def init(session_id: str = "session-1") -> SystemMessage:
    return SystemMessage(subtype="init", data={"session_id": session_id, "model": MODEL})


def assistant_text(text: str, session_id: str = "session-1") -> AssistantMessage:
    return AssistantMessage(content=[TextBlock(text=text)], model=MODEL, session_id=session_id)


def tool_use(name: str, tool_input: dict[str, Any] | None = None) -> AssistantMessage:
    return AssistantMessage(
        content=[ToolUseBlock(id=f"toolu_{name}", name=name, input=tool_input or {})],
        model=MODEL,
    )


def tool_result(name: str, content: str = "secret file content") -> UserMessage:
    return UserMessage(content=[ToolResultBlock(tool_use_id=f"toolu_{name}", content=content)])


def result(
    text: str | None = "done",
    *,
    session_id: str = "session-1",
    subtype: str = "success",
    is_error: bool = False,
    errors: list[str] | None = None,
    terminal_reason: str | None = "completed",
) -> ResultMessage:
    return ResultMessage(
        subtype=subtype,
        duration_ms=1200,
        duration_api_ms=1000,
        is_error=is_error,
        num_turns=1,
        session_id=session_id,
        stop_reason="end_turn",
        total_cost_usd=0.0003,
        usage={"input_tokens": 10, "output_tokens": 3},
        result=text,
        model_usage={
            MODEL: {
                "inputTokens": 10,
                "outputTokens": 3,
                "cacheReadInputTokens": 0,
                "cacheCreationInputTokens": 0,
                "webSearchRequests": 0,
                "costUSD": 0.0003,
                "contextWindow": 200000,
                "maxOutputTokens": 8192,
            }
        },
        errors=errors,
        terminal_reason=terminal_reason,
    )


def answer(text: str, session_id: str = "session-1") -> list[Message]:
    """A one-turn successful run."""
    return [init(session_id), assistant_text(text, session_id), result(text, session_id=session_id)]


class FakeRun:
    """Plays back ``script``. With ``hang=True`` it then waits for ``interrupt()``."""

    def __init__(self, script: Sequence[Message], *, hang: bool = False) -> None:
        self.script = list(script)
        self.hang = hang
        self.interrupted = asyncio.Event()
        self.waiting = asyncio.Event()
        """Set once the run has played its script and is waiting to be interrupted."""

    async def messages(self) -> AsyncGenerator[Message, None]:
        for message in self.script:
            await asyncio.sleep(0)
            yield message
        if self.hang:
            self.waiting.set()
            await self.interrupted.wait()
            yield result(
                "",
                subtype="error_during_execution",
                is_error=True,
                terminal_reason="aborted_streaming",
            )

    async def interrupt(self) -> None:
        self.interrupted.set()


RunFactory = Callable[[str, str | None], FakeRun]


class FakeRunner:
    """Records each ``start()`` and hands out runs from ``factory``."""

    def __init__(self, factory: RunFactory | Sequence[Message]) -> None:
        if callable(factory):
            self._factory: RunFactory = factory
        else:
            script = list(factory)
            self._factory = lambda _prompt, _resume: FakeRun(script)
        self.calls: list[tuple[str, str | None]] = []
        self.runs: list[FakeRun] = []
        self.active = 0
        self.max_active = 0
        self.closed = 0
        self.started = asyncio.Event()

    async def first_run_waiting(self) -> FakeRun:
        """Wait until the first run has played its script and hangs."""
        await self.started.wait()
        await self.runs[0].waiting.wait()
        return self.runs[0]

    def start(self, prompt: str, *, resume: str | None) -> AbstractAsyncContextManager[FakeRun]:
        return self._start(prompt, resume)

    @asynccontextmanager
    async def _start(self, prompt: str, resume: str | None) -> AsyncIterator[FakeRun]:
        self.calls.append((prompt, resume))
        run = self._factory(prompt, resume)
        self.runs.append(run)
        self.started.set()
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            yield run
        finally:
            self.active -= 1
            self.closed += 1


class FailingRunner:
    """A runner whose ``start()`` raises, like a CLI that cannot be launched."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error or RuntimeError("cannot start the Claude CLI")

    def start(self, prompt: str, *, resume: str | None) -> AbstractAsyncContextManager[FakeRun]:
        return self._start()

    @asynccontextmanager
    async def _start(self) -> AsyncIterator[FakeRun]:
        raise self.error
        yield  # pragma: no cover
