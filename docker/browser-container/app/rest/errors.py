"""Error contract for the REST facade.

Every failure maps to a JSON body ``{ok: false, error_type, message}`` with a
distinguishable ``error_type`` so the caller (mindora daemon) can branch:

* ``not-found``   — index absent from the latest /dom snapshot; re-read /dom.
* ``stale``       — element/page changed; the number no longer resolves; re-read.
* ``nav-failed``  — navigation could not complete.
* ``timeout``     — the browser did not respond in time.
* ``no-session``  — unknown sessionId.
* ``cdp-error``   — any other CDP-level failure.
"""

from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from ..engine.act import ElementNotFound, NavigationError, StaleElement
from ..engine.cdp_client import CDPError

# HTTP status per error_type. 409 for stale/not-found so a healthy re-read is the
# obvious next move; 502 for browser/CDP faults; 504 for timeouts.
_STATUS = {
    "not-found": 409,
    "stale": 409,
    "nav-failed": 502,
    "timeout": 504,
    "no-session": 404,
    "cdp-error": 502,
    "no-download": 404,
    "not-ready": 409,
}


class ActFailure(HTTPException):
    """HTTPException carrying a typed error body."""

    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(status_code=_STATUS.get(error_type, 502))
        self.error_type = error_type
        self.message = message


def classify(exc: Exception) -> ActFailure:
    """Map an engine exception to a typed ActFailure."""
    if isinstance(exc, ElementNotFound):
        return ActFailure("not-found", str(exc))
    if isinstance(exc, StaleElement):
        return ActFailure("stale", str(exc))
    if isinstance(exc, NavigationError):
        return ActFailure("nav-failed", str(exc))
    if isinstance(exc, CDPError):
        msg = str(exc)
        if "timeout" in msg.lower():
            return ActFailure("timeout", msg)
        return ActFailure("cdp-error", msg)
    return ActFailure("cdp-error", str(exc))


def error_body(exc: ActFailure) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error_type": exc.error_type, "message": exc.message},
    )
