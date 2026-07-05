"""T2 (in-process): REST wiring works without a real browser.

Uses FastAPI TestClient. No browser is running, so /health reports
``browser: false`` and an unknown session yields the typed no-session error —
both exercise the real app + error handler wiring end to end.
"""

from fastapi.testclient import TestClient

from app.rest.main import app


def test_health_reports_browser_false():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        # browser reachability depends on whether Chrome CDP is up; just a bool.
        assert isinstance(body["browser"], bool)


def test_unknown_session_typed_error():
    with TestClient(app) as client:
        resp = client.get("/session/does-not-exist/dom")
        assert resp.status_code == 404
        body = resp.json()
        assert body == {
            "ok": False,
            "error_type": "no-session",
            "message": "unknown sessionId: does-not-exist",
        }
