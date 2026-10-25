"""Translate Claude Agent SDK messages into A2A task updates.

:class:`EventMapper` is pure: it only turns SDK messages into a list of
:data:`Update` values. The executor applies them to the task with
``TaskUpdater``, so the mapping can be tested without an event queue.

Mapping rules:

- Assistant text is held back until the next message shows whether it was the
  final answer. Text followed by a tool call or tool result becomes a
  ``WORKING`` status message (:class:`Progress`); text followed by the result
  becomes the artifact (:class:`FinalAnswer`).
- A tool call becomes a ``WORKING`` status message naming the tool only. Tool
  inputs and results are never forwarded.
- A successful ``ResultMessage`` ends the run with :class:`FinalAnswer` and
  :class:`Completed`; any other result ends it with :class:`Failed`. Usage and
  cost go into the final update's metadata.
- Nothing is produced after the run has ended.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    Message,
    ResultMessage,
    ServerToolUseBlock,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
)

METADATA_KEY = "claude"
"""Key under which run details are stored in the task's metadata."""


@dataclass(frozen=True)
class Progress:
    """Intermediate text, sent as a ``WORKING`` status message."""

    text: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class FinalAnswer:
    """The final answer, sent as the task's artifact."""

    text: str


@dataclass(frozen=True)
class Completed:
    """The run succeeded: move the task to ``COMPLETED``."""

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Failed:
    """The run failed: move the task to ``FAILED`` with an explanation."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


Update = Progress | FinalAnswer | Completed | Failed


def tool_progress_text(tool_name: str) -> str:
    return f"Running tool: {tool_name}"


def result_metadata(result: ResultMessage) -> dict[str, Any]:
    """Usage, cost and outcome of a run, without any conversation content."""
    details: dict[str, Any] = {
        "subtype": result.subtype,
        "num_turns": result.num_turns,
        "duration_ms": result.duration_ms,
    }
    optional = {
        "stop_reason": result.stop_reason,
        "terminal_reason": result.terminal_reason,
        "total_cost_usd": result.total_cost_usd,
        "usage": result.usage,
        "model_usage": result.model_usage,
    }
    details.update({key: value for key, value in optional.items() if value is not None})
    return {METADATA_KEY: details}


def _result_failure_text(result: ResultMessage) -> str:
    text = f"Agent run failed ({result.subtype})"
    if result.api_error_status is not None:
        text += f", API status {result.api_error_status}"
    if result.errors:
        text += ": " + "; ".join(result.errors)
    elif result.is_error and result.result:
        text += ": " + result.result
    return text


class EventMapper:
    """Maps the message stream of one Agent SDK run to :data:`Update` values."""

    def __init__(self) -> None:
        self._pending_text: list[str] = []
        self._finished = False
        self.session_id: str | None = None
        """The latest Agent SDK session ID seen in the stream."""
        self.result_metadata: dict[str, Any] | None = None
        """Usage and cost from the ``ResultMessage``, once it has arrived."""

    @property
    def finished(self) -> bool:
        """True once a terminal update has been produced."""
        return self._finished

    def on_message(self, message: Message) -> list[Update]:
        if self._finished:
            return []

        if isinstance(message, SystemMessage):
            session_id = message.data.get("session_id")
            if message.subtype == "init" and isinstance(session_id, str):
                self.session_id = session_id
            return []

        if isinstance(message, AssistantMessage):
            if message.session_id:
                self.session_id = message.session_id
            if message.parent_tool_use_id is not None:
                # Subagent traffic; only the main agent's answer is reported.
                return []
            return self._on_assistant(message)

        if isinstance(message, UserMessage):
            # Tool results (or injected turns): the text so far was not final.
            return self._flush_progress()

        if isinstance(message, ResultMessage):
            return self._on_result(message)

        # StreamEvent, RateLimitEvent and other housekeeping messages.
        return []

    def on_stream_end(self) -> list[Update]:
        """The stream stopped. Fail the task if no result arrived."""
        if self._finished:
            return []
        self._finished = True
        return [*self._flush_progress(), Failed("Agent SDK stream ended without a result")]

    def on_error(self, text: str) -> list[Update]:
        """The run raised. Fail the task unless it already ended."""
        if self._finished:
            return []
        self._finished = True
        return [*self._flush_progress(), Failed(text)]

    def _on_assistant(self, message: AssistantMessage) -> list[Update]:
        updates: list[Update] = []
        for block in message.content:
            if isinstance(block, TextBlock):
                if block.text.strip():
                    self._pending_text.append(block.text)
            elif isinstance(block, ToolUseBlock | ServerToolUseBlock):
                updates.extend(self._flush_progress())
                updates.append(
                    Progress(tool_progress_text(block.name), metadata={"tool_name": block.name})
                )
        return updates

    def _on_result(self, result: ResultMessage) -> list[Update]:
        self._finished = True
        if result.session_id:
            self.session_id = result.session_id
        metadata = result_metadata(result)
        self.result_metadata = metadata

        if result.is_error or result.subtype != "success":
            return [*self._flush_progress(), Failed(_result_failure_text(result), metadata)]

        final_text = result.result if result.result and result.result.strip() else None
        if final_text is None:
            final_text = "\n\n".join(self._pending_text)
        self._pending_text.clear()

        updates: list[Update] = []
        if final_text.strip():
            updates.append(FinalAnswer(final_text))
        updates.append(Completed(metadata))
        return updates

    def _flush_progress(self) -> list[Update]:
        if not self._pending_text:
            return []
        text = "\n\n".join(self._pending_text)
        self._pending_text.clear()
        return [Progress(text)]
