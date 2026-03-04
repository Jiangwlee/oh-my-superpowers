"""个股深研档案管理。

独立于每日数据目录，按股票代码组织深研档案。
仅负责数据采集和存储，不含任何 LLM 调用。

目录结构:
    ~/.ashare-assistant/deep_research/
    ├── index.json
    ├── 002050/
    │   ├── profile.json
    │   ├── raw_em.json
    │   ├── raw_tgb.json
    │   └── brief.md
    └── ...

时效策略：从未采集 + 距上次 ≥ 7 天 → 需要更新。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STALE_DAYS = 7
_TIME_FMT = "%Y-%m-%d %H:%M:%S"


@dataclass
class DeepResearchTarget:
    """深研目标。"""

    code: str
    name: str = ""
    context: str = ""


def normalize_full_code(code: str) -> str:
    """将 6 位股票代码转换为 szXXXXXX 或 shXXXXXX。"""
    raw = code.strip().lower()
    if raw.startswith(("sz", "sh")) and len(raw) == 8:
        return raw
    six = "".join(ch for ch in raw if ch.isdigit())
    if len(six) != 6:
        return raw
    prefix = "sh" if six.startswith(("5", "6", "9")) else "sz"
    return f"{prefix}{six}"


class DeepResearchArchive:
    """深研档案管理器。"""

    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir
        self._base.mkdir(parents=True, exist_ok=True)
        self._index_path = self._base / "index.json"

    def load_index(self) -> dict[str, Any]:
        """读取全局索引。"""
        if not self._index_path.exists():
            return {"stocks": {}, "last_updated": None}
        try:
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("读取 index.json 失败")
            return {"stocks": {}, "last_updated": None}

    def _save_index(self, index: dict[str, Any]) -> None:
        """写入全局索引。"""
        index["last_updated"] = datetime.now().strftime(_TIME_FMT)
        self._index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def update_index(self, code: str, name: str) -> None:
        """更新索引中某只股票的采集记录。"""
        index = self.load_index()
        now = datetime.now().strftime(_TIME_FMT)
        entry = index["stocks"].get(code)
        if entry:
            entry["name"] = name
            entry["last_collected_at"] = now
            entry["collect_count"] = entry.get("collect_count", 0) + 1
        else:
            index["stocks"][code] = {
                "name": name,
                "first_collected_at": now,
                "last_collected_at": now,
                "last_brief_at": None,
                "collect_count": 1,
            }
        self._save_index(index)

    def needs_update(self, code: str, *, force: bool = False) -> bool:
        """判断股票是否需要重新采集。"""
        if force:
            return True
        index = self.load_index()
        entry = index["stocks"].get(code)
        if not entry:
            return True
        last = entry.get("last_collected_at")
        if not last:
            return True
        try:
            last_dt = datetime.strptime(last, _TIME_FMT)
        except ValueError:
            return True
        return datetime.now() - last_dt >= timedelta(days=_STALE_DAYS)

    def save_raw_data(
        self,
        code: str,
        name: str,
        em_data: dict[str, Any],
        tgb_data: dict[str, Any],
    ) -> None:
        """保存原始采集数据到档案目录。"""
        stock_dir = self._base / code
        stock_dir.mkdir(parents=True, exist_ok=True)

        profile = {
            "code": code,
            "name": name,
            "full_code": normalize_full_code(code),
            "last_collected_at": datetime.now().strftime(_TIME_FMT),
        }
        (stock_dir / "profile.json").write_text(
            json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (stock_dir / "raw_em.json").write_text(
            json.dumps(em_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (stock_dir / "raw_tgb.json").write_text(
            json.dumps(tgb_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.update_index(code, name)

    def load_raw_data(self, code: str) -> dict[str, Any] | None:
        """读取股票的深研原始数据。"""
        stock_dir = self._base / code
        if not stock_dir.exists():
            return None

        result: dict[str, Any] = {"code": code, "name": "", "has_brief": False}

        profile_path = stock_dir / "profile.json"
        if profile_path.exists():
            try:
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
                result["name"] = profile.get("name", "")
                result["last_collected_at"] = profile.get("last_collected_at")
            except Exception:
                logger.exception("读取 profile.json 失败：%s", code)

        em_path = stock_dir / "raw_em.json"
        if em_path.exists():
            try:
                result["raw_em"] = json.loads(em_path.read_text(encoding="utf-8"))
            except Exception:
                result["raw_em"] = {}
        else:
            result["raw_em"] = {}

        tgb_path = stock_dir / "raw_tgb.json"
        if tgb_path.exists():
            try:
                result["raw_tgb"] = json.loads(tgb_path.read_text(encoding="utf-8"))
            except Exception:
                result["raw_tgb"] = {}
        else:
            result["raw_tgb"] = {}

        result["has_brief"] = (stock_dir / "brief.md").exists()
        return result

    def save_report(self, code: str, report: str) -> str:
        """保存 LLM 生成的深研报告。"""
        stock_dir = self._base / code
        stock_dir.mkdir(parents=True, exist_ok=True)
        brief_path = stock_dir / "brief.md"
        brief_path.write_text(report, encoding="utf-8")

        # 更新 index 中的 last_brief_at
        index = self.load_index()
        now = datetime.now().strftime(_TIME_FMT)
        entry = index["stocks"].get(code)
        if entry:
            entry["last_brief_at"] = now
        else:
            index["stocks"][code] = {
                "name": "",
                "first_collected_at": now,
                "last_collected_at": now,
                "last_brief_at": now,
                "collect_count": 0,
            }
        self._save_index(index)
        return str(brief_path)
