"""ASGI app and command-line entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from starlette.applications import Starlette
from starlette.routing import BaseRoute

from a2a_claude_agent.agent_card import JSONRPC_PATH, REST_PATH, build_agent_card
from a2a_claude_agent.config import Settings
from a2a_claude_agent.executor import ClaudeAgentExecutor
from a2a_claude_agent.runner import ClaudeRunner, ClaudeSDKRunner
from a2a_claude_agent.session_store import SessionStore

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    runner: ClaudeRunner | None = None,
    session_store: SessionStore | None = None,
) -> Starlette:
    """Build the A2A server: Agent Card, JSON-RPC and (optionally) HTTP+JSON.

    ``runner`` defaults to :class:`ClaudeSDKRunner`; tests pass a fake.
    """
    settings = settings if settings is not None else Settings()
    agent_card = build_agent_card(settings)
    executor = ClaudeAgentExecutor(
        runner if runner is not None else ClaudeSDKRunner(settings),
        session_store,
    )
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes: list[BaseRoute] = [
        *create_agent_card_routes(agent_card=agent_card),
        *create_jsonrpc_routes(request_handler=request_handler, rpc_url=JSONRPC_PATH),
    ]
    if settings.enable_rest:
        routes.extend(create_rest_routes(request_handler=request_handler, path_prefix=REST_PATH))

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        yield
        await request_handler.aclose()

    app = Starlette(routes=routes, lifespan=lifespan)
    app.state.settings = settings
    app.state.agent_card = agent_card
    app.state.executor = executor
    return app


def main() -> None:
    """Start the server with settings from the environment."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = Settings()
    settings.resolved_cwd.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Serving %r (model %s, tools %s, cwd %s) at %s",
        settings.agent_name,
        settings.model,
        ",".join(settings.effective_tools) or "none",
        settings.resolved_cwd,
        settings.base_url,
    )
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
