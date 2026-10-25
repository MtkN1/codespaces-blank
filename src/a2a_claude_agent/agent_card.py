"""Agent Card built from :class:`~a2a_claude_agent.config.Settings`."""

from __future__ import annotations

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from a2a_claude_agent.config import Settings

JSONRPC_PATH = "/a2a/jsonrpc"
REST_PATH = "/a2a/rest"
PROTOCOL_VERSION = "1.0"
TEXT_MODES = ["text/plain"]


def build_agent_card(settings: Settings) -> AgentCard:
    """Describe the agent: text in, text out, streaming, no push notifications."""
    base_url = settings.base_url
    interfaces = [
        AgentInterface(
            protocol_binding="JSONRPC",
            protocol_version=PROTOCOL_VERSION,
            url=f"{base_url}{JSONRPC_PATH}",
        )
    ]
    if settings.enable_rest:
        interfaces.append(
            AgentInterface(
                protocol_binding="HTTP+JSON",
                protocol_version=PROTOCOL_VERSION,
                url=f"{base_url}{REST_PATH}",
            )
        )

    return AgentCard(
        name=settings.agent_name,
        description=settings.agent_description,
        version=settings.agent_version,
        supported_interfaces=interfaces,
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=TEXT_MODES,
        default_output_modes=TEXT_MODES,
        skills=[
            AgentSkill(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                tags=skill.tags,
                examples=skill.examples,
                input_modes=TEXT_MODES,
                output_modes=TEXT_MODES,
            )
            for skill in settings.skills
        ],
    )
