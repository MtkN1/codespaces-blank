from claude_agent_sdk import AssistantMessage, StreamEvent, TextBlock, ThinkingBlock

from a2a_claude_agent.event_mapper import (
    METADATA_KEY,
    Completed,
    EventMapper,
    Failed,
    FinalAnswer,
    Progress,
)
from tests import fakes


def run(messages):
    mapper = EventMapper()
    updates = []
    for message in messages:
        updates.extend(mapper.on_message(message))
    return mapper, updates


def test_plain_answer_becomes_artifact_then_completed():
    mapper, updates = run(fakes.answer("5"))

    assert [type(u) for u in updates] == [FinalAnswer, Completed]
    assert updates[0] == FinalAnswer("5")
    assert mapper.finished
    assert mapper.session_id == "session-1"


def test_completed_metadata_carries_usage_and_models_but_no_content():
    _, updates = run(fakes.answer("5"))

    details = updates[-1].metadata[METADATA_KEY]
    assert details["subtype"] == "success"
    assert details["total_cost_usd"] == 0.0003
    assert details["usage"] == {"input_tokens": 10, "output_tokens": 3}
    assert list(details["model_usage"]) == [fakes.MODEL]
    assert "result" not in details


def test_text_before_a_tool_call_is_progress_and_tool_is_named_only():
    _, updates = run(
        [
            fakes.init(),
            fakes.assistant_text("Let me read the file."),
            fakes.tool_use("Read", {"file_path": "/secret/path.txt"}),
            fakes.tool_result("Read", "TOP SECRET"),
            fakes.assistant_text("The file says hello."),
            fakes.result("The file says hello."),
        ]
    )

    assert updates[:2] == [
        Progress("Let me read the file."),
        Progress("Running tool: Read", metadata={"tool_name": "Read"}),
    ]
    assert updates[2:4] == [FinalAnswer("The file says hello."), updates[3]]
    assert isinstance(updates[3], Completed)
    rendered = repr(updates)
    assert "/secret/path.txt" not in rendered
    assert "TOP SECRET" not in rendered


def test_text_followed_by_tool_result_is_flushed_as_progress():
    _, updates = run(
        [
            fakes.assistant_text("Checking."),
            fakes.tool_result("Read"),
            fakes.result("ok"),
        ]
    )

    assert updates == [Progress("Checking."), FinalAnswer("ok"), updates[-1]]


def test_falls_back_to_streamed_text_when_result_is_empty():
    _, updates = run([fakes.assistant_text("partial answer"), fakes.result(None)])

    assert updates[0] == FinalAnswer("partial answer")
    assert isinstance(updates[1], Completed)


def test_empty_answer_completes_without_artifact():
    _, updates = run([fakes.result("")])

    assert [type(u) for u in updates] == [Completed]


def test_error_result_fails_with_reason():
    _, updates = run(
        [
            fakes.init(),
            fakes.result(
                None, subtype="error_max_turns", is_error=True, errors=["Reached max turns (3)"]
            ),
        ]
    )

    assert len(updates) == 1
    failed = updates[0]
    assert isinstance(failed, Failed)
    assert "error_max_turns" in failed.text
    assert "Reached max turns (3)" in failed.text
    assert failed.metadata[METADATA_KEY]["subtype"] == "error_max_turns"


def test_success_subtype_with_is_error_still_fails():
    _, updates = run([fakes.result("API Error: 529 overloaded", is_error=True)])

    assert isinstance(updates[0], Failed)
    assert "API Error: 529 overloaded" in updates[0].text


def test_nothing_is_emitted_after_the_result():
    mapper, _ = run(fakes.answer("5"))

    assert mapper.on_message(fakes.assistant_text("late")) == []
    assert mapper.on_message(fakes.result("again")) == []
    assert mapper.on_stream_end() == []
    assert mapper.on_error("boom") == []


def test_stream_end_without_result_fails_and_flushes_text():
    mapper, updates = run([fakes.init(), fakes.assistant_text("half way")])

    assert updates == []
    end = mapper.on_stream_end()
    assert end[0] == Progress("half way")
    assert isinstance(end[1], Failed)
    assert mapper.finished


def test_on_error_fails_once():
    mapper = EventMapper()

    assert mapper.on_error("Agent run failed (RuntimeError)") == [
        Failed("Agent run failed (RuntimeError)")
    ]
    assert mapper.on_error("again") == []


def test_ignores_thinking_subagents_and_stream_events():
    _, updates = run(
        [
            AssistantMessage(content=[ThinkingBlock(thinking="hmm", signature="x")], model="m"),
            AssistantMessage(
                content=[TextBlock(text="subagent says hi")], model="m", parent_tool_use_id="t1"
            ),
            StreamEvent(uuid="u", session_id="s", event={"type": "content_block_delta"}),
            fakes.result("final"),
        ]
    )

    assert updates[0] == FinalAnswer("final")


def test_session_id_follows_the_latest_message():
    mapper, _ = run([fakes.init("first"), fakes.result("x", session_id="second")])

    assert mapper.session_id == "second"
