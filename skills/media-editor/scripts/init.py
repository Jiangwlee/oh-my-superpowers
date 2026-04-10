"""初始化 media-editor 数据目录和 SQLite schema。

用途：omp media-editor init
功能：创建目录结构、初始化 SQLite FTS5 索引、写入默认 taxonomy.json 和 preferences.json。
幂等：重复运行安全，不会覆盖已有数据。
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

DEFAULT_TAXONOMY: dict[str, dict] = {
    "LLM": {},
    "AI Agent": {},
    "Claude Code": {},
    "CodeX": {},
    "Vibe Coding": {},
    "AI Application": {},
}

DEFAULT_PREFERENCES: dict[str, object] = {
    "last_fetch_time": None,
    "user_profile": {},
    "promoted_urls": [],
    "last_promoted": None,
}


def get_data_dir() -> Path:
    """获取数据目录路径，优先从环境变量读取。"""
    env = os.environ.get("MEDIA_EDITOR_DATA_DIR")
    return Path(env) if env else DEFAULT_DATA_DIR


def init_dirs(data_dir: Path) -> None:
    """创建完整目录结构。

    Args:
        data_dir: 数据根目录路径。
    """
    dirs = [
        data_dir / "archive" / "daily",
        data_dir / "cards",
        data_dir / "stats",
        data_dir / "reports",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    logger.info("目录结构已就绪：%s", data_dir)


def init_sqlite(data_dir: Path) -> None:
    """初始化 SQLite 数据库和 FTS5 虚拟表。

    Args:
        data_dir: 数据根目录路径。
    """
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                source TEXT,
                fetch_time TEXT,
                l1_tag TEXT,
                l2_tag TEXT,
                engagement_retweets INTEGER DEFAULT 0,
                engagement_comments INTEGER DEFAULT 0,
                summary TEXT,
                selected INTEGER DEFAULT 1,
                daily_date TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
                title,
                summary,
                l1_tag,
                l2_tag,
                content=items,
                content_rowid=id
            );

            CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
                INSERT INTO items_fts(rowid, title, summary, l1_tag, l2_tag)
                VALUES (new.id, new.title, new.summary, new.l1_tag, new.l2_tag);
            END;

            CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
                INSERT INTO items_fts(items_fts, rowid, title, summary, l1_tag, l2_tag)
                VALUES ('delete', old.id, old.title, old.summary, old.l1_tag, old.l2_tag);
            END;
        """)
        conn.commit()
        logger.info("SQLite schema 已初始化：%s", db_path)
    finally:
        conn.close()


def init_json_file(path: Path, default: dict) -> None:
    """若文件不存在则写入默认值，已存在则跳过。

    Args:
        path: 目标文件路径。
        default: 默认内容。
    """
    if path.exists():
        logger.info("已存在，跳过：%s", path)
        return
    path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("已初始化：%s", path)


def main() -> None:
    """CLI 入口：初始化数据目录。"""
    parser = argparse.ArgumentParser(
        description="初始化 media-editor 数据目录和 SQLite schema。"
    )
    parser.parse_args()

    data_dir = get_data_dir()
    init_dirs(data_dir)
    init_sqlite(data_dir)
    init_json_file(data_dir / "taxonomy.json", DEFAULT_TAXONOMY)
    init_json_file(data_dir / "preferences.json", DEFAULT_PREFERENCES)

    print(f"✓ media-editor 数据目录已就绪：{data_dir}")


if __name__ == "__main__":
    main()
