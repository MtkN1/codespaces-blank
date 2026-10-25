"""Mapping from A2A ``contextId`` to Claude Agent SDK ``session_id``."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod


class SessionStore(ABC):
    """Remembers which Agent SDK session continues each A2A context."""

    @abstractmethod
    async def get(self, context_id: str) -> str | None:
        """Return the session ID for ``context_id``, or ``None`` if there is none."""

    @abstractmethod
    async def set(self, context_id: str, session_id: str) -> None:
        """Record that ``context_id`` continues in ``session_id``."""

    @abstractmethod
    async def delete(self, context_id: str) -> None:
        """Forget ``context_id``. Unknown IDs are ignored."""


class InMemorySessionStore(SessionStore):
    """Process-local store. Sessions are lost on restart and not shared across replicas."""

    def __init__(self) -> None:
        self._sessions: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get(self, context_id: str) -> str | None:
        async with self._lock:
            return self._sessions.get(context_id)

    async def set(self, context_id: str, session_id: str) -> None:
        async with self._lock:
            self._sessions[context_id] = session_id

    async def delete(self, context_id: str) -> None:
        async with self._lock:
            self._sessions.pop(context_id, None)
