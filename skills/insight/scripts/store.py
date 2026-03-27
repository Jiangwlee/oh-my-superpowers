"""Insight 存储层。

双模式存储：
- 持久化：YAML frontmatter + markdown 文件（人可读）
- 元数据管理：SQLite（evidence_links, hit_logs）

目录结构：
  ~/.local/share/oh-my-superpowers/insight/
  ├── <project-hash>/
  │   ├── memories/              # 每条一个 markdown
  │   ├── insights/              # 每条一个 markdown
  │   └── meta.db                # SQLite
  └── global/
      ├── memories/
      ├── insights/
      └── meta.db
"""

from __future__ import annotations

import logging
import re
import sqlite3
from contextlib import contextmanager
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Insight, Memory, Scope, generate_id

logger = logging.getLogger(__name__)

BASE_DIR = Path.home() / ".local" / "share" / "oh-my-superpowers" / "insight"


class InsightStore:
    """Memory + Insight 存储管理器。"""

    def __init__(self, project_id: str = "global"):
        if not re.match(r"^[a-zA-Z0-9_\-]+$", project_id):
            raise ValueError(f"Invalid project_id: {project_id!r}")
        self.project_id = project_id
        self.project_dir = BASE_DIR / project_id
        self.memories_dir = self.project_dir / "memories"
        self.insights_dir = self.project_dir / "insights"
        self.db_path = self.project_dir / "meta.db"

        self._ensure_dirs()
        self._safe_init_db()

    def _ensure_dirs(self) -> None:
        """创建存储目录。"""
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        self.insights_dir.mkdir(parents=True, exist_ok=True)

    def _safe_init_db(self) -> None:
        """初始化 DB，损坏时自动重建。"""
        try:
            self._init_db()
            with self._connect() as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()
                if result[0] != "ok":
                    raise sqlite3.DatabaseError("integrity check failed")
        except sqlite3.DatabaseError as e:
            logger.warning("DB corrupted (%s), rebuilding", e)
            self.db_path.unlink(missing_ok=True)
            for suffix in ("-wal", "-shm"):
                Path(str(self.db_path) + suffix).unlink(missing_ok=True)
            self._init_db()

    def _init_db(self) -> None:
        """初始化 SQLite 元数据库。"""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS evidence_links (
                    insight_id TEXT NOT NULL,
                    memory_id TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (insight_id, memory_id)
                );

                CREATE TABLE IF NOT EXISTS hit_logs (
                    item_id TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    session_id TEXT,
                    timestamp INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_hit_item
                    ON hit_logs(item_id);
                CREATE INDEX IF NOT EXISTS idx_hit_timestamp
                    ON hit_logs(timestamp);

                CREATE TABLE IF NOT EXISTS processed_sessions (
                    session_id TEXT PRIMARY KEY,
                    processed_at INTEGER NOT NULL,
                    memory_count INTEGER NOT NULL DEFAULT 0
                );
            """)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """创建 SQLite 连接（WAL 模式），退出时自动关闭。"""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Memory CRUD
    # ------------------------------------------------------------------

    def store_memory(self, memory: Memory) -> str:
        """存储一条 memory 到 markdown 文件。

        Args:
            memory: 要存储的 Memory 对象。

        Returns:
            存储的 memory ID。
        """
        file_path = self.memories_dir / f"{memory.id}.md"
        file_path.write_text(memory.to_markdown(), encoding="utf-8")
        logger.info("Stored memory %s at %s", memory.id, file_path)
        return memory.id

    def get_memory(self, memory_id: str) -> Memory | None:
        """获取单条 memory。

        Args:
            memory_id: Memory ID。

        Returns:
            Memory 对象，不存在时返回 None。
        """
        file_path = self.memories_dir / f"{memory_id}.md"
        if not file_path.exists():
            return None
        try:
            text = file_path.read_text(encoding="utf-8")
            return Memory.from_frontmatter(text)
        except (ValueError, KeyError) as e:
            logger.error("Failed to load memory %s: %s", memory_id, e)
            return None

    def list_memories(
        self,
        sort: str = "hit_count",
        limit: int = 50,
    ) -> list[Memory]:
        """列出所有 memory。

        Args:
            sort: 排序字段，支持 'hit_count' 和 'confidence'。
            limit: 最大返回数量。

        Returns:
            Memory 列表。
        """
        memories: list[Memory] = []
        for f in self.memories_dir.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8")
                memories.append(Memory.from_frontmatter(text))
            except (ValueError, KeyError) as e:
                logger.warning("Skip loading %s: %s", f.name, e)

        if sort == "confidence":
            memories.sort(key=lambda m: m.confidence, reverse=True)
        else:
            memories.sort(key=lambda m: m.hit_count, reverse=True)

        return memories[:limit]

    def delete_memory(self, memory_id: str) -> bool:
        """删除一条 memory。

        Args:
            memory_id: Memory ID。

        Returns:
            是否成功删除。
        """
        file_path = self.memories_dir / f"{memory_id}.md"
        if not file_path.exists():
            return False
        file_path.unlink()
        logger.info("Deleted memory %s", memory_id)
        return True

    # ------------------------------------------------------------------
    # Insight CRUD
    # ------------------------------------------------------------------

    def store_insight(self, insight: Insight) -> str:
        """存储一条 insight 到 markdown 文件。

        Args:
            insight: 要存储的 Insight 对象。

        Returns:
            存储的 insight ID。
        """
        file_path = self.insights_dir / f"{insight.id}.md"
        file_path.write_text(insight.to_markdown(), encoding="utf-8")
        logger.info("Stored insight %s at %s", insight.id, file_path)
        return insight.id

    def get_insight(self, insight_id: str) -> Insight | None:
        """获取单条 insight。

        Args:
            insight_id: Insight ID。

        Returns:
            Insight 对象，不存在时返回 None。
        """
        file_path = self.insights_dir / f"{insight_id}.md"
        if not file_path.exists():
            return None
        try:
            text = file_path.read_text(encoding="utf-8")
            return Insight.from_frontmatter(text)
        except (ValueError, KeyError) as e:
            logger.error("Failed to load insight %s: %s", insight_id, e)
            return None

    def list_insights(
        self,
        sort: str = "confidence",
        limit: int = 20,
    ) -> list[Insight]:
        """列出所有 insight。

        Args:
            sort: 排序字段，支持 'confidence' 和 'evidence_count'。
            limit: 最大返回数量。

        Returns:
            Insight 列表。
        """
        insights: list[Insight] = []
        for f in self.insights_dir.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8")
                insights.append(Insight.from_frontmatter(text))
            except (ValueError, KeyError) as e:
                logger.warning("Skip loading %s: %s", f.name, e)

        if sort == "evidence_count":
            insights.sort(key=lambda i: i.evidence_count, reverse=True)
        else:
            insights.sort(key=lambda i: i.confidence, reverse=True)

        return insights[:limit]

    def delete_insight(self, insight_id: str) -> bool:
        """删除一条 insight 及其 evidence_links。

        Args:
            insight_id: Insight ID。

        Returns:
            是否成功删除。
        """
        file_path = self.insights_dir / f"{insight_id}.md"
        if not file_path.exists():
            return False
        # DB first, then file — safer ordering for crash recovery
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM evidence_links WHERE insight_id = ?",
                (insight_id,),
            )
        file_path.unlink()
        logger.info("Deleted insight %s", insight_id)
        return True

    # ------------------------------------------------------------------
    # Evidence links
    # ------------------------------------------------------------------

    def link_evidence(self, insight_id: str, memory_id: str) -> None:
        """关联 insight 和 memory。

        Args:
            insight_id: Insight ID。
            memory_id: Memory ID。
        """
        with self._connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO evidence_links
                   (insight_id, memory_id, created_at)
                   VALUES (?, ?, ?)""",
                (insight_id, memory_id, int(datetime.now().timestamp())),
            )

    def get_evidence(self, insight_id: str) -> list[str]:
        """获取 insight 关联的所有 memory ID。

        Args:
            insight_id: Insight ID。

        Returns:
            关联的 memory ID 列表。
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT memory_id FROM evidence_links WHERE insight_id = ?",
                (insight_id,),
            ).fetchall()
            return [row[0] for row in rows]

    # ------------------------------------------------------------------
    # Hit logging
    # ------------------------------------------------------------------

    def log_hit(
        self,
        item_id: str,
        item_type: str,
        session_id: str = "",
    ) -> None:
        """记录一次命中日志。

        Args:
            item_id: Memory 或 Insight 的 ID。
            item_type: 'memory' 或 'insight'。
            session_id: 触发命中的会话 ID。
        """
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO hit_logs
                   (item_id, item_type, session_id, timestamp)
                   VALUES (?, ?, ?, ?)""",
                (item_id, item_type, session_id, int(datetime.now().timestamp())),
            )

    def get_hit_count(self, item_id: str) -> int:
        """获取某条记录的命中次数。

        Args:
            item_id: Memory 或 Insight 的 ID。

        Returns:
            命中次数。
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM hit_logs WHERE item_id = ?",
                (item_id,),
            ).fetchone()
            return row[0] if row else 0

    # ------------------------------------------------------------------
    # Recall（核心）
    # ------------------------------------------------------------------

    def recall(self, budget: int = 4096, format: str = "md") -> str:
        """召回记忆和洞察，在 token 预算内输出。

        策略：
        1. 加载全部 insight（全量）
        2. 剩余预算按 hit_count * confidence 降序填充 memory
        3. 记录 hit_logs
        4. 输出 markdown 或 JSON

        Args:
            budget: Token 预算（近似 len(text) // 4）。
            format: 输出格式，'md' 或 'json'。

        Returns:
            格式化的召回内容。
        """
        used_tokens = 0
        recalled_insights: list[Insight] = []
        recalled_memories: list[Memory] = []

        # 1. 全量加载 insight
        all_insights = self.list_insights(sort="confidence", limit=100)
        for ins in all_insights:
            text = ins.to_markdown()
            tokens = len(text) // 4
            if used_tokens + tokens > budget:
                break
            recalled_insights.append(ins)
            used_tokens += tokens

        # 2. 剩余预算填充 memory（按 hit_count * confidence 排序）
        all_memories = self.list_memories(sort="hit_count", limit=200)
        all_memories.sort(
            key=lambda m: m.hit_count * m.confidence,
            reverse=True,
        )
        for mem in all_memories:
            text = mem.to_markdown()
            tokens = len(text) // 4
            if used_tokens + tokens > budget:
                break
            recalled_memories.append(mem)
            used_tokens += tokens

        # 3. 批量记录 hit_logs（单次事务）
        now_ts = int(datetime.now().timestamp())
        hit_rows = (
            [(ins.id, "insight", "", now_ts) for ins in recalled_insights]
            + [(mem.id, "memory", "", now_ts) for mem in recalled_memories]
        )
        if hit_rows:
            with self._connect() as conn:
                conn.executemany(
                    "INSERT INTO hit_logs (item_id, item_type, session_id, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    hit_rows,
                )

        # 4. 输出
        if format == "json":
            return self._recall_json(recalled_insights, recalled_memories)
        return self._recall_md(recalled_insights, recalled_memories)

    def format_recall(
        self,
        insights: list[Insight],
        memories: list[Memory],
        format: str = "md",
    ) -> str:
        """格式化已召回的 insight 和 memory（公共接口）。

        Args:
            insights: 已召回的 Insight 列表。
            memories: 已召回的 Memory 列表。
            format: 输出格式，'md' 或 'json'。

        Returns:
            格式化的召回内容。
        """
        if format == "json":
            return self._recall_json(insights, memories)
        return self._recall_md(insights, memories)

    def _recall_md(
        self,
        insights: list[Insight],
        memories: list[Memory],
    ) -> str:
        """以 markdown 格式输出召回内容。"""
        parts: list[str] = []

        if insights:
            parts.append("## Insights\n")
            for ins in insights:
                parts.append(
                    f"- **{ins.pattern}** → {ins.action} "
                    f"(confidence: {ins.confidence}, evidence: {ins.evidence_count})"
                )
            parts.append("")

        if memories:
            parts.append("## Memories\n")
            for mem in memories:
                parts.append(
                    f"- [{mem.kind.value}] {mem.content} "
                    f"(hits: {mem.hit_count}, confidence: {mem.confidence})"
                )
            parts.append("")

        if not parts:
            return "No memories or insights found."

        return "\n".join(parts)

    def _recall_json(
        self,
        insights: list[Insight],
        memories: list[Memory],
    ) -> str:
        """以 JSON 格式输出召回内容。"""
        import json

        data = {
            "insights": [
                {
                    "id": ins.id,
                    "pattern": ins.pattern,
                    "action": ins.action,
                    "confidence": ins.confidence,
                    "evidence_count": ins.evidence_count,
                    "tags": ins.tags,
                }
                for ins in insights
            ],
            "memories": [
                {
                    "id": mem.id,
                    "kind": mem.kind.value,
                    "content": mem.content,
                    "context": mem.context,
                    "hit_count": mem.hit_count,
                    "confidence": mem.confidence,
                    "tags": mem.tags,
                }
                for mem in memories
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Session tracking（增量 capture）
    # ------------------------------------------------------------------

    def is_session_processed(self, session_id: str) -> bool:
        """检查 session 是否已处理过。

        Args:
            session_id: Session ID。

        Returns:
            是否已处理。
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return row is not None

    def mark_session_processed(
        self, session_id: str, memory_count: int = 0
    ) -> None:
        """标记 session 为已处理。

        Args:
            session_id: Session ID。
            memory_count: 本次提取的 memory 数量。
        """
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO processed_sessions
                   (session_id, processed_at, memory_count)
                   VALUES (?, ?, ?)""",
                (session_id, int(datetime.now().timestamp()), memory_count),
            )

    def get_processed_session_ids(self) -> set[str]:
        """获取所有已处理的 session ID 集合。

        Returns:
            已处理的 session ID 集合。
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT session_id FROM processed_sessions"
            ).fetchall()
            return {row[0] for row in rows}

    # ------------------------------------------------------------------
    # Promote / Degrade
    # ------------------------------------------------------------------

    def promote(self, memory_id: str, reason: str = "") -> Insight | None:
        """将 memory 提升为 insight。

        Memory 保留，创建新 insight，写 evidence_links。

        Args:
            memory_id: 要提升的 Memory ID。
            reason: 提升原因（用作 action）。

        Returns:
            新创建的 Insight，memory 不存在时返回 None。
        """
        memory = self.get_memory(memory_id)
        if memory is None:
            return None

        now = datetime.now()
        insight = Insight(
            id=generate_id("ins"),
            pattern=memory.content,
            action=reason if reason else memory.context,
            evidence=[memory_id],
            scope=memory.scope,
            created_at=now,
            last_validated_at=now,
            evidence_count=1,
            confidence=memory.confidence,
            tags=list(memory.tags),
        )
        self.store_insight(insight)
        self.link_evidence(insight.id, memory_id)
        logger.info("Promoted memory %s to insight %s", memory_id, insight.id)
        return insight

    def degrade(self, insight_id: str, reason: str = "") -> bool:
        """降级 insight：删除 insight 文件和 evidence_links，memory 保留。

        Args:
            insight_id: 要降级的 Insight ID。
            reason: 降级原因（仅日志记录）。

        Returns:
            是否成功降级。
        """
        if reason:
            logger.info("Degrading insight %s: %s", insight_id, reason)
        return self.delete_insight(insight_id)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """返回存储统计。

        Returns:
            包含 memory/insight 数量、命中统计等的字典。
        """
        memory_count = len(list(self.memories_dir.glob("*.md")))
        insight_count = len(list(self.insights_dir.glob("*.md")))

        with self._connect() as conn:
            total_hits = conn.execute(
                "SELECT COUNT(*) FROM hit_logs"
            ).fetchone()[0]
            evidence_links = conn.execute(
                "SELECT COUNT(*) FROM evidence_links"
            ).fetchone()[0]

        return {
            "project_id": self.project_id,
            "total_memories": memory_count,
            "total_insights": insight_count,
            "total_hits": total_hits,
            "total_evidence_links": evidence_links,
            "store_path": str(self.project_dir),
        }


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------


def get_store(project_id: str, scope: Scope = Scope.PROJECT) -> InsightStore:
    """获取对应 scope 的 store。

    Args:
        project_id: 项目 ID。
        scope: 作用域。

    Returns:
        对应的 InsightStore 实例。
    """
    if scope == Scope.USER:
        return InsightStore("global")
    return InsightStore(project_id)
