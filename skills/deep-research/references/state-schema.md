# State Schema

`state.json` 的核心结构：

```json
{
  "topic": "Claude Code memory",
  "slug": "claude-code-memory",
  "mode": "default",
  "workspace": "/abs/path",
  "status": "initialized",
  "subquestions": [
    {"question": "memory patterns", "status": "open"}
  ],
  "source_index": [
    {
      "source_id": "S001",
      "title": "Example",
      "url": "https://example.com",
      "platform": "google",
      "raw_file": "/abs/path/raw/S001.txt",
      "meta_file": "/abs/path/raw/S001.meta.json"
    }
  ],
  "source_notes": [
    {
      "source_id": "S001",
      "relevance": "high",
      "facts": ["..."],
      "opinions": ["..."],
      "open_questions": ["..."]
    }
  ],
  "hypotheses": [
    {
      "claim": "memory is layered",
      "confidence": "medium",
      "source_ids": ["S001"]
    }
  ],
  "next_steps": [
    {"action": "search", "reason": "verify long-term memory"}
  ],
  "report_files": {
    "brief": null,
    "full_report": null
  }
}
```

`omp-deep-research update-state` 的 `payload-file` 支持的字段：

- `round_log`：单轮研究日志；会追加到 `rounds.jsonl`
- `source_note`：单个 source note；按 `source_id` 覆盖/新增
- `subquestions`：完整列表；直接替换
- `hypothesis`：追加单条 hypothesis
- `next_step`：追加单条 next step
- `status`：更新研究状态

建议：
- 原始正文不要写入 `state.json`
- 每轮结束只保留压缩后的 note / hypothesis / next step
