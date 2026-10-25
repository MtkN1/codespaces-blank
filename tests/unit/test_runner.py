from a2a_claude_agent.config import Settings
from a2a_claude_agent.runner import build_options


def test_options_pin_model_tools_and_settings(tmp_path):
    settings = Settings(model="haiku", cwd=tmp_path / "ws", max_turns=3, max_budget_usd=0.1)

    options = build_options(settings, resume=None)

    assert options.model == "haiku"
    assert options.fallback_model is None
    assert options.tools == ["Read", "Glob", "Grep"]
    assert options.allowed_tools == []
    assert {"Bash", "Write", "Edit", "Agent"} <= set(options.disallowed_tools)
    assert options.permission_mode == "dontAsk"
    assert options.setting_sources == []
    assert options.strict_mcp_config is True
    assert options.skills == []
    assert not options.agents
    assert options.cwd == (tmp_path / "ws").resolve()
    assert options.max_turns == 3
    assert options.max_budget_usd == 0.1
    assert options.resume is None
    assert options.verbatim_prompts is True
    assert options.env["CLAUDE_CODE_SUBAGENT_MODEL"] == "haiku"


def test_options_resume_session():
    options = build_options(Settings(), resume="session-123")

    assert options.resume == "session-123"
