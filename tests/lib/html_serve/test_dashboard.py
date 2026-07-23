from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DASHBOARD = ROOT / "docker" / "html-serve" / "index.html"
COMPOSE = ROOT / "docker" / "html-serve" / "compose.yaml"


def test_dashboard_is_versioned_and_mounted_read_only() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "source: ./index.html" in compose
    assert "target: /usr/share/nginx/html/index.html" in compose
    assert compose.count("read_only: true") >= 3


def test_dashboard_combines_monitoring_with_project_navigation() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")

    assert "页面监控与入口" in dashboard
    assert "最近更新" in dashboard
    assert "全部项目" in dashboard
    assert "scanDirectory" in dashboard
    assert "item.name.endsWith('.html')" in dashboard
    assert "href=\"#${encodeURIComponent(project.name)}\"" in dashboard


def test_dashboard_uses_read_only_autoindex_api() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")

    assert "const API_BASE = BASE_PATH + '/_api'" in dashboard
    assert "cache: 'no-store'" in dashboard
    assert not any(method in dashboard for method in ("method: 'POST'", "method: 'PUT'", "method: 'DELETE'"))
