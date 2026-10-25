"""Server and agent settings, read from ``A2A_CLAUDE_*`` environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_TOOLS = ["Read", "Glob", "Grep"]
"""Read-only tools the agent can use.

Claude Code lets these read inside the working directory without asking; with
``permission_mode="dontAsk"`` reads outside it are denied. A bare ``"Read"``
rule in ``allowed_tools`` would lift that limit, so none is added by default.
"""

DEFAULT_DISALLOWED_TOOLS = [
    "Bash",
    "Write",
    "Edit",
    "NotebookEdit",
    "WebFetch",
    "WebSearch",
    "Agent",
    "Task",
]
"""Tools that are always removed, even when ``tools`` names them.

``Agent`` / ``Task`` spawn subagents, which could run on another model, so they
are blocked together with the tools that write files, run commands or reach
the network.
"""

DEFAULT_SYSTEM_PROMPT = (
    "You are an agent reached over the A2A protocol by another program. "
    "Answer the request concisely. You can only read files in your working "
    "directory; you cannot run commands or change files."
)


class SkillSettings(BaseModel):
    """One skill advertised on the Agent Card."""

    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


def _default_skills() -> list[SkillSettings]:
    return [
        SkillSettings(
            id="general",
            name="General assistant",
            description="Answers questions and reads files in its working directory.",
            tags=["claude", "general"],
            examples=["What is 2+3?", "Summarize README.md in the workspace."],
        )
    ]


def _split_csv(value: object) -> object:
    """Accept ``"Read,Glob"`` or a JSON list for list-valued variables."""
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            import json

            return json.loads(text)
        return [item.strip() for item in text.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    """Settings for :class:`~a2a_claude_agent.executor.ClaudeAgentExecutor` and the server."""

    model_config = SettingsConfigDict(
        env_prefix="A2A_CLAUDE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Agent (Claude Agent SDK) ---
    model: str = "haiku"
    """Model alias or full model ID. Always passed explicitly to the Agent SDK."""

    tools: Annotated[list[str], NoDecode] = Field(default_factory=lambda: list(DEFAULT_TOOLS))
    """Built-in tools the agent can see. Any tool not listed does not exist for it."""
    allowed_tools: Annotated[list[str], NoDecode] = Field(default_factory=list)
    """Extra permission rules that run without asking, e.g. ``"Read(//data/docs/**)"``."""
    disallowed_tools: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: list(DEFAULT_DISALLOWED_TOOLS)
    )
    cwd: Path = Path("workspace")
    """Working directory of the agent. Created at startup if missing."""

    max_turns: int = Field(default=10, ge=1)
    max_budget_usd: float | None = Field(default=None, gt=0)
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    permission_mode: Literal["dontAsk", "plan"] = "dontAsk"
    """``dontAsk`` denies any tool call not pre-approved instead of waiting."""

    # --- Server ---
    host: str = "127.0.0.1"
    port: int = Field(default=41241, ge=0, le=65535)
    public_url: str | None = None
    """Base URL advertised on the Agent Card. Defaults to ``http://{host}:{port}``."""
    enable_rest: bool = True

    # --- Agent Card ---
    agent_name: str = "Claude Agent"
    agent_description: str = "A Claude Agent SDK agent exposed over the A2A protocol."
    agent_version: str = "0.1.0"
    skills: list[SkillSettings] = Field(default_factory=_default_skills)

    @field_validator("tools", "allowed_tools", "disallowed_tools", mode="before")
    @classmethod
    def _parse_tool_list(cls, value: object) -> object:
        return _split_csv(value)

    @field_validator("model")
    @classmethod
    def _model_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("model must not be empty")
        return value

    @property
    def base_url(self) -> str:
        if self.public_url:
            return self.public_url.rstrip("/")
        return f"http://{self.host}:{self.port}"

    @property
    def resolved_cwd(self) -> Path:
        return self.cwd.expanduser().resolve()

    @property
    def effective_tools(self) -> list[str]:
        """``tools`` minus anything that is also disallowed."""
        blocked = {_tool_name(rule) for rule in self.disallowed_tools}
        return [name for name in self.tools if _tool_name(name) not in blocked]

    @property
    def effective_allowed_tools(self) -> list[str]:
        """``allowed_tools`` minus anything that is also disallowed."""
        blocked = {_tool_name(rule) for rule in self.disallowed_tools}
        return [rule for rule in self.allowed_tools if _tool_name(rule) not in blocked]


def _tool_name(rule: str) -> str:
    """``"Read(./**)"`` -> ``"Read"``."""
    return rule.split("(", 1)[0].strip()
