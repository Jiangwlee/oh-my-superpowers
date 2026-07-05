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
import os
import uuid
from dataclasses import dataclass, field

from .cdp_client import CDPClient, CDPError

# How long to wait for a click to spawn a new tab before concluding none opened.
_NEW_TAB_WAIT = float(os.environ.get("OMP_NEW_TAB_WAIT", "0.8"))


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
        for tid in await self._page_target_ids():
            return tid
        created = await self._cdp.send(
            "Target.createTarget", {"url": "about:blank"}
        )
        return created["targetId"]

    async def _page_target_ids(self) -> list[str]:
        targets = await self._cdp.send("Target.getTargets")
        return [
            t["targetId"]
            for t in targets.get("targetInfos", [])
            if t.get("type") == "page"
        ]

    async def _adopt(self, session: Session, target_id: str) -> None:
        """Make ``target_id`` the session's focus tab (new page ⇒ map cleared)."""
        attached = await self._cdp.send(
            "Target.attachToTarget", {"targetId": target_id, "flatten": True}
        )
        session.cdp_session_id = attached["sessionId"]
        session.target_id = target_id
        session.index_map.clear()
        for domain in ("Page", "DOM", "Runtime"):
            await self._cdp.send(f"{domain}.enable", session_id=session.cdp_session_id)

    async def reconcile_focus(self, session: Session, detect_new: bool = False) -> None:
        """Maintain the single-focus-tab invariant after an action.

        Adopts a tab the action spawned (target=_blank / window.open) as the new
        focus, closes every other page target (recycling old/stray tabs), and
        brings the focus tab to the VNC foreground. Transparent to the agent:
        the next /dom naturally reads the focus tab. Call under the session lock.
        """
        new_target = None
        if detect_new:
            deadline = asyncio.get_running_loop().time() + _NEW_TAB_WAIT
            while True:
                others = [t for t in await self._page_target_ids() if t != session.target_id]
                if others:
                    new_target = others[-1]
                    break
                if asyncio.get_running_loop().time() >= deadline:
                    break
                await asyncio.sleep(0.1)
        else:
            others = [t for t in await self._page_target_ids() if t != session.target_id]
            if others:
                new_target = others[-1]

        if new_target is not None:
            await self._adopt(session, new_target)

        # Recycle every non-focus page target so tabs do not pile up.
        for tid in await self._page_target_ids():
            if tid != session.target_id:
                try:
                    await self._cdp.send("Target.closeTarget", {"targetId": tid})
                except CDPError:
                    pass

        # Foreground the focus tab so VNC shows exactly what the agent operates on.
        try:
            await self._cdp.send("Page.bringToFront", session_id=session.cdp_session_id)
        except CDPError:
            pass
