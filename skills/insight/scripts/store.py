"""Insight 存储层。

双模式存储：
- Insight 持久化：YAML frontmatter + markdown 文件（人可读、QMD 可索引）
- 元数据管理：SQLite（evidence_links, consumption_logs）
- 检索：QMD 混合检索（可用时）/ SQLite FTS5 降级（QMD 不可用时）

目录结构：
  ~/.local/share/oh-my-superpowers/insight/
  ├── <project-hash>/          # 项目级
  │   ├── insights/            # markdown 文件
  │   └── meta.db              # SQLite 元数据
  └── global/                  # 用户级
      ├── insights/
      └── meta.db
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Insight, InsightScope

logger = logging.getLogger(__name__)

BASE_DIR = Path.home() / ".local" / "share" / "oh-my-superpowers" / "insight"


class InsightStore:
    """Insight 存储管理器。"""

    def __init__(self, project_id: str = "global"):
        self.project_id = project_id
        self.project_dir = BASE_DIR / project_id
        self.insights_dir = self.project_dir / "insights"
        self.db_path = self.project_dir / "meta.db"
        self._qmd_available: bool | None = None

        self._ensure_dirs()
        self._init_db()

    def _ensure_dirs(self) -> None:
        self.insights_dir.mkdir(parents=True, exist_ok=True)

    def _init_db(self) -> None:
        """初始化 SQLite 元数据库。"""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS evidence_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    insight_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    runtime TEXT,
                    before_text TEXT,
                    after_text TEXT,
                    context TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS consumption_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    insight_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    adopted INTEGER DEFAULT 0,
                    feedback TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS insight_index (
                    id TEXT PRIMARY KEY,
                    trigger_text TEXT,
                    wrong_default TEXT,
                    corrected_behavior TEXT,
                    tags TEXT,
                    confidence REAL,
                    scope TEXT,
                    file_path TEXT,
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS insight_fts USING fts5(
                    id,
                    trigger_text,
                    wrong_default,
                    corrected_behavior,
                    tags,
                    content=insight_index,
                    content_rowid=rowid
                );

                CREATE TRIGGER IF NOT EXISTS insight_index_ai AFTER INSERT ON insight_index BEGIN
                    INSERT INTO insight_fts(rowid, id, trigger_text, wrong_default, corrected_behavior, tags)
                    VALUES (new.rowid, new.id, new.trigger_text, new.wrong_default, new.corrected_behavior, new.tags);
                END;

                CREATE TRIGGER IF NOT EXISTS insight_index_ad AFTER DELETE ON insight_index BEGIN
                    INSERT INTO insight_fts(insight_fts, rowid, id, trigger_text, wrong_default, corrected_behavior, tags)
                    VALUES ('delete', old.rowid, old.id, old.trigger_text, old.wrong_default, old.corrected_behavior, old.tags);
                END;

                CREATE TRIGGER IF NOT EXISTS insight_index_au AFTER UPDATE ON insight_index BEGIN
                    INSERT INTO insight_fts(insight_fts, rowid, id, trigger_text, wrong_default, corrected_behavior, tags)
                    VALUES ('delete', old.rowid, old.id, old.trigger_text, old.wrong_default, old.corrected_behavior, old.tags);
                    INSERT INTO insight_fts(rowid, id, trigger_text, wrong_default, corrected_behavior, tags)
                    VALUES (new.rowid, new.id, new.trigger_text, new.wrong_default, new.corrected_behavior, new.tags);
                END;
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    # ------------------------------------------------------------------
    # 存储
    # ------------------------------------------------------------------

    def store(self, insight: Insight) -> str:
        """存储 insight（markdown 文件 + SQLite 索引）。"""
        # 写 markdown 文件
        file_path = self.insights_dir / f"{insight.id}.md"
        file_path.write_text(insight.to_markdown(), encoding="utf-8")

        # 更新 SQLite 索引
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO insight_index
                   (id, trigger_text, wrong_default, corrected_behavior, tags, confidence, scope, file_path, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    insight.id,
                    insight.trigger,
                    insight.wrong_default,
                    insight.corrected_behavior,
                    json.dumps(insight.tags, ensure_ascii=False),
                    insight.confidence,
                    insight.scope.value,
                    str(file_path),
                    datetime.now().isoformat(),
                ),
            )

            # 存储 evidence links
            for ex in insight.examples:
                conn.execute(
                    """INSERT INTO evidence_links
                       (insight_id, session_id, runtime, before_text, after_text, context)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (insight.id, ex.session_id, "", ex.before[:1000], ex.after[:1000], ex.context[:1000]),
                )

        # 如果 QMD 可用，更新 QMD 索引
        if self._is_qmd_available():
            self._qmd_update()

        logger.info("Stored insight %s at %s", insight.id, file_path)
        return insight.id

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5) -> list[Insight]:
        """检索相关 insight。

        优先使用 QMD 混合检索，降级为 SQLite FTS5。
        """
        if self._is_qmd_available():
            return self._qmd_search(query, top_k)
        return self._fts_search(query, top_k)

    def _fts_search(self, query: str, top_k: int = 5) -> list[Insight]:
        """SQLite FTS5 检索（降级方案）。

        FTS5 默认按空格分词，对中文支持有限。
        策略：先尝试原始查询，无结果时用 LIKE 模糊匹配。
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row

            # 先尝试 FTS5
            try:
                fts_query = " OR ".join(f'"{w}"' for w in query.split() if w)
                if not fts_query:
                    fts_query = f'"{query}"'
                rows = conn.execute(
                    """SELECT i.*, rank
                       FROM insight_fts f
                       JOIN insight_index i ON f.id = i.id
                       WHERE insight_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (fts_query, top_k),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []

            # FTS5 无结果时用 LIKE 模糊匹配
            if not rows:
                like_pattern = f"%{query}%"
                rows = conn.execute(
                    """SELECT * FROM insight_index
                       WHERE trigger_text LIKE ?
                          OR wrong_default LIKE ?
                          OR corrected_behavior LIKE ?
                          OR tags LIKE ?
                       ORDER BY confidence DESC
                       LIMIT ?""",
                    (like_pattern, like_pattern, like_pattern, like_pattern, top_k),
                ).fetchall()

        return [self._load_insight(row["id"]) for row in rows if row["id"]]

    def _qmd_search(self, query: str, top_k: int = 5) -> list[Insight]:
        """QMD 混合检索。"""
        try:
            result = subprocess.run(
                [
                    "qmd", "query", query,
                    "--json",
                    "--limit", str(top_k),
                    "--collection", f"insight-{self.project_id}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning("QMD search failed, falling back to FTS5")
                return self._fts_search(query, top_k)

            results = json.loads(result.stdout)
            insights = []
            for r in results:
                file_path = r.get("file", "")
                if file_path:
                    insight_id = Path(file_path).stem
                    insight = self._load_insight(insight_id)
                    if insight:
                        insights.append(insight)
            return insights

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            logger.warning("QMD search error, falling back to FTS5")
            return self._fts_search(query, top_k)

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------

    def get(self, insight_id: str) -> Insight | None:
        """获取单条 insight。"""
        return self._load_insight(insight_id)

    def list_insights(
        self,
        sort: str = "confidence",
        limit: int = 20,
    ) -> list[Insight]:
        """列出所有 insight。"""
        order = "confidence DESC" if sort == "confidence" else "updated_at DESC"
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT id FROM insight_index ORDER BY {order} LIMIT ?",
                (limit,),
            ).fetchall()

        return [
            ins
            for row in rows
            if (ins := self._load_insight(row["id"])) is not None
        ]

    def _load_insight(self, insight_id: str) -> Insight | None:
        """从 markdown 文件加载 insight。"""
        file_path = self.insights_dir / f"{insight_id}.md"
        if not file_path.exists():
            return None
        try:
            text = file_path.read_text(encoding="utf-8")
            return Insight.from_frontmatter(text)
        except (ValueError, KeyError) as e:
            logger.error("Failed to load insight %s: %s", insight_id, e)
            return None

    # ------------------------------------------------------------------
    # 更新
    # ------------------------------------------------------------------

    def update_confidence(self, insight_id: str, delta: float) -> None:
        """更新 insight 置信度。"""
        insight = self._load_insight(insight_id)
        if insight is None:
            return
        insight.confidence = max(0.0, min(1.0, insight.confidence + delta))
        insight.last_confirmed = datetime.now()
        self.store(insight)

    def promote(self, insight_id: str) -> bool:
        """提升 insight 作用域：project → user (global)。"""
        insight = self._load_insight(insight_id)
        if insight is None:
            return False
        if insight.scope == InsightScope.USER:
            return False  # 已经是 user 级

        insight.scope = InsightScope.USER
        # 存到 global store
        global_store = InsightStore("global")
        global_store.store(insight)
        logger.info("Promoted insight %s to global scope", insight_id)
        return True

    def log_consumption(
        self,
        insight_id: str,
        session_id: str,
        adopted: bool,
        feedback: str = "",
    ) -> None:
        """记录 insight 消费日志。"""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO consumption_logs
                   (insight_id, session_id, adopted, feedback)
                   VALUES (?, ?, ?, ?)""",
                (insight_id, session_id, int(adopted), feedback),
            )

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """返回存储统计。"""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM insight_index").fetchone()[0]
            avg_conf = conn.execute("SELECT AVG(confidence) FROM insight_index").fetchone()[0]
            consumptions = conn.execute("SELECT COUNT(*) FROM consumption_logs").fetchone()[0]
            adoptions = conn.execute(
                "SELECT COUNT(*) FROM consumption_logs WHERE adopted = 1"
            ).fetchone()[0]

        return {
            "project_id": self.project_id,
            "total_insights": total,
            "avg_confidence": round(avg_conf or 0, 3),
            "total_consumptions": consumptions,
            "adoption_rate": round(adoptions / consumptions, 3) if consumptions else 0,
            "qmd_available": self._is_qmd_available(),
            "store_path": str(self.project_dir),
        }

    # ------------------------------------------------------------------
    # QMD 管理
    # ------------------------------------------------------------------

    def _is_qmd_available(self) -> bool:
        """检查 QMD 是否可用。"""
        if self._qmd_available is not None:
            return self._qmd_available
        self._qmd_available = shutil.which("qmd") is not None
        return self._qmd_available

    def _qmd_update(self) -> None:
        """更新 QMD 索引。"""
        try:
            # 确保 collection 已注册
            subprocess.run(
                [
                    "qmd", "collection", "add",
                    str(self.insights_dir),
                    "--name", f"insight-{self.project_id}",
                    "--mask", "**/*.md",
                ],
                capture_output=True,
                timeout=10,
            )
            # 触发索引更新
            subprocess.run(
                ["qmd", "update"],
                capture_output=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("QMD update failed")


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------


def get_store(project_id: str, scope: InsightScope = InsightScope.PROJECT) -> InsightStore:
    """获取对应 scope 的 store。"""
    if scope == InsightScope.USER:
        return InsightStore("global")
    return InsightStore(project_id)


def search_all(query: str, project_id: str, top_k: int = 5) -> list[Insight]:
    """同时搜索项目级和用户级 insight。"""
    project_store = InsightStore(project_id)
    global_store = InsightStore("global")

    results = project_store.search(query, top_k)
    results.extend(global_store.search(query, top_k))

    # 按 confidence 排序，取 top_k
    results.sort(key=lambda i: i.confidence, reverse=True)
    return results[:top_k]
