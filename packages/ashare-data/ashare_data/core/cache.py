"""统一磁盘缓存模块。"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ashare_data.core.config import CACHE_DIR

_PERSIST_BY_DATE_CATEGORIES = {"ths", "funding", "broker", "market"}


def _safe_name(text: str, limit: int = 40) -> str:
    out = []
    for ch in str(text):
        if ch.isalnum() or ch in ("-", "_", "."):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)[:limit].strip("_") or "cache"


def _cache_path(category: str, key: str) -> Path:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    category_dir = Path(CACHE_DIR) / _safe_name(category, 24)
    filename = f"{_safe_name(key)}__{digest}.json"
    return category_dir / filename


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_envelope(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _has_date_token(text: str) -> bool:
    raw = str(text or "")
    for i in range(0, len(raw) - 7):
        chunk = raw[i : i + 8]
        if all(ch.isdigit() for ch in chunk):
            return True
    for i in range(0, len(raw) - 9):
        chunk = raw[i : i + 10]
        if (
            chunk[4] == "-"
            and chunk[7] == "-"
            and all(ch.isdigit() for j, ch in enumerate(chunk) if j not in (4, 7))
        ):
            return True
    return False


def _is_trade_date_persistent(meta: dict[str, Any]) -> bool:
    category = str(meta.get("category") or "")
    key = str(meta.get("key") or "")
    if not _has_date_token(key):
        return False
    if category in _PERSIST_BY_DATE_CATEGORIES:
        return True
    if category == "kline" and "daily" in key and "minute" not in key:
        return True
    return False


def _is_expired(meta: dict[str, Any]) -> bool:
    if _is_trade_date_persistent(meta):
        return False
    ttl_seconds = meta.get("ttl_seconds")
    if ttl_seconds in (None, ""):
        return False
    try:
        ttl = float(ttl_seconds)
    except (TypeError, ValueError):
        return False
    if ttl < 0:
        return False
    try:
        created = str(meta.get("created_at") or "")
        created_ts = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
    except Exception:
        return False
    return time.time() >= created_ts + ttl


def cache_get(category: str, key: str) -> Any | None:
    """读取缓存，命中返回 data，否则返回 None。"""
    path = _cache_path(category, key)
    try:
        exists = path.exists()
    except OSError:
        return None
    if not exists:
        return None
    envelope = _read_envelope(path)
    if not envelope:
        return None
    meta = envelope.get("_cache_meta") if isinstance(envelope.get("_cache_meta"), dict) else {}
    if _is_expired(meta):
        try:
            path.unlink()
        except OSError:
            pass
        return None
    return envelope.get("data")


def cache_set(category: str, key: str, data: Any, ttl_seconds: int | None = None) -> str:
    """写入缓存，返回文件路径。"""
    path = _cache_path(category, key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return ""
    payload = {
        "_cache_meta": {
            "created_at": _now_iso(),
            "ttl_seconds": ttl_seconds,
            "category": str(category),
            "key": str(key),
        },
        "data": data,
    }
    tmp_path = path.with_suffix(".tmp")
    try:
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, path)
        return str(path)
    except OSError:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        return ""


def cache_invalidate(category: str, key: str | None = None) -> int:
    """删除指定缓存；未提供 key 时删除整个分类。"""
    if key is None:
        category_dir = Path(CACHE_DIR) / _safe_name(category, 24)
        try:
            exists = category_dir.exists()
        except OSError:
            return 0
        if not exists:
            return 0
        removed = 0
        for path in category_dir.rglob("*.json"):
            try:
                path.unlink()
                removed += 1
            except OSError:
                continue
        return removed

    path = _cache_path(category, key)
    if path.exists():
        try:
            path.unlink()
            return 1
        except OSError:
            return 0
    return 0


def cache_cleanup(max_age_days: int = 7, max_total_bytes: int = 500 * 1024 * 1024) -> dict[str, int]:
    """清理过期/过老缓存，并在容量超限时按最老文件继续清理。"""
    root = Path(CACHE_DIR)
    try:
        exists = root.exists()
    except OSError:
        return {"removed_files": 0, "kept_files": 0, "freed_bytes": 0}
    if not exists:
        return {"removed_files": 0, "kept_files": 0, "freed_bytes": 0}

    now_ts = time.time()
    max_age_sec = max(0, max_age_days) * 24 * 3600
    removed_files = 0
    freed_bytes = 0
    kept: list[tuple[float, int, Path]] = []

    for path in root.rglob("*.json"):
        try:
            st = path.stat()
        except OSError:
            continue
        age = now_ts - st.st_mtime
        if max_age_sec and age > max_age_sec:
            try:
                size = st.st_size
                path.unlink()
                removed_files += 1
                freed_bytes += size
                continue
            except OSError:
                pass
        kept.append((st.st_mtime, st.st_size, path))

    total_bytes = sum(size for _, size, _ in kept)
    if total_bytes > max_total_bytes:
        kept.sort(key=lambda item: item[0])  # oldest first
        for _, size, path in kept:
            if total_bytes <= max_total_bytes:
                break
            try:
                path.unlink()
                removed_files += 1
                freed_bytes += size
                total_bytes -= size
            except OSError:
                continue

    remaining = 0
    for _, _, path in kept:
        try:
            if path.exists():
                remaining += 1
        except OSError:
            continue
    return {"removed_files": removed_files, "kept_files": remaining, "freed_bytes": freed_bytes}
