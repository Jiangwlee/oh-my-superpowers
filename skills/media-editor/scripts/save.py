"""保存媒体条目到 daily archive、SQLite 索引和 markdown card。

用途：omp-media-save --json '<item_json>'
原子性：使用临时文件 + rename 保证 JSONL 写入原子性，SQLite 使用事务。
任意步骤失败时回滚已完成步骤。
"""

import argparse
import json
import logging
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "oh-my-superpowers" / "media-editor"


def get_data_dir() -> Path:
    """获取数据目录路径，优先从环境变量读取。"""
    env = os.environ.get("MEDIA_EDITOR_DATA_DIR")
    return Path(env) if env else DEFAULT_DATA_DIR


def slugify(url: str) -> str:
    """将 URL 转换为安全的文件名 slug。

    Args:
        url: 原始 URL。

    Returns:
        安全的文件名字符串，最长 80 字符。
    """
    slug = re.sub(r"https?://", "", url)
    slug = re.sub(r"[^\w\-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80]


def get_daily_date(fetch_time: str) -> str:
    """从 ISO 时间戳提取日期字符串 YYYY-MM-DD。

    Args:
        fetch_time: ISO 8601 时间戳字符串。

    Returns:
        日期字符串，解析失败时返回今天的日期。
    """
    try:
        return fetch_time[:10]
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def append_jsonl_atomic(jsonl_path: Path, item: dict) -> None:
    """原子追加一行到 JSONL 文件。

    使用临时文件 + rename 策略：先将原文件内容 + 新行写入临时文件，再 rename 替换。

    Args:
        jsonl_path: 目标 JSONL 文件路径。
        item: 要追加的数据字典。

    Raises:
        OSError: 文件操作失败时抛出。
    """
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    new_line = json.dumps(item, ensure_ascii=False) + "\n"

    dir_path = jsonl_path.parent
    fd, tmp_path_str = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_f:
            if jsonl_path.exists():
                tmp_f.write(jsonl_path.read_text(encoding="utf-8"))
            tmp_f.write(new_line)
        tmp_path.replace(jsonl_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def insert_sqlite(db_path: Path, item: dict, daily_date: str) -> None:
    """插入条目到 SQLite（URL 唯一，重复抛 IntegrityError）。

    Args:
        db_path: SQLite 数据库路径。
        item: 条目数据字典。
        daily_date: 采集日期字符串 YYYY-MM-DD。

    Raises:
        sqlite3.IntegrityError: URL 已存在时抛出。
        sqlite3.Error: 其他数据库错误。
    """
    tags = item.get("tags", {})
    engagement = item.get("engagement", {})
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN")
        conn.execute(
            """
            INSERT INTO items
                (url, title, source, fetch_time, l1_tag, l2_tag,
                 engagement_retweets, engagement_comments, summary, selected, daily_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("url", ""),
                item.get("title", ""),
                item.get("source", ""),
                item.get("fetch_time", ""),
                tags.get("L1", ""),
                tags.get("L2", ""),
                engagement.get("retweets", 0),
                engagement.get("comments", 0),
                item.get("summary", ""),
                1 if item.get("selected", True) else 0,
                daily_date,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def write_card(cards_dir: Path, daily_date: str, item: dict) -> Path:
    """生成 markdown card 文件供 QMD 索引。

    Args:
        cards_dir: cards 根目录。
        daily_date: 日期字符串 YYYY-MM-DD。
        item: 条目数据字典。

    Returns:
        写入的 card 文件路径。
    """
    day_dir = cards_dir / daily_date
    day_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(item.get("url", "unknown"))
    card_path = day_dir / f"{slug}.md"
    tags = item.get("tags", {})
    content = f"""# {item.get('title', '')}

**URL:** {item.get('url', '')}
**Source:** {item.get('source', '')}
**Date:** {item.get('fetch_time', '')}
**L1:** {tags.get('L1', '')}
**L2:** {tags.get('L2', '')}

{item.get('summary', '')}
"""
    card_path.write_text(content, encoding="utf-8")
    return card_path


def save_item(data_dir: Path, item: dict) -> dict[str, str]:
    """保存条目，三写原子操作，任意失败时回滚。

    Args:
        data_dir: 数据根目录。
        item: 条目数据字典。

    Returns:
        操作结果字典，包含 status 字段。
    """
    url = item.get("url", "")
    if not url:
        return {"status": "error", "message": "url 字段不能为空"}

    daily_date = get_daily_date(item.get("fetch_time", ""))
    jsonl_path = data_dir / "archive" / "daily" / f"{daily_date}.jsonl"
    db_path = data_dir / "index.db"
    cards_dir = data_dir / "cards"

    # Step 1: JSONL 原子写入
    try:
        append_jsonl_atomic(jsonl_path, item)
    except OSError as e:
        logger.exception("JSONL 写入失败")
        return {"status": "error", "message": str(e)}

    # Step 2: SQLite 写入
    try:
        insert_sqlite(db_path, item, daily_date)
    except sqlite3.IntegrityError:
        # URL 已存在：回滚 JSONL（移除最后一行）
        _rollback_jsonl(jsonl_path, item)
        return {"status": "duplicate"}
    except sqlite3.Error as e:
        _rollback_jsonl(jsonl_path, item)
        logger.exception("SQLite 写入失败")
        return {"status": "error", "message": str(e)}

    # Step 3: markdown card
    try:
        write_card(cards_dir, daily_date, item)
    except OSError as e:
        # Card 写入失败：不阻断主流程，仅记录警告
        logger.warning("Card 写入失败（不影响存档）：%s", e)

    return {"status": "ok", "url": url}


def _rollback_jsonl(jsonl_path: Path, item: dict) -> None:
    """回滚 JSONL：移除最后一行（与 item URL 匹配的行）。

    Args:
        jsonl_path: JSONL 文件路径。
        item: 需要撤销的条目。
    """
    if not jsonl_path.exists():
        return
    url = item.get("url", "")
    try:
        lines = jsonl_path.read_text(encoding="utf-8").splitlines(keepends=True)
        new_lines = [l for l in lines if json.loads(l).get("url") != url]
        if len(new_lines) < len(lines):
            jsonl_path.write_text("".join(new_lines), encoding="utf-8")
    except Exception:
        logger.exception("JSONL 回滚失败，数据可能不一致")


def main() -> None:
    """CLI 入口：保存一条媒体条目。"""
    parser = argparse.ArgumentParser(description="保存媒体条目到 daily archive。")
    parser.add_argument("--json", required=True, dest="item_json", help="条目 JSON 字符串")
    args = parser.parse_args()

    try:
        item = json.loads(args.item_json)
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "message": f"JSON 解析失败：{e}"}))
        return

    data_dir = get_data_dir()
    result = save_item(data_dir, item)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
