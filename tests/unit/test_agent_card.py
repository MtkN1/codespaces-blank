from a2a.types import AgentCard
from google.protobuf.json_format import MessageToDict

from a2a_claude_agent.agent_card import build_agent_card
from a2a_claude_agent.config import Settings, SkillSettings


def test_card_reflects_settings():
    settings = Settings(
        agent_name="Reader",
        agent_description="Reads files",
        agent_version="1.2.3",
        port=8123,
        skills=[SkillSettings(id="read", name="Read", description="Reads", tags=["files"])],
    )

    card = build_agent_card(settings)

    assert isinstance(card, AgentCard)
    assert card.name == "Reader"
    assert card.description == "Reads files"
    assert card.version == "1.2.3"
    assert card.capabilities.streaming is True
    assert card.capabilities.push_notifications is False
    assert [skill.id for skill in card.skills] == ["read"]
    assert list(card.skills[0].tags) == ["files"]
    assert list(card.default_input_modes) == ["text/plain"]


def test_interfaces_point_at_the_mounted_routes():
    card = build_agent_card(Settings(public_url="https://agents.example.com"))

    bindings = {(i.protocol_binding, i.url) for i in card.supported_interfaces}
    assert bindings == {
        ("JSONRPC", "https://agents.example.com/a2a/jsonrpc"),
        ("HTTP+JSON", "https://agents.example.com/a2a/rest"),
    }
    assert all(i.protocol_version == "1.0" for i in card.supported_interfaces)
    # JSON-RPC is listed first, so it is the preferred transport.
    assert card.supported_interfaces[0].protocol_binding == "JSONRPC"


def test_rest_can_be_turned_off():
    card = build_agent_card(Settings(enable_rest=False))

    assert [i.protocol_binding for i in card.supported_interfaces] == ["JSONRPC"]


def test_card_serializes():
    data = MessageToDict(build_agent_card(Settings()))

    assert data["name"] == "Claude Agent"
    assert data["skills"][0]["id"] == "general"
