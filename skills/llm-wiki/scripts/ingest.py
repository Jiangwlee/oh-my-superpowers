"""Ingest URL, text, or file sources into raw/."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from common import (
    infer_project,
    strip_leading_title_heading,
    raw_dir,
    resolve_wiki_home,
    slugify,
    today_utc,
    title_from_body,
    title_from_plain_text,
    write_text_atomic,
)


def render_raw_document(
    title: str,
    source_label: str,
    body: str,
    *,
    published: str = "Unknown",
    project: str | None = None,
) -> str:
    """Render a Karpathy-style raw source markdown file."""

    cleaned_body = strip_leading_title_heading(body.strip(), title)
    lines = [
        f"# {title}",
        "",
        f"> Source: {source_label}",
        f"> Collected: {today_utc()}",
        f"> Published: {published}",
    ]
    if project:
        lines.append(f"> Project: {project}")
    lines.extend(["", cleaned_body])
    return "\n".join(lines).rstrip() + "\n"


def ingest_text(wiki_home: Path, title: str | None, project: str | None, content: str) -> Path:
    """Save stdin text to raw/ using the raw source template."""

    body = content.strip()
    if not body:
        raise ValueError("no text provided on stdin")

    inferred_title = title or title_from_body(body) or f"note-{today_utc()}"
    slug = slugify(inferred_title)
    destination = raw_dir(wiki_home) / f"{slug}.md"
    write_text_atomic(
        destination,
        render_raw_document(
            inferred_title,
            "text-input",
            body,
            project=infer_project(project),
        ),
    )
    return destination


def ingest_url(wiki_home: Path, url: str, project: str | None) -> Path:
    """Fetch a URL via `omp web-operator read-url --json` and save it to raw/."""

    try:
        result = subprocess.run(
            ["omp", "web-operator", "read-url", url, "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as err:
        raise RuntimeError("`omp` not found; cannot ingest URLs without web-operator") from err
    except subprocess.CalledProcessError as err:
        stderr = err.stderr.strip() or err.stdout.strip()
        raise RuntimeError(f"failed to fetch URL via web-operator: {stderr}") from err

    payload = json.loads(result.stdout)
    body = (payload.get("content") or payload.get("text") or "").strip()
    if not body:
        raise ValueError("web-operator returned no content")

    candidate_title = payload.get("title")
    if candidate_title and candidate_title.strip() == url:
        candidate_title = None
    title = candidate_title or title_from_body(body) or title_from_plain_text(body) or url
    slug = slugify(title)
    destination = raw_dir(wiki_home) / f"{slug}.md"
    write_text_atomic(
        destination,
        render_raw_document(
            title,
            payload.get("url") or url,
            body,
            project=infer_project(project),
        ),
    )
    return destination


def ingest_file(wiki_home: Path, path_str: str, project: str | None) -> Path:
    """Copy a local markdown/text file into raw/."""

    source = Path(path_str).expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise ValueError(f"local file not found: {path_str}")
    body = source.read_text(encoding="utf-8").strip()
    if not body:
        raise ValueError("local file is empty")
    title = title_from_body(body) or title_from_plain_text(body) or source.stem
    slug = slugify(title)
    destination = raw_dir(wiki_home) / f"{slug}.md"
    write_text_atomic(
        destination,
        render_raw_document(
            title,
            str(source),
            body,
            project=infer_project(project),
        ),
    )
    return destination


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Ingest URL, text, or file into raw/.")
    parser.add_argument("source", nargs="?", help="Source URL or local file.")
    parser.add_argument("--text", action="store_true", help="Read content from stdin.")
    parser.add_argument("--title", help="Explicit title for text ingest.")
    parser.add_argument("--project", help="Optional project metadata.")
    parser.add_argument("--path", help="Wiki home directory (default: <git-root>/wiki or global).")
    args = parser.parse_args(argv)

    wiki_home = resolve_wiki_home(args.path)
    raw_dir(wiki_home).mkdir(parents=True, exist_ok=True)

    try:
        if args.text:
            destination = ingest_text(wiki_home, args.title, args.project, sys.stdin.read())
        elif args.source and args.source.startswith(("http://", "https://")):
            destination = ingest_url(wiki_home, args.source, args.project)
        elif args.source:
            destination = ingest_file(wiki_home, args.source, args.project)
        else:
            raise ValueError("provide a source argument or --text")
    except (RuntimeError, ValueError) as err:
        print(str(err), file=sys.stderr)
        return 1

    print(f"Ingested raw source: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
