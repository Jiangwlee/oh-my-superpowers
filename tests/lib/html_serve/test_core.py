import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from html_serve.core import HtmlServeConfig, HtmlServeError, normalize_relative_path, publish_file, url_metadata


def make_config(tmp_path: Path) -> HtmlServeConfig:
    return HtmlServeConfig(
        data_dir=tmp_path,
        port=8888,
        localhost_base_url="http://localhost:8888",
        tailscale_base_url="http://100.64.0.1:8888",
        compose_dir=tmp_path / "compose",
    )


def test_normalize_relative_path_rejects_escape() -> None:
    with pytest.raises(HtmlServeError):
        normalize_relative_path("../report.html")
    with pytest.raises(HtmlServeError):
        normalize_relative_path("/report.html")
    with pytest.raises(HtmlServeError):
        normalize_relative_path("reports/report.md")


def test_publish_file_returns_localhost_and_tailscale_urls(tmp_path: Path) -> None:
    source = tmp_path / "source.html"
    source.write_text("<!doctype html><title>ok</title>", encoding="utf-8")

    result = publish_file(
        input_path=source,
        config=make_config(tmp_path),
        relative_path="reports/report.html",
        verify=False,
    )

    assert (tmp_path / "reports" / "report.html").read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert result["localhost_url"] == "http://localhost:8888/reports/report.html"
    assert result["tailscale_url"] == "http://100.64.0.1:8888/reports/report.html"
    assert result["urls"] == {
        "localhost": "http://localhost:8888/reports/report.html",
        "tailscale": "http://100.64.0.1:8888/reports/report.html",
    }


def test_url_metadata_can_check_existing_file(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b.html").write_text("ok", encoding="utf-8")

    result = url_metadata(make_config(tmp_path), "a/b.html", check=True, verify=False)

    assert result["exists"] is True
    assert result["localhost_url"].endswith("/a/b.html")
    assert result["tailscale_url"].endswith("/a/b.html")
