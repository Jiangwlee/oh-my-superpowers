#!/usr/bin/env python3
"""Unified project memory CLI (MVP).

Stores memory entries in `.memory/memories.jsonl` under a project directory and
maintains a human-readable `INDEX.md`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_MAX_ITEMS = 200
DEFAULT_AUTOLOAD_LIMIT = 20
ACTIVE_STATUS = "active"
TOPIC_PATTERN = "abcdefghijklmnopqrstuvwxyz0123456789_"


class MemoryError(Exception):
    """Raised for user-facing memory CLI errors."""


@dataclass
class MemoryStore:
    project_dir: Path

    @property
    def memory_dir(self) -> Path:
        return self.project_dir / ".memory"

    @property
    def memories_path(self) -> Path:
        return self.memory_dir / "memories.jsonl"

    @property
    def index_path(self) -> Path:
        return self.memory_dir / "INDEX.md"

    def ensure(self) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memories_path.touch(exist_ok=True)

    def load_items(self) -> list[dict[str, Any]]:
        self.ensure()
        items: list[dict[str, Any]] = []
        for line in self.memories_path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                print("warning: skipped corrupted memory row", file=sys.stderr)
                continue
            if isinstance(item, dict):
                items.append(item)
        return items

    def append_item(self, item: dict[str, Any]) -> None:
        self.ensure()
        with self.memories_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    def write_all(self, items: list[dict[str, Any]]) -> None:
        self.ensure()
        fd, tmp_name = tempfile.mkstemp(
            prefix="memories.", suffix=".jsonl", dir=str(self.memory_dir)
        )
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                for item in items:
                    f.write(json.dumps(item, ensure_ascii=False, sort_keys=True))
                    f.write("\n")
            tmp_path.replace(self.memories_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _topic_is_valid(topic: str) -> bool:
    return bool(topic) and all(ch in TOPIC_PATTERN for ch in topic)


def _default_weight(source: str) -> int:
    mapping = {
        "explicit_user_memory": 8,
        "repeat_reminder": 7,
        "precompact_summary": 5,
        "session_end_summary": 4,
        "manual": 6,
    }
    return mapping.get(source, 6)


def _contains_sensitive(text: str) -> bool:
    lower = text.lower()
    patterns = [
        "-----begin private key-----",
        "authorization: bearer ",
        "set-cookie:",
        "session=",
        "api_key",
        "apikey",
    ]
    if any(p in lower for p in patterns):
        return True
    if "sk-" in text and len(text) >= 24:
        return True
    long_alnum = 0
    for ch in text:
        if ch.isalnum():
            long_alnum += 1
            if long_alnum >= 32:
                return True
        else:
            long_alnum = 0
    return False


def _make_summary(content: str) -> str:
    text = " ".join(content.strip().split())
    if len(text) <= 40:
        return text
    return text[:37] + "..."


def _sort_for_autoload(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(item: dict[str, Any]) -> tuple[Any, ...]:
        return (
            int(item.get("weight", 0)),
            item.get("last_retrieved_at") or "",
            item.get("updated_at") or "",
        )

    return sorted(items, key=key, reverse=True)


def _active_project_items(store: MemoryStore) -> list[dict[str, Any]]:
    items = store.load_items()
    project = str(store.project_dir.resolve())
    active: list[dict[str, Any]] = []
    for item in items:
        if item.get("status") != ACTIVE_STATUS:
            continue
        if item.get("project") != project:
            continue
        active.append(item)
    return active


def _emit(obj: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
        return
    if isinstance(obj, dict):
        print(json.dumps(obj, ensure_ascii=False))
        return
    print(obj)


def cmd_add(args: argparse.Namespace, store: MemoryStore) -> int:
    if not _topic_is_valid(args.topic):
        raise MemoryError("invalid topic: use lowercase letters, numbers, underscores")
    content = args.content.strip()
    if not content:
        raise MemoryError("content must not be empty")
    if not args.force and _contains_sensitive(content):
        raise MemoryError("sensitive content detected; refusing to store")

    items = store.load_items()
    now = _now_iso()
    summary = args.summary or _make_summary(content)
    project = str(store.project_dir.resolve())

    # Simple dedupe/merge: same topic + same summary merges by reinforcing weight.
    for item in items:
        if (
            item.get("status") == ACTIVE_STATUS
            and item.get("project") == project
            and item.get("topic") == args.topic
            and item.get("summary") == summary
        ):
            item["updated_at"] = now
            item["weight"] = int(item.get("weight", 1)) + 1
            tags = set(item.get("tags") or [])
            tags.update(args.tags)
            item["tags"] = sorted(t for t in tags if t)
            store.write_all(items)
            rebuild_index(store)
            _emit(item, args.json)
            return 0

    source = args.source or "manual"
    item = {
        "id": f"mem_{datetime.now(UTC).strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}",
        "topic": args.topic,
        "content": content,
        "summary": summary,
        "tags": args.tags,
        "source": source,
        "tool": args.tool or "manual",
        "project": project,
        "created_at": now,
        "updated_at": now,
        "weight": int(args.weight if args.weight is not None else _default_weight(source)),
        "retrieval_hits": 0,
        "last_retrieved_at": None,
        "confidence": float(args.confidence),
        "status": ACTIVE_STATUS,
        "supersedes": None,
        "evidence": {
            "trigger": args.trigger or "manual",
            "raw_excerpt": args.raw_excerpt or "",
        },
    }
    store.append_item(item)
    rebuild_index(store)
    _emit(item, args.json)
    return 0


def cmd_search(args: argparse.Namespace, store: MemoryStore) -> int:
    q = args.query.lower()
    items = []
    for item in _active_project_items(store):
        hay = " ".join(
            [
                str(item.get("topic", "")),
                str(item.get("summary", "")),
                str(item.get("content", "")),
                " ".join(item.get("tags") or []),
            ]
        ).lower()
        if q in hay:
            items.append(item)
    items = _sort_for_autoload(items)[: args.limit]
    if args.json:
        _emit({"items": items, "count": len(items)}, True)
        return 0
    for item in items:
        print(f"{item['id']} {item['topic']} w={item.get('weight', 0)} {item['summary']}")
    return 0


def cmd_topics(args: argparse.Namespace, store: MemoryStore) -> int:
    items = _sort_for_autoload(_active_project_items(store))
    seen: set[str] = set()
    topics: list[str] = []
    for item in items:
        topic = str(item.get("topic", ""))
        if topic and topic not in seen:
            seen.add(topic)
            topics.append(topic)
        if len(topics) >= args.limit:
            break
    if args.json:
        _emit({"topics": topics, "count": len(topics)}, True)
        return 0
    for topic in topics:
        print(topic)
    return 0


def cmd_show(args: argparse.Namespace, store: MemoryStore) -> int:
    target = args.target or args.topic or args.memory_id
    if not target:
        raise MemoryError("show requires a target (positional, --topic, or --id)")
    items = _active_project_items(store)
    matched = [
        item
        for item in items
        if item.get("id") == target or item.get("topic") == target
    ]
    matched = _sort_for_autoload(matched)
    if args.json:
        _emit({"items": matched, "count": len(matched)}, True)
        return 0
    for item in matched:
        print(json.dumps(item, ensure_ascii=False, indent=2))
    return 0 if matched else 1


def _touch_by_ids(items: list[dict[str, Any]], ids: set[str], delta: int) -> int:
    now = _now_iso()
    touched = 0
    for item in items:
        if item.get("id") not in ids:
            continue
        item["retrieval_hits"] = int(item.get("retrieval_hits", 0)) + 1
        item["weight"] = max(1, int(item.get("weight", 1)) + delta)
        item["last_retrieved_at"] = now
        item["updated_at"] = now
        touched += 1
    return touched


def cmd_touch(args: argparse.Namespace, store: MemoryStore) -> int:
    items = store.load_items()
    count = _touch_by_ids(items, {args.memory_id}, args.delta)
    if count:
        store.write_all(items)
        rebuild_index(store)
    if args.json:
        _emit({"touched": count}, True)
    else:
        print(f"touched={count}")
    return 0 if count else 1


def cmd_delete(args: argparse.Namespace, store: MemoryStore) -> int:
    items = store.load_items()
    before = len(items)
    for item in items:
        if item.get("id") == args.memory_id:
            item["status"] = "archived"
            item["updated_at"] = _now_iso()
    store.write_all(items)
    rebuild_index(store)
    changed = before != 0 and any(i.get("id") == args.memory_id for i in items)
    if args.json:
        _emit({"deleted": 1 if changed else 0}, True)
    else:
        print(f"deleted={1 if changed else 0}")
    return 0 if changed else 1


def _prune_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    status_rank = 0 if item.get("status") != ACTIVE_STATUS else 1
    return (
        status_rank,
        int(item.get("weight", 0)),
        int(item.get("retrieval_hits", 0)),
        item.get("last_retrieved_at") or "",
        item.get("updated_at") or "",
    )


def cmd_prune(args: argparse.Namespace, store: MemoryStore) -> int:
    items = store.load_items()
    if len(items) <= args.max_items:
        if args.json:
            _emit({"removed": 0, "remaining": len(items)}, True)
        else:
            print("removed=0")
        return 0

    sorted_items = sorted(items, key=_prune_sort_key)
    remove_count = len(items) - args.max_items
    to_remove_ids = {item["id"] for item in sorted_items[:remove_count]}
    kept = [item for item in items if item.get("id") not in to_remove_ids]
    store.write_all(kept)
    rebuild_index(store)
    if args.json:
        _emit({"removed": remove_count, "remaining": len(kept)}, True)
    else:
        print(f"removed={remove_count}")
    return 0


def cmd_autoload_topics(args: argparse.Namespace, store: MemoryStore) -> int:
    all_items = store.load_items()
    project = str(store.project_dir.resolve())
    active_items = [
        item
        for item in all_items
        if item.get("status") == ACTIVE_STATUS and item.get("project") == project
    ]
    ranked = _sort_for_autoload(active_items)

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in ranked:
        topic = str(item.get("topic", ""))
        if not topic or topic in seen:
            continue
        seen.add(topic)
        selected.append(item)
        if len(selected) >= args.limit:
            break

    if args.touch:
        touched = _touch_by_ids(all_items, {i["id"] for i in selected}, args.delta)
        if touched:
            store.write_all(all_items)
            rebuild_index(store)

    topics = [str(item.get("topic")) for item in selected]
    if args.json:
        _emit({"topics": topics, "count": len(topics)}, True)
        return 0
    print(f"[mem-autoload] top topics ({len(topics)}):")
    for topic in topics:
        print(f"- {topic}")
    return 0


def rebuild_index(store: MemoryStore) -> None:
    items = _active_project_items(store)
    items = _sort_for_autoload(items)

    lines = [
        "# Memory Index",
        "",
        f"- project: `{store.project_dir.resolve()}`",
        f"- updated_at: `{_now_iso()}`",
        f"- active_items: `{len(items)}`",
        "",
        "## Topics",
        "",
    ]

    topic_rows: dict[str, dict[str, Any]] = {}
    for item in items:
        topic = str(item.get("topic", ""))
        if topic not in topic_rows:
            topic_rows[topic] = item

    for topic, item in topic_rows.items():
        lines.append(
            f"- `{topic}` | w={item.get('weight', 0)} | hits={item.get('retrieval_hits', 0)} | {item.get('summary', '')}"
        )
    lines.append("")
    store.memory_dir.mkdir(parents=True, exist_ok=True)
    store.index_path.write_text("\n".join(lines), encoding="utf-8")


def cmd_rebuild_index(args: argparse.Namespace, store: MemoryStore) -> int:
    rebuild_index(store)
    if args.json:
        _emit({"index_path": str(store.index_path)}, True)
    else:
        print(store.index_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified memory CLI (project-level)")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory containing .memory/ (default: current directory)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_json_flag(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--json", action="store_true", help="Output JSON")

    p_add = subparsers.add_parser("add", help="Add a memory entry")
    p_add.add_argument("--topic", required=True)
    p_add.add_argument("--content", required=True)
    p_add.add_argument("--summary")
    p_add.add_argument("--tags", default="")
    p_add.add_argument("--weight", type=int)
    p_add.add_argument("--source")
    p_add.add_argument("--tool")
    p_add.add_argument("--trigger")
    p_add.add_argument("--raw-excerpt")
    p_add.add_argument("--confidence", type=float, default=0.95)
    p_add.add_argument("--force", action="store_true")
    add_json_flag(p_add)
    p_add.set_defaults(func=cmd_add)

    p_search = subparsers.add_parser("search", help="Search active memories")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10)
    add_json_flag(p_search)
    p_search.set_defaults(func=cmd_search)

    p_topics = subparsers.add_parser("topics", help="List active topics")
    p_topics.add_argument("--limit", type=int, default=100)
    add_json_flag(p_topics)
    p_topics.set_defaults(func=cmd_topics)

    p_show = subparsers.add_parser("show", help="Show memory by id or topic")
    p_show.add_argument("target", nargs="?")
    p_show.add_argument("--topic", help="Show by topic (alias for positional target)")
    p_show.add_argument("--id", dest="memory_id", help="Show by memory id")
    add_json_flag(p_show)
    p_show.set_defaults(func=cmd_show)

    p_touch = subparsers.add_parser("touch", help="Increase weight/retrieval hits")
    p_touch.add_argument("memory_id")
    p_touch.add_argument("--delta", type=int, default=1)
    add_json_flag(p_touch)
    p_touch.set_defaults(func=cmd_touch)

    p_delete = subparsers.add_parser("delete", help="Archive memory by id")
    p_delete.add_argument("memory_id")
    add_json_flag(p_delete)
    p_delete.set_defaults(func=cmd_delete)

    p_prune = subparsers.add_parser("prune", help="Prune to max item count")
    p_prune.add_argument("--max-items", type=int, default=DEFAULT_MAX_ITEMS)
    add_json_flag(p_prune)
    p_prune.set_defaults(func=cmd_prune)

    p_rebuild = subparsers.add_parser("rebuild-index", help="Rebuild INDEX.md")
    add_json_flag(p_rebuild)
    p_rebuild.set_defaults(func=cmd_rebuild_index)

    p_autoload = subparsers.add_parser(
        "autoload-topics",
        help="Return top-weighted active topics for /mem-autoload",
    )
    p_autoload.add_argument("--limit", type=int, default=DEFAULT_AUTOLOAD_LIMIT)
    p_autoload.add_argument(
        "--no-touch",
        dest="touch",
        action="store_false",
        help="Do not increase weight/hits for selected topics",
    )
    p_autoload.add_argument("--delta", type=int, default=1)
    p_autoload.set_defaults(touch=True)
    add_json_flag(p_autoload)
    p_autoload.set_defaults(func=cmd_autoload_topics)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.tags = [t.strip() for t in str(getattr(args, "tags", "")).split(",") if t.strip()]
    store = MemoryStore(project_dir=Path(args.project_dir).resolve())
    try:
        return int(args.func(args, store))
    except MemoryError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
