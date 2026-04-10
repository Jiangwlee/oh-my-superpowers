"""将 daily archive 中的条目晋升至 root-archive，并更新用户偏好。

用途：omp media-editor promote --url <url>
晋升规则：URL 去重，已存在于 root-archive 则返回 duplicate。
"""

import argparse
import json
import logging
import os
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


def find_item_in_daily(data_dir: Path, url: str) -> dict | None:
    """在所有 daily JSONL 文件中搜索指定 URL 的条目。

    Args:
        data_dir: 数据根目录。
        url: 目标 URL。

    Returns:
        找到的条目字典，未找到返回 None。
    """
    daily_dir = data_dir / "archive" / "daily"
    if not daily_dir.exists():
        return None

    for jsonl_file in sorted(daily_dir.glob("*.jsonl"), reverse=True):
        try:
            for line in jsonl_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if item.get("url") == url:
                    return item
        except Exception:
            logger.exception("读取 daily 文件失败：%s", jsonl_file)
    return None


def is_in_root_archive(root_archive_path: Path, url: str) -> bool:
    """检查 URL 是否已在 root-archive 中。

    Args:
        root_archive_path: root-archive.jsonl 路径。
        url: 目标 URL。

    Returns:
        True 表示已存在。
    """
    if not root_archive_path.exists():
        return False
    try:
        for line in root_archive_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and json.loads(line).get("url") == url:
                return True
    except Exception:
        logger.exception("读取 root-archive 失败")
    return False


def append_root_archive(root_archive_path: Path, item: dict) -> None:
    """原子追加条目到 root-archive.jsonl。

    Args:
        root_archive_path: root-archive.jsonl 路径。
        item: 要追加的条目字典。
    """
    root_archive_path.parent.mkdir(parents=True, exist_ok=True)
    new_line = json.dumps(item, ensure_ascii=False) + "\n"
    dir_path = root_archive_path.parent
    fd, tmp_path_str = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_f:
            if root_archive_path.exists():
                tmp_f.write(root_archive_path.read_text(encoding="utf-8"))
            tmp_f.write(new_line)
        tmp_path.replace(root_archive_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def update_preferences(preferences_path: Path, url: str) -> None:
    """更新 preferences.json：追加晋升 URL，更新 last_promoted 时间戳。

    Args:
        preferences_path: preferences.json 路径。
        url: 晋升的 URL。
    """
    try:
        prefs: dict = json.loads(preferences_path.read_text(encoding="utf-8"))
    except Exception:
        prefs = {"last_fetch_time": None, "user_profile": {}, "promoted_urls": [], "last_promoted": None}

    promoted: list[str] = prefs.get("promoted_urls", [])
    if url not in promoted:
        promoted.append(url)
    prefs["promoted_urls"] = promoted
    prefs["last_promoted"] = datetime.now(timezone.utc).isoformat()

    preferences_path.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")


def promote_item(data_dir: Path, url: str) -> dict[str, str]:
    """执行晋升操作。

    Args:
        data_dir: 数据根目录。
        url: 要晋升的条目 URL。

    Returns:
        操作结果字典，包含 status 字段。
    """
    root_archive_path = data_dir / "archive" / "root-archive.jsonl"
    preferences_path = data_dir / "preferences.json"

    # 检查是否已在 root-archive
    if is_in_root_archive(root_archive_path, url):
        return {"status": "duplicate"}

    # 在 daily 中查找
    item = find_item_in_daily(data_dir, url)
    if item is None:
        return {"status": "not_found"}

    # 写入 root-archive
    try:
        append_root_archive(root_archive_path, item)
    except OSError as e:
        logger.exception("写入 root-archive 失败")
        return {"status": "error", "message": str(e)}

    # 更新偏好
    try:
        update_preferences(preferences_path, url)
    except Exception:
        logger.exception("更新 preferences.json 失败（不影响晋升结果）")

    return {"status": "ok"}


def main() -> None:
    """CLI 入口：晋升条目至 root-archive。"""
    parser = argparse.ArgumentParser(description="将 daily archive 条目晋升至 root-archive。")
    parser.add_argument("--url", required=True, help="要晋升的条目 URL")
    args = parser.parse_args()

    data_dir = get_data_dir()
    result = promote_item(data_dir, args.url)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
