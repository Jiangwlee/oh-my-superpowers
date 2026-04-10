"""结构化查询 media-editor SQLite 存档。

用途：omp media-editor query [--l1 <category>] [--date <YYYY-MM-DD>] [--source <x.com|reddit.com>] [--limit <n>]
输出：JSON 数组，每个元素为一条存档条目。
"""

import argparse
import json
import logging
import os
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "oh-my-superpowers" / "media-editor"


def get_data_dir() -> Path:
    """获取数据目录路径，优先从环境变量读取。"""
    env = os.environ.get("MEDIA_EDITOR_DATA_DIR")
    return Path(env) if env else DEFAULT_DATA_DIR


def query_items(
    db_path: Path,
    l1: str | None = None,
    date: str | None = None,
    source: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """查询 SQLite 存档条目。

    Args:
        db_path: SQLite 数据库路径。
        l1: L1 分类过滤（精确匹配）。
        date: 采集日期过滤（YYYY-MM-DD）。
        source: 来源过滤（x.com 或 reddit.com）。
        limit: 返回条数上限。

    Returns:
        条目字典列表，出错时返回空列表。
    """
    if not db_path.exists():
        logger.error("数据库不存在：%s，请先运行 omp media-editor init", db_path)
        return []

    conditions: list[str] = []
    params: list[object] = []

    if l1:
        conditions.append("l1_tag = ?")
        params.append(l1)
    if date:
        conditions.append("daily_date = ?")
        params.append(date)
    if source:
        conditions.append("source = ?")
        params.append(source)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT url, title, source, fetch_time, l1_tag, l2_tag,
               engagement_retweets, engagement_comments, summary, selected, daily_date
        FROM items
        {where_clause}
        ORDER BY fetch_time DESC
        LIMIT ?
    """
    params.append(limit)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(sql, params).fetchall()
            return [
                {
                    "url": row["url"],
                    "title": row["title"],
                    "source": row["source"],
                    "fetch_time": row["fetch_time"],
                    "tags": {"L1": row["l1_tag"], "L2": row["l2_tag"]},
                    "engagement": {
                        "retweets": row["engagement_retweets"],
                        "comments": row["engagement_comments"],
                    },
                    "summary": row["summary"],
                    "selected": bool(row["selected"]),
                    "daily_date": row["daily_date"],
                }
                for row in rows
            ]
        finally:
            conn.close()
    except sqlite3.Error:
        logger.exception("查询失败")
        return []


def main() -> None:
    """CLI 入口：结构化查询存档。"""
    parser = argparse.ArgumentParser(description="结构化查询 media-editor 存档。")
    parser.add_argument("--l1", help="L1 分类过滤（如：Claude Code）")
    parser.add_argument("--date", help="采集日期过滤（YYYY-MM-DD）")
    parser.add_argument("--source", help="来源过滤（x.com 或 reddit.com）")
    parser.add_argument("--limit", type=int, default=20, help="返回条数上限（默认 20）")
    args = parser.parse_args()

    data_dir = get_data_dir()
    results = query_items(
        db_path=data_dir / "index.db",
        l1=args.l1,
        date=args.date,
        source=args.source,
        limit=args.limit,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
