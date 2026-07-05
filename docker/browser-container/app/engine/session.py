"""Browser session lifecycle and per-session index map.

Single-user model: one browser, reuse one page target across calls. A REST
``sessionId`` maps to a flattened CDP session attached to that page target.

The index map (``index -> backendNodeId``) is refreshed on every ``/dom`` call.
Per the pinned contract, element numbers are stable **within a snapshot only**;
each ``/dom`` re-extracts and re-numbers. ``act`` resolves against the most
recent snapshot's map; a number missing from it, or a backendNodeId that no
longer resolves, is reported as ``stale`` / ``not-found`` so the caller re-reads.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from .cdp_client import CDPClient, CDPError


@dataclass
class Session:
    """A live browser session bound to one page target."""

    session_id: str
    cdp_session_id: str
    target_id: str
    # index -> backendNodeId, valid only for the latest /dom snapshot.
    index_map: dict[int, int] = field(default_factory=dict)
    # Serializes /dom and /act on this session so an overlapping snapshot cannot
    # swap the map out from under an in-flight action (keeps dom/act consistent).
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionManager:
    """Owns the CDP connection and the set of live sessions."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9222) -> None:
        self._cdp = CDPClient(host, port)
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    @property
    def cdp(self) -> CDPClient:
        return self._cdp

    async def startup(self) -> None:
        """Ensure the CDP connection is live, reconnecting if it dropped.

        If the socket was lost, any prior sessions hold dead cdp_session_ids,
        so they are cleared — callers re-create via get_or_create().
        """
        if not self._cdp.connected:
            self._sessions.clear()
            await self._cdp.connect()

    async def shutdown(self) -> None:
        await self._cdp.close()
        self._sessions.clear()

    async def health(self) -> bool:
        """True if the browser is reachable over CDP."""
        try:
            await self.startup()
            await self._cdp.send("Target.getTargets")
            return True
        except (CDPError, OSError):
            return False

    # -- session creation / reuse -------------------------------------------

    async def get_or_create(self) -> Session:
        """Return an existing session or create one bound to the page target.

        Single-user: all callers share the one page target, so an existing
        session is reused rather than opening new tabs on every call.
        """
        # Serialize so concurrent POST /session calls cannot both observe an
        # empty registry and create competing sessions on the same target.
        async with self._lock:
            await self.startup()
            if self._sessions:
                return next(iter(self._sessions.values()))

            target_id = await self._ensure_page_target()
            attached = await self._cdp.send(
                "Target.attachToTarget", {"targetId": target_id, "flatten": True}
            )
            cdp_session_id = attached["sessionId"]
            # Enable the domains the engine relies on.
            for domain in ("Page", "DOM", "Runtime"):
                await self._cdp.send(f"{domain}.enable", session_id=cdp_session_id)

            session = Session(
                session_id=uuid.uuid4().hex,
                cdp_session_id=cdp_session_id,
                target_id=target_id,
            )
            self._sessions[session.session_id] = session
            return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def _ensure_page_target(self) -> str:
        targets = await self._cdp.send("Target.getTargets")
        for info in targets.get("targetInfos", []):
            if info.get("type") == "page":
                return info["targetId"]
        created = await self._cdp.send(
            "Target.createTarget", {"url": "about:blank"}
        )
        return created["targetId"]
