"""Async Chrome DevTools Protocol client.

Connects directly to a Chrome-family browser over a single browser-level
WebSocket and routes commands to page targets via flattened auto-attach
sessions. No LLM, no business logic — pure transport.

Ported pitfalls from the Node ``cdp.mjs`` implementation (knowledge, not code):

* ``Input.dispatchMouseEvent`` of type ``mouseWheel`` is fire-and-forget — Chrome
  never sends a response, so a naive ``send()`` waiting on a reply would hang.
  We never wait on mouseWheel; scrolling goes through JS instead.
* ``Page.navigate`` is a hard reload even for the same URL: it discards all page
  state (input values, JS variables, injected globals). Callers must not assume
  anything survives a navigation — and every ``backendNodeId`` captured before a
  navigation becomes stale after it.
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
from typing import Any, Callable

import websockets


class CDPError(Exception):
    """A CDP command returned an error or the node could no longer be resolved."""


class CDPClient:
    """Single-connection CDP client with flattened session routing."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9222) -> None:
        self._host = host
        self._port = port
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._next_id = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._reader_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()
        # method -> callbacks for browser/session events (mid is None frames).
        # Downloads land here via Browser.downloadWillBegin / downloadProgress.
        self._event_listeners: dict[str, list[Callable[[dict[str, Any]], None]]] = {}

    def on(self, method: str, callback: Callable[[dict[str, Any]], None]) -> None:
        """Subscribe a synchronous callback to a CDP event method.

        The callback runs inside the reader loop, so it must be non-blocking
        (dict/record updates only) — never await or do I/O in it.
        """
        self._event_listeners.setdefault(method, []).append(callback)

    # -- connection lifecycle ------------------------------------------------

    async def connect(self) -> None:
        """Open the browser-level WebSocket and start the reader loop.

        Idempotent and concurrency-safe: only one coroutine opens the socket
        even if several observe ``_ws is None`` at once.
        """
        if self._ws is not None:
            return
        async with self._connect_lock:
            if self._ws is not None:  # another coroutine won the race
                return
            ws_url = self._browser_ws_url()
            # max_size=None: DOM/AX payloads can exceed the default 1 MiB cap.
            ws = await websockets.connect(ws_url, max_size=None, ping_interval=None)
            self._ws = ws
            self._reader_task = asyncio.create_task(self._reader())

    def _browser_ws_url(self) -> str:
        """Fetch the browser-level webSocketDebuggerUrl from the DevTools HTTP API."""
        url = f"http://{self._host}:{self._port}/json/version"
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 (localhost only)
            data = json.loads(resp.read().decode("utf-8"))
        ws = data.get("webSocketDebuggerUrl")
        if not ws:
            raise CDPError("No webSocketDebuggerUrl. Is Chrome remote debugging enabled?")
        return ws

    async def close(self) -> None:
        if self._reader_task is not None:
            self._reader_task.cancel()
            self._reader_task = None
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    @property
    def connected(self) -> bool:
        return self._ws is not None

    async def _reader(self) -> None:
        """Dispatch incoming frames: resolve command futures; drop events."""
        assert self._ws is not None
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                mid = msg.get("id")
                if mid is None:
                    # Event frame: fan out to any listeners for this method.
                    for cb in self._event_listeners.get(msg.get("method", ""), ()):
                        try:
                            cb(msg.get("params", {}))
                        except Exception:  # noqa: BLE001 — a bad listener must not kill the reader
                            pass
                    continue
                fut = self._pending.pop(mid, None)
                if fut is not None and not fut.done():
                    fut.set_result(msg)
        except asyncio.CancelledError:
            pass
        except websockets.ConnectionClosed:
            pass
        finally:
            # Whatever ended the loop, the socket is unusable. Fail pending
            # commands and drop the socket so the next startup() reconnects.
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(CDPError("CDP connection closed"))
            self._pending.clear()
            self._ws = None

    # -- command dispatch ----------------------------------------------------

    async def send(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        session_id: str | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Send a CDP command and await its result.

        Args:
            method: CDP method, e.g. ``"DOM.resolveNode"``.
            params: Command parameters.
            session_id: Flattened session to route to; None targets the browser.
            timeout: Seconds to wait for a reply.

        Returns:
            The ``result`` object of the reply.

        Raises:
            CDPError: On CDP-reported error or timeout.
        """
        if self._ws is None:
            raise CDPError("CDP client not connected")
        async with self._lock:
            self._next_id += 1
            mid = self._next_id
        payload: dict[str, Any] = {"id": mid, "method": method, "params": params or {}}
        if session_id is not None:
            payload["sessionId"] = session_id
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[mid] = fut
        try:
            await self._ws.send(json.dumps(payload))
        except (websockets.ConnectionClosed, OSError) as exc:
            self._pending.pop(mid, None)
            raise CDPError(f"CDP send failed: {method}") from exc
        try:
            msg = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError as exc:
            self._pending.pop(mid, None)
            raise CDPError(f"CDP timeout: {method}") from exc
        if "error" in msg:
            raise CDPError(f"{method}: {msg['error'].get('message', msg['error'])}")
        return msg.get("result", {})
