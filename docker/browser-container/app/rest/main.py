"""REST facade over the indexed browser engine.

High-level, LLM-free. The caller's agent reads ``/dom`` (numbered interactive
elements) and drives ``/act`` by number. The container holds no brain: it does
not detect login walls or decide takeovers — that is the consumer's job.

Auth: if ``OMP_BROWSER_TOKEN`` is set, every request (except ``/health``) must
carry ``Authorization: Bearer <token>``.
"""

from __future__ import annotations

import base64
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel

from ..engine import act as actions
from ..engine.downloads import DownloadNotFound
from ..engine.session import SessionManager
from .errors import ActFailure, classify, error_body

CDP_HOST = os.environ.get("CDP_HOST", "127.0.0.1")
CDP_PORT = int(os.environ.get("CDP_PORT", "9222"))

manager = SessionManager(CDP_HOST, CDP_PORT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Best-effort connect; /health still works if the browser is not up yet.
    try:
        await manager.startup()
    except Exception:  # noqa: BLE001 — surfaced via /health
        pass
    yield
    await manager.shutdown()


app = FastAPI(title="omp browser-container", lifespan=lifespan)


def require_token(authorization: str | None = Header(default=None)) -> None:
    """Enforce the bearer token when one is configured.

    Read at request time (not import time) so the process environment is fully
    established — freezing an empty token at import could leave endpoints open.
    """
    token = os.environ.get("OMP_BROWSER_TOKEN", "")
    if not token:
        return
    if authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="invalid or missing token")


@app.exception_handler(ActFailure)
async def _act_failure_handler(_request, exc: ActFailure):
    return error_body(exc)


class ActRequest(BaseModel):
    action: str
    args: dict[str, Any] = {}


@app.get("/health")
async def health() -> dict[str, Any]:
    """Liveness of the container + reachability of the browser over CDP."""
    return {"ok": True, "browser": await manager.health()}


@app.post("/session", dependencies=[Depends(require_token)])
async def create_session() -> dict[str, str]:
    """Create or reuse the browser session; return its id."""
    session = await manager.get_or_create()
    return {"sessionId": session.session_id}


async def _get_session(session_id: str):
    # Ensure the CDP link is live first: if it dropped, startup() reconnects and
    # clears the now-dead sessions, so a stale id correctly yields no-session.
    await manager.startup()
    session = manager.get(session_id)
    if session is None:
        raise ActFailure("no-session", f"unknown sessionId: {session_id}")
    return session


@app.get("/session/{session_id}/dom", dependencies=[Depends(require_token)])
async def get_dom(session_id: str) -> dict[str, Any]:
    """Return numbered interactive elements and refresh the index map."""
    from ..engine import dom_index

    session = await _get_session(session_id)
    try:
        # Serialize extraction+store so overlapping /dom calls cannot leave the
        # returned listing and the stored map describing different snapshots.
        async with session.lock:
            listing, index_map = await dom_index.extract(manager.cdp, session.cdp_session_id)
            session.index_map = index_map
    except Exception as exc:  # noqa: BLE001
        raise classify(exc) from exc
    return {"ok": True, "count": len(index_map), "dom": listing}


@app.post("/session/{session_id}/act", dependencies=[Depends(require_token)])
async def act(session_id: str, body: ActRequest) -> dict[str, Any]:
    """Execute one action against the session's latest snapshot."""
    session = await _get_session(session_id)
    try:
        # Same per-session lock as /dom: an action resolves against a stable map
        # that a concurrent snapshot cannot swap mid-flight.
        async with session.lock:
            return await _dispatch(session, body.action, body.args)
    except ActFailure:
        raise
    except Exception as exc:  # noqa: BLE001
        raise classify(exc) from exc


async def _dispatch(session, action: str, args: dict[str, Any]) -> dict[str, Any]:
    cdp = manager.cdp
    if action == "navigate":
        result = await actions.navigate(cdp, session, args["url"])
    elif action == "click":
        result = await actions.click(cdp, session, int(args["index"]))
    elif action == "type":
        result = await actions.type_text(cdp, session, int(args["index"]), str(args["text"]))
    elif action == "scroll":
        result = await actions.scroll(cdp, session, int(args.get("dy", 600)))
    else:
        raise ActFailure("cdp-error", f"unknown action: {action}")
    # Keep one focus tab: adopt any tab this action spawned, recycle the rest,
    # and foreground it. New-tab spawning is a click concern, so only click pays
    # the detection wait.
    await manager.reconcile_focus(session, detect_new=(action == "click"))
    return result


@app.get("/session/{session_id}/shot", dependencies=[Depends(require_token)])
async def screenshot(session_id: str) -> dict[str, Any]:
    """Return a base64 PNG screenshot (optional, for multimodal callers)."""
    session = await _get_session(session_id)
    try:
        result = await manager.cdp.send(
            "Page.captureScreenshot", {"format": "png"}, session_id=session.cdp_session_id
        )
    except Exception as exc:  # noqa: BLE001
        raise classify(exc) from exc
    data = result.get("data", "")
    # Validate it decodes; keep the base64 string as the wire format.
    base64.b64decode(data)
    return {"ok": True, "format": "png", "base64": data}


# -- downloads (交付物3 ①': capture in container, extract in mindora) ---------

# Bytes read per disk block when streaming a download; bounds server memory
# regardless of how large a range the client asks for.
_STREAM_BLOCK = 1 << 20  # 1 MiB


def _parse_range(header: str | None, total: int) -> tuple[int, int] | None:
    """Parse a single ``bytes=start-end`` range against a known total size.

    Returns an inclusive ``(start, end)`` clamped to ``[0, total-1]``, or None
    when there is no/!bytes/unsatisfiable range (caller then serves full body).
    Supports ``bytes=start-``, ``bytes=start-end`` and suffix ``bytes=-N``.
    """
    if not header or not header.startswith("bytes=") or total <= 0:
        return None
    spec = header[len("bytes="):].split(",")[0].strip()
    if "-" not in spec:
        return None
    lo, hi = spec.split("-", 1)
    if lo == "":  # suffix: last N bytes
        if hi == "":
            return None
        n = min(int(hi), total)
        return (total - n, total - 1)
    start = int(lo)
    end = int(hi) if hi != "" else total - 1
    end = min(end, total - 1)
    if start > end:
        return None
    return (start, end)


def _stream_file(path: str, start: int, end: int):
    """Yield ``[start, end]`` (inclusive) of ``path`` in bounded blocks."""
    remaining = end - start + 1
    with open(path, "rb") as f:
        f.seek(start)
        while remaining > 0:
            chunk = f.read(min(_STREAM_BLOCK, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@app.get("/session/{session_id}/downloads", dependencies=[Depends(require_token)])
async def list_downloads(session_id: str) -> dict[str, Any]:
    """List downloads captured since the browser came up (browser-level)."""
    await _get_session(session_id)  # validate session; downloads are global
    out = []
    for rec in manager.downloads.list():
        item = {
            "downloadId": rec.guid,
            "filename": rec.filename,
            "totalBytes": rec.total_bytes,
            "receivedBytes": rec.received_bytes,
            "state": rec.state,
        }
        if rec.state == "completed":
            item["sha256"] = manager.downloads.sha256(rec.guid)
        out.append(item)
    return {"ok": True, "count": len(out), "downloads": out}


@app.get("/session/{session_id}/download/{download_id}", dependencies=[Depends(require_token)])
async def fetch_download(session_id: str, download_id: str, request: Request) -> Response:
    """Stream a completed download's raw bytes; honors HTTP Range for chunking."""
    await _get_session(session_id)
    try:
        rec = manager.downloads.get(download_id)
        if rec.state != "completed":
            raise ActFailure("not-ready", f"download {download_id} state={rec.state}")
        total = manager.downloads.size_on_disk(download_id)
        path = manager.downloads.path(download_id)
    except DownloadNotFound as exc:
        raise ActFailure("no-download", str(exc)) from exc

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'attachment; filename="{rec.filename or download_id}"',
        "X-Content-SHA256": manager.downloads.sha256(download_id),
    }
    rng = _parse_range(request.headers.get("range"), total)
    from fastapi.responses import StreamingResponse

    if rng is None:
        headers["Content-Length"] = str(total)
        return StreamingResponse(
            _stream_file(path, 0, total - 1),
            media_type="application/octet-stream",
            headers=headers,
        )
    start, end = rng
    headers["Content-Range"] = f"bytes {start}-{end}/{total}"
    headers["Content-Length"] = str(end - start + 1)
    return StreamingResponse(
        _stream_file(path, start, end),
        status_code=206,
        media_type="application/octet-stream",
        headers=headers,
    )


@app.delete("/session/{session_id}/download/{download_id}", dependencies=[Depends(require_token)])
async def delete_download(session_id: str, download_id: str) -> dict[str, Any]:
    """Drop a download's file + record after mindora has fetched it."""
    await _get_session(session_id)
    try:
        manager.downloads.delete(download_id)
    except DownloadNotFound as exc:
        raise ActFailure("no-download", str(exc)) from exc
    return {"ok": True, "deleted": download_id}
