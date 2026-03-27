"""V1 → V2 一次性迁移脚本。

扫描旧 insights/ 目录下的 .md 文件，将 v1 Insight 转换为 v2 Memory，
写入新 memories/ 目录。

用法：
    python -m skills.insight.scripts.migrate_v1 [--project-id PROJECT_ID]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Memory, MemoryKind, Scope, generate_id, _parse_datetime
from .store import BASE_DIR, InsightStore

logger = logging.getLogger(__name__)


def _parse_v1_frontmatter(text: str) -> dict[str, Any]:
    """解析 v1 格式的 YAML frontmatter。

    Args:
        text: 完整的 markdown 文本。

    Returns:
        解析后的字段字典。
    """
    if not text.startswith("---"):
        raise ValueError("Missing frontmatter")

    end = text.index("---", 3)
    frontmatter = text[3:end].strip()

    data: dict[str, Any] = {}
    for line in frontmatter.split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1].replace('\\"', '"')
        data[key] = value

    # 解析 JSON 数组字段
    for arr_field in ("tags", "source_session_ids"):
        if arr_field in data and isinstance(data[arr_field], str):
            try:
                data[arr_field] = json.loads(data[arr_field])
            except json.JSONDecodeError:
                data[arr_field] = []

    return data


def _v1_to_memory(data: dict[str, Any]) -> Memory:
    """将 v1 Insight 字段转换为 v2 Memory。

    Args:
        data: 从 v1 frontmatter 解析出的字段字典。

    Returns:
        新的 Memory 对象。
    """
    # v1 字段映射：
    #   trigger → context
    #   corrected_behavior → content
    #   scope → scope
    #   confidence → confidence
    #   first_seen → created_at
    #   source_session_ids[0] → source_session_id
    source_sessions = data.get("source_session_ids", [])
    source_session_id = source_sessions[0] if source_sessions else ""

    return Memory(
        id=generate_id("mem"),
        kind=MemoryKind.CORRECTION,
        content=data.get("corrected_behavior", ""),
        context=data.get("trigger", ""),
        scope=Scope(data.get("scope", "project")),
        source_session_id=source_session_id,
        created_at=_parse_datetime(data.get("first_seen", "")),
        hit_count=int(data.get("correction_count", 1)),
        confidence=float(data.get("confidence", 0.5)),
        tags=["migrated_v1"] + (data.get("tags", []) or []),
    )


def migrate_project(project_id: str) -> dict[str, int]:
    """迁移单个项目的 v1 insights 到 v2 memories。

    Args:
        project_id: 项目 ID 或 'global'。

    Returns:
        迁移统计：{'scanned', 'migrated', 'skipped', 'errors'}。
    """
    project_dir = BASE_DIR / project_id
    old_insights_dir = project_dir / "insights"

    stats = {"scanned": 0, "migrated": 0, "skipped": 0, "errors": 0}

    if not old_insights_dir.exists():
        logger.info("No insights directory found for %s, skipping", project_id)
        return stats

    store = InsightStore(project_id)
    md_files = list(old_insights_dir.glob("*.md"))
    stats["scanned"] = len(md_files)

    for f in md_files:
        try:
            text = f.read_text(encoding="utf-8")
            data = _parse_v1_frontmatter(text)

            # 跳过已经是 v2 格式的文件（有 pattern 字段说明是 v2 insight）
            if "pattern" in data:
                stats["skipped"] += 1
                continue

            # 跳过没有 corrected_behavior 的文件
            if not data.get("corrected_behavior"):
                logger.warning("Skip %s: no corrected_behavior", f.name)
                stats["skipped"] += 1
                continue

            memory = _v1_to_memory(data)
            store.store_memory(memory)
            stats["migrated"] += 1
            logger.info(
                "Migrated %s → %s: %s",
                f.name,
                memory.id,
                memory.content[:60],
            )

        except (ValueError, KeyError) as e:
            logger.error("Error migrating %s: %s", f.name, e)
            stats["errors"] += 1

    return stats


def migrate_all() -> dict[str, dict[str, int]]:
    """迁移所有项目的 v1 数据。

    Returns:
        每个项目 ID 到迁移统计的映射。
    """
    results: dict[str, dict[str, int]] = {}

    if not BASE_DIR.exists():
        logger.info("Base directory %s not found, nothing to migrate", BASE_DIR)
        return results

    for project_dir in BASE_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        project_id = project_dir.name
        logger.info("Migrating project: %s", project_id)
        results[project_id] = migrate_project(project_id)

    return results


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="Migrate v1 insights to v2 memories",
    )
    parser.add_argument(
        "--project-id",
        help="Migrate specific project (default: all projects)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    print("=== omp-insight v1 → v2 migration ===\n")

    if args.project_id:
        results = {args.project_id: migrate_project(args.project_id)}
    else:
        results = migrate_all()

    if not results:
        print("No projects found to migrate.")
        return

    # 打印统计
    total_scanned = 0
    total_migrated = 0
    total_skipped = 0
    total_errors = 0

    for project_id, stats in results.items():
        print(f"  {project_id}:")
        print(f"    scanned:  {stats['scanned']}")
        print(f"    migrated: {stats['migrated']}")
        print(f"    skipped:  {stats['skipped']}")
        print(f"    errors:   {stats['errors']}")
        total_scanned += stats["scanned"]
        total_migrated += stats["migrated"]
        total_skipped += stats["skipped"]
        total_errors += stats["errors"]

    print(f"\n  Total: {total_scanned} scanned, {total_migrated} migrated, "
          f"{total_skipped} skipped, {total_errors} errors")

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
