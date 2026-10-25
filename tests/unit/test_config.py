from pathlib import Path

import pytest
from pydantic import ValidationError

from a2a_claude_agent.config import DEFAULT_DISALLOWED_TOOLS, DEFAULT_TOOLS, Settings


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch, tmp_path):
    for name in list(__import__("os").environ):
        if name.startswith("A2A_CLAUDE_"):
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)  # no stray .env file


def test_defaults_are_read_only_and_local():
    settings = Settings()

    assert settings.model == "haiku"
    assert settings.tools == DEFAULT_TOOLS == ["Read", "Glob", "Grep"]
    assert settings.allowed_tools == []
    assert {"Bash", "Write", "Edit"} <= set(settings.disallowed_tools)
    assert settings.permission_mode == "dontAsk"
    assert settings.host == "127.0.0.1"
    assert settings.base_url == "http://127.0.0.1:41241"


def test_reads_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("A2A_CLAUDE_MODEL", "sonnet")
    monkeypatch.setenv("A2A_CLAUDE_TOOLS", "Read, Grep")
    monkeypatch.setenv("A2A_CLAUDE_ALLOWED_TOOLS", '["Read(//data/**)"]')
    monkeypatch.setenv("A2A_CLAUDE_CWD", str(tmp_path / "ws"))
    monkeypatch.setenv("A2A_CLAUDE_MAX_TURNS", "3")
    monkeypatch.setenv("A2A_CLAUDE_MAX_BUDGET_USD", "0.25")
    monkeypatch.setenv("A2A_CLAUDE_PORT", "9000")
    monkeypatch.setenv("A2A_CLAUDE_PUBLIC_URL", "https://agent.example.com/")
    monkeypatch.setenv(
        "A2A_CLAUDE_SKILLS", '[{"id": "qa", "name": "Q&A", "description": "Answers questions"}]'
    )

    settings = Settings()

    assert settings.model == "sonnet"
    assert settings.tools == ["Read", "Grep"]
    assert settings.allowed_tools == ["Read(//data/**)"]
    assert settings.resolved_cwd == (tmp_path / "ws").resolve()
    assert settings.max_turns == 3
    assert settings.max_budget_usd == 0.25
    assert settings.port == 9000
    assert settings.base_url == "https://agent.example.com"
    assert [skill.id for skill in settings.skills] == ["qa"]


def test_disallowed_tools_win_over_tools_and_allowed_tools():
    settings = Settings(
        tools=["Read", "Bash", "Write"],
        allowed_tools=["Bash(git status)", "Read(//data/**)"],
    )

    assert settings.effective_tools == ["Read"]
    assert settings.effective_allowed_tools == ["Read(//data/**)"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"model": "  "},
        {"max_turns": 0},
        {"max_budget_usd": 0},
        {"port": 70000},
        {"permission_mode": "bypassPermissions"},
    ],
)
def test_rejects_invalid_values(overrides):
    with pytest.raises(ValidationError):
        Settings(**overrides)


def test_relative_cwd_is_resolved(tmp_path):
    assert Settings(cwd=Path("workspace")).resolved_cwd == tmp_path / "workspace"


def test_default_disallowed_tools_block_subagents():
    assert {"Agent", "Task"} <= set(DEFAULT_DISALLOWED_TOOLS)
