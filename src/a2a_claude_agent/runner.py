"""Thin wrapper around the Claude Agent SDK, so tests can swap in a fake."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Protocol

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, Message

from a2a_claude_agent.config import Settings

logger = logging.getLogger(__name__)


class AgentRun(Protocol):
    """One prompt being answered by the Agent SDK."""

    def messages(self) -> AsyncGenerator[Message, None]:
        """Yield SDK messages up to and including the ``ResultMessage``."""
        ...

    async def interrupt(self) -> None:
        """Ask the running agent to stop as soon as possible."""
        ...


class ClaudeRunner(Protocol):
    """Starts Agent SDK runs. The context manager owns the run's resources."""

    def start(self, prompt: str, *, resume: str | None) -> AbstractAsyncContextManager[AgentRun]:
        """Start answering ``prompt``, continuing session ``resume`` if given.

        Leaving the context manager must release everything the run holds,
        including the CLI subprocess, whether the run finished or not.
        """
        ...


def build_options(settings: Settings, *, resume: str | None) -> ClaudeAgentOptions:
    """Agent SDK options for one run.

    Every value that could otherwise come from the CLI's defaults or from
    ``~/.claude`` / ``.claude`` settings is set explicitly here: the model, the
    tool set, the permission mode and the setting sources.
    """
    return ClaudeAgentOptions(
        model=settings.model,
        fallback_model=None,
        # Only these built-in tools exist for the agent.
        tools=settings.effective_tools,
        allowed_tools=settings.effective_allowed_tools,
        disallowed_tools=list(settings.disallowed_tools),
        # Deny anything that is not pre-approved instead of waiting for an answer.
        permission_mode=settings.permission_mode,
        system_prompt=settings.system_prompt,
        cwd=settings.resolved_cwd,
        max_turns=settings.max_turns,
        max_budget_usd=settings.max_budget_usd,
        # Do not read ~/.claude or ./.claude settings, which could change the
        # model, permissions or hooks behind our back.
        setting_sources=[],
        strict_mcp_config=True,
        skills=[],
        agents={},
        resume=resume,
        # Prompts come from remote callers: deliver them as written, so an
        # "@/path" mention cannot pull a local file into the context (which
        # bypasses tool permissions) and a leading "/" is not a slash command.
        verbatim_prompts=True,
        env={
            # Pin the model of any subagent too, in case one is ever enabled.
            "CLAUDE_CODE_SUBAGENT_MODEL": settings.model,
            "CLAUDE_AGENT_SDK_CLIENT_APP": "a2a-claude-agent/0.1.0",
        },
        stderr=_log_stderr,
    )


def _log_stderr(line: str) -> None:
    logger.debug("claude: %s", line.rstrip())


class _SDKRun:
    def __init__(self, client: ClaudeSDKClient) -> None:
        self._client = client

    async def messages(self) -> AsyncGenerator[Message, None]:
        async for message in self._client.receive_response():
            yield message

    async def interrupt(self) -> None:
        await self._client.interrupt()


class ClaudeSDKRunner:
    """Runs each prompt in its own ``ClaudeSDKClient`` (one CLI subprocess per run).

    The conversation is carried across runs through the session saved on disk
    by the CLI, using ``resume``.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def start(self, prompt: str, *, resume: str | None) -> AbstractAsyncContextManager[AgentRun]:
        return self._start(prompt, resume=resume)

    @asynccontextmanager
    async def _start(self, prompt: str, *, resume: str | None) -> AsyncIterator[AgentRun]:
        self._settings.resolved_cwd.mkdir(parents=True, exist_ok=True)
        client = ClaudeSDKClient(options=build_options(self._settings, resume=resume))
        # The SDK requires connect, receive and disconnect in the same task.
        await client.connect()
        try:
            await client.query(prompt)
            yield _SDKRun(client)
        finally:
            await client.disconnect()
