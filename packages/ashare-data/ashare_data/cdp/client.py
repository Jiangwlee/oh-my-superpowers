"""Generic Chrome CDP client backed by the local `cdp.mjs` helper."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from asyncio import run as run_async
from typing import Any

from websockets import connect as ws_connect

from ashare_data.cdp.config import get_cdp_base_url, get_cdp_script, get_cdp_timeout
from ashare_data.cdp.errors import CdpEvalError, CdpNavigationError, CdpUnavailableError
from ashare_data.cdp.session import CdpPageSession

logger = logging.getLogger(__name__)


class CdpClient:
    """Reusable CDP client.

    The client uses Chrome's HTTP DevTools endpoints for tab lifecycle and the
    existing `cdp.mjs` helper for page evaluation.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        script_path: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or get_cdp_base_url()).rstrip("/")
        self.script_path = script_path or get_cdp_script()
        self.timeout = timeout or get_cdp_timeout()

    def open_page(self, url: str) -> CdpPageSession:
        """Open a new page target and return a session bound to it."""
        target = self._create_target(url)
        target_id = str(target.get("id") or target.get("targetId") or "")
        if not target_id:
            raise CdpNavigationError("CDP new page did not return target id")
        time.sleep(1.0)
        return CdpPageSession(
            client=self,
            target_id=target_id,
            page_url=url,
            timeout=self.timeout,
        )

    def close_page(self, target_id: str) -> None:
        """Close a page target."""
        encoded = urllib.parse.quote(target_id, safe="")
        try:
            self._http_text(f"{self.base_url}/json/close/{encoded}")
        except Exception as exc:
            logger.warning("close_page 失败: %s", exc)

    def list_targets(self) -> list[dict[str, Any]]:
        """List current page targets."""
        payload = self._http_json(f"{self.base_url}/json/list")
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def run_eval(self, target_id: str, expression: str) -> str:
        """Evaluate a JavaScript expression in the target page."""
        try:
            return run_async(self._run_eval_async(target_id=target_id, expression=expression))
        except CdpUnavailableError:
            raise
        except Exception as exc:
            raise CdpEvalError(str(exc)) from exc

    def _create_target(self, url: str) -> dict[str, Any]:
        encoded_url = urllib.parse.quote(url, safe=":/?&=%")
        endpoint = f"{self.base_url}/json/new?{encoded_url}"
        for method in ("PUT", "GET"):
            try:
                return self._http_json(endpoint, method=method)
            except Exception as exc:
                last_exc = exc
                logger.debug("create_target via %s failed: %s", method, exc)
        raise CdpNavigationError(f"Unable to create CDP target: {last_exc}")  # type: ignore[name-defined]

    async def _run_eval_async(self, *, target_id: str, expression: str) -> str:
        ws_url = self._get_browser_ws_url()
        async with ws_connect(ws_url, open_timeout=self.timeout, close_timeout=self.timeout) as ws:
            next_id = 0

            async def send(method: str, params: dict[str, Any] | None = None, session_id: str | None = None) -> dict[str, Any]:
                nonlocal next_id
                next_id += 1
                payload: dict[str, Any] = {"id": next_id, "method": method, "params": params or {}}
                if session_id:
                    payload["sessionId"] = session_id
                await ws.send(json.dumps(payload))
                while True:
                    message = json.loads(await ws.recv())
                    if message.get("id") != next_id:
                        continue
                    if message.get("error"):
                        raise CdpUnavailableError(str(message["error"]))
                    result = message.get("result") or {}
                    if not isinstance(result, dict):
                        raise CdpUnavailableError(f"Unexpected CDP result: {result}")
                    return result

            attached = await send("Target.attachToTarget", {"targetId": target_id, "flatten": True})
            session_id = str(attached.get("sessionId") or "")
            if not session_id:
                raise CdpUnavailableError("CDP attach did not return sessionId")
            await send("Runtime.enable", session_id=session_id)
            evaluated = await send(
                "Runtime.evaluate",
                {
                    "expression": expression,
                    "awaitPromise": True,
                    "returnByValue": True,
                },
                session_id=session_id,
            )
            await send("Target.detachFromTarget", {"sessionId": session_id})
        result = evaluated.get("result") or {}
        if evaluated.get("exceptionDetails"):
            raise CdpEvalError(str(evaluated["exceptionDetails"]))
        value = result.get("value")
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    def _get_browser_ws_url(self) -> str:
        payload = self._http_json(f"{self.base_url}/json/version")
        if not isinstance(payload, dict):
            raise CdpUnavailableError("CDP /json/version did not return an object")
        ws_url = payload.get("webSocketDebuggerUrl")
        if not isinstance(ws_url, str) or not ws_url:
            raise CdpUnavailableError("CDP browser websocket url missing")
        return ws_url

    def _http_json(self, url: str, method: str = "GET") -> Any:
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise CdpUnavailableError(f"Cannot reach CDP endpoint: {url} — {exc}") from exc
        except json.JSONDecodeError as exc:
            raise CdpUnavailableError(f"Invalid CDP response: {url} — {exc}") from exc

    def _http_text(self, url: str, method: str = "GET") -> str:
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise CdpUnavailableError(f"Cannot reach CDP endpoint: {url} — {exc}") from exc
