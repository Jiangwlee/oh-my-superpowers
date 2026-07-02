import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from html_serve.core import (
    HtmlServeConfig,
    extract_title,
    list_entries,
    load_manifest,
    publish_file,
    reindex_manifest,
)


def make_config(tmp_path: Path) -> HtmlServeConfig:
    return HtmlServeConfig(
        data_dir=tmp_path / "data",
        port=8888,
        localhost_base_url="http://localhost:8888",
        tailscale_base_url="http://100.64.0.1:8888",
        compose_dir=tmp_path / "compose",
        manifest_path=tmp_path / "state" / "manifest.jsonl",
    )


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_extract_title_html_and_md(tmp_path: Path) -> None:
    html = write(tmp_path / "a.html", "<!doctype html><head><title> AI 日报 </title></head>")
    md = write(tmp_path / "b.md", "\n# GitHub 趋势\n\ncontent")
    plain = write(tmp_path / "c.html", "<p>no title</p>")
    assert extract_title(html) == "AI 日报"
    assert extract_title(md) == "GitHub 趋势"
    assert extract_title(plain) == ""


def test_publish_appends_manifest_entry(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.data_dir.mkdir(parents=True)
    source = write(tmp_path / "src.html", "<title>Daily Brief</title>")

    publish_file(
        input_path=source,
        config=config,
        relative_path="ai-daily/2026-07-02.html",
        verify=False,
        tags=["ai", "daily"],
        source_name="daily-ai-brief",
    )

    manifest = load_manifest(config)
    entry = manifest["ai-daily/2026-07-02.html"]
    assert entry["title"] == "Daily Brief"  # auto-extracted
    assert entry["tags"] == ["ai", "daily"]
    assert entry["source"] == "daily-ai-brief"
    assert entry["published_at"]


def test_publish_explicit_title_wins_and_republish_last_wins(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.data_dir.mkdir(parents=True)
    source = write(tmp_path / "src.html", "<title>auto</title>")

    publish_file(input_path=source, config=config, relative_path="r/a.html", verify=False, title="第一版")
    publish_file(input_path=source, config=config, relative_path="r/a.html", verify=False, title="第二版")

    manifest = load_manifest(config)
    assert len(manifest) == 1
    assert manifest["r/a.html"]["title"] == "第二版"


def test_reindex_rebuilds_from_filesystem(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    write(config.data_dir / "ai-daily" / "2026-07-01.html", "<title>Brief 1</title>")
    write(config.data_dir / "ai-daily" / "2026-07-01.md", "# Brief 1 md")
    write(config.data_dir / "_tmp" / "x.html", "<title>tmp</title>")  # hidden-ish dirs kept
    write(config.data_dir / ".hidden" / "x.html", "<title>hidden</title>")

    result = reindex_manifest(config)

    manifest = load_manifest(config)
    assert "ai-daily/2026-07-01.html" in manifest
    assert "ai-daily/2026-07-01.md" in manifest
    assert "_tmp/x.html" in manifest
    assert not any(p.startswith(".hidden") for p in manifest)
    assert manifest["ai-daily/2026-07-01.html"]["title"] == "Brief 1"
    assert result["indexed"] == len(manifest)


def test_list_entries_filters_and_urls(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    write(config.data_dir / "ai-daily" / "2026-07-01.html", "<title>知识库专题</title>关于知识库的内容")
    write(config.data_dir / "github-trending" / "2026-07-01.html", "<title>Trending</title>agent framework")
    reindex_manifest(config)

    all_entries = list_entries(config)
    assert len(all_entries) == 2

    under = list_entries(config, under="ai-daily")
    assert [e["relative_path"] for e in under] == ["ai-daily/2026-07-01.html"]
    assert under[0]["localhost_url"] == "http://localhost:8888/ai-daily/2026-07-01.html"
    assert under[0]["abs_path"].endswith("ai-daily/2026-07-01.html")

    hits = list_entries(config, grep="Agent")  # case-insensitive content grep
    assert [e["relative_path"] for e in hits] == ["github-trending/2026-07-01.html"]


def test_list_entries_fs_fallback_and_stale_manifest(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    tracked = write(config.data_dir / "a" / "tracked.html", "<title>t</title>")
    reindex_manifest(config)
    write(config.data_dir / "a" / "untracked.html", "<title>u</title>")  # published outside manifest
    tracked.unlink()  # manifest now has a ghost entry

    entries = list_entries(config)
    paths = [e["relative_path"] for e in entries]
    assert "a/untracked.html" in paths  # fs fallback picks it up
    assert "a/tracked.html" not in paths  # ghost dropped


def test_list_entries_since_until_and_tags(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.data_dir.mkdir(parents=True)
    src = write(tmp_path / "s.html", "<title>x</title>")
    publish_file(input_path=src, config=config, relative_path="r/a.html", verify=False, tags=["kb"])
    publish_file(input_path=src, config=config, relative_path="r/b.html", verify=False, tags=["agent"])

    assert [e["relative_path"] for e in list_entries(config, tags=["kb"])] == ["r/a.html"]
    assert list_entries(config, since="2099-01-01") == []
    assert len(list_entries(config, until="2099-01-01")) == 2
