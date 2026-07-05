"""Action execution: resolve an index to a live node, then act on it.

Numbers come from the session's latest ``/dom`` snapshot. A number absent from
the map is ``not-found``; a backendNodeId that no longer resolves (element gone,
or the page navigated) is ``stale``. Both push the caller to re-read ``/dom``.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from .cdp_client import CDPClient, CDPError
from .session import Session


class ElementNotFound(Exception):
    """The index is not in the latest snapshot's map."""


class StaleElement(Exception):
    """The backendNodeId no longer resolves (element changed / page navigated)."""


class NavigationError(Exception):
    """Page.navigate reported a failure."""


async def _resolve_object_id(cdp: CDPClient, session: Session, index: int) -> str:
    backend = session.index_map.get(index)
    if backend is None:
        raise ElementNotFound(f"index {index} not in latest /dom snapshot")
    try:
        resolved = await cdp.send(
            "DOM.resolveNode",
            {"backendNodeId": backend},
            session_id=session.cdp_session_id,
        )
    except CDPError as exc:
        # A timeout / transport failure is not a stale element — let it surface
        # as its own error type. Only a genuine resolve failure means stale.
        if "timeout" in str(exc).lower() or "send failed" in str(exc).lower():
            raise
        raise StaleElement(f"index {index} no longer resolves") from exc
    object_id = resolved.get("object", {}).get("objectId")
    if not object_id:
        raise StaleElement(f"index {index} resolved to no object")
    return object_id


async def click(cdp: CDPClient, session: Session, index: int) -> dict[str, Any]:
    object_id = await _resolve_object_id(cdp, session, index)
    # Scroll into view and read the viewport-relative center. Coordinates come
    # from JS, but the click itself is dispatched via CDP Input events so it is
    # a trusted mouse sequence (isTrusted=true) — this drives hover menus and
    # pointer-event-dependent widgets that a JS this.click() cannot.
    rect_json = await cdp.send(
        "Runtime.callFunctionOn",
        {
            "objectId": object_id,
            "functionDeclaration": (
                "function(){ this.scrollIntoView({block:'center',inline:'center'}); "
                "const r=this.getBoundingClientRect(); "
                "return JSON.stringify({x:r.left+r.width/2, y:r.top+r.height/2, "
                "w:r.width, h:r.height}); }"
            ),
            "returnByValue": True,
        },
        session_id=session.cdp_session_id,
    )
    rect = json.loads(rect_json.get("result", {}).get("value") or "{}")
    if not rect or (rect.get("w", 0) == 0 and rect.get("h", 0) == 0):
        raise StaleElement(f"index {index} has no clickable box")
    x, y = rect["x"], rect["y"]
    sid = session.cdp_session_id
    # Move first so hover state settles, then a full press/release pair.
    await cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y}, session_id=sid)
    base = {"x": x, "y": y, "button": "left", "clickCount": 1}
    await cdp.send("Input.dispatchMouseEvent", {**base, "type": "mousePressed"}, session_id=sid)
    await cdp.send("Input.dispatchMouseEvent", {**base, "type": "mouseReleased"}, session_id=sid)
    return {"ok": True, "action": "click", "index": index}


async def type_text(cdp: CDPClient, session: Session, index: int, text: str) -> dict[str, Any]:
    object_id = await _resolve_object_id(cdp, session, index)
    # Focus and select existing content so insertText replaces rather than appends.
    await cdp.send(
        "Runtime.callFunctionOn",
        {
            "objectId": object_id,
            "functionDeclaration": (
                "function(){ this.focus(); if (this.select) this.select(); }"
            ),
        },
        session_id=session.cdp_session_id,
    )
    await cdp.send(
        "Input.insertText", {"text": text}, session_id=session.cdp_session_id
    )
    return {"ok": True, "action": "type", "index": index}


async def scroll(cdp: CDPClient, session: Session, dy: int = 600) -> dict[str, Any]:
    # mouseWheel is fire-and-forget in CDP and would hang send(); use JS scroll.
    await cdp.send(
        "Runtime.evaluate",
        {"expression": f"window.scrollBy(0, {int(dy)})"},
        session_id=session.cdp_session_id,
    )
    return {"ok": True, "action": "scroll", "dy": dy}


async def navigate(cdp: CDPClient, session: Session, url: str) -> dict[str, Any]:
    # Any navigation attempt (even a failing one that commits an error page)
    # invalidates every prior backendNodeId, so drop the map before checking.
    session.index_map.clear()
    result = await cdp.send(
        "Page.navigate", {"url": url}, session_id=session.cdp_session_id
    )
    if result.get("errorText"):
        raise NavigationError(result["errorText"])
    await _wait_ready(cdp, session)
    return {"ok": True, "action": "navigate", "url": url}


async def _wait_ready(cdp: CDPClient, session: Session, timeout: float = 20.0) -> None:
    """Poll document.readyState until 'complete' (best-effort)."""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        res = await cdp.send(
            "Runtime.evaluate",
            {"expression": "document.readyState", "returnByValue": True},
            session_id=session.cdp_session_id,
        )
        if res.get("result", {}).get("value") == "complete":
            return
        await asyncio.sleep(0.2)
