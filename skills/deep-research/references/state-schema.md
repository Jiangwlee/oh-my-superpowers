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
      "credibility": "high",
      "credibility_reason": "官方文档",
      "published_date": "2026-03",
      "language": "en",
      "facts": ["..."],
      "opinions": ["..."],
      "contradicts": ["S003"],
      "open_questions": ["..."]
    }
  ],
  "hypotheses": [
    {
      "claim": "memory is layered",
      "confidence": "medium",
      "status": "active",
      "source_ids": ["S001"]
    }
  ],
  "next_steps": [
    {"action": "search", "reason": "verify long-term memory", "status": "pending"}
  ],
  "report_files": {
    "brief": null,
    "full_report": null
  }
}
```

## source_notes 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `source_id` | 是 | 对应 source_index 中的 ID |
| `relevance` | 是 | high / medium / low |
| `credibility` | 是 | high / medium / low |
| `credibility_reason` | 是 | 一句话说明（官方文档 / 权威媒体 / 个人博客 / 匿名帖子等） |
| `published_date` | 否 | 来源发布时间，粗粒度即可（如 "2026-03"） |
| `language` | 否 | 来源语言（en / zh / ja 等） |
| `facts` | 是 | 提取的事实列表 |
| `opinions` | 是 | 提取的观点列表 |
| `contradicts` | 否 | 与哪些 source_id 存在矛盾 |
| `open_questions` | 否 | 该来源引出的待解问题 |

## hypotheses 字段说明

| 字段 | 说明 |
|------|------|
| `claim` | 假说内容 |
| `confidence` | high / medium / low |
| `status` | active / confirmed / rejected |
| `source_ids` | 支持该假说的来源 |

## next_steps 字段说明

| 字段 | 说明 |
|------|------|
| `action` | 动作描述 |
| `reason` | 为什么需要这步 |
| `status` | pending / done / skipped |

## update-state payload 支持的字段

- `round_log`：单轮研究日志；会追加到 `rounds.jsonl`
- `source_note`：单个 source note；按 `source_id` 覆盖/新增
- `subquestions`：完整列表；直接替换
- `hypothesis`：追加单条 hypothesis
- `next_step`：追加单条 next step
- `complete_next_step`：传入 `action` 文本，将匹配的 next_step 标记为 done
- `update_hypothesis`：传入 `{ "claim": "...", "status": "confirmed|rejected", "confidence": "..." }`，更新匹配的 hypothesis
- `status`：更新研究状态

建议：
- 原始正文不要写入 `state.json`
- 每轮结束只保留压缩后的 note / hypothesis / next step
- 完成的 next_step 及时标记为 done，被否定的 hypothesis 标记为 rejected
