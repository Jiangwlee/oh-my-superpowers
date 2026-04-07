---
name: media-editor
description: >-
  Use when the media-editor agent needs to initialize the data directory,
  save archived media items, query the archive, or promote items to root-archive.
  Do NOT use when browsing the web, generating reports, or doing tasks unrelated
  to media archive management.
---

# media-editor Skill

数据层管理 CLI。供 media-editor Agent 调用，负责存档的读写、检索和晋升。

## CLI 命令

### init

初始化数据目录和 SQLite schema。首次使用前必须运行。

```
omp media-editor init
```

幂等操作，重复运行安全。

---

### save

保存一条媒体条目到 daily archive、SQLite 索引和 markdown card。

```
omp media-editor save --json '<item_json>'
```

`item_json` 字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | 是 | 文章 URL（唯一键） |
| title | string | 是 | 标题 |
| source | string | 是 | `x.com` 或 `reddit.com` |
| fetch_time | string | 是 | ISO 8601 时间戳 |
| tags | object | 是 | `{"L1": "Claude Code", "L2": "MCP工具"}` |
| engagement | object | 否 | `{"retweets": 0, "comments": 0}` |
| summary | string | 否 | ≤20 字摘要 |
| selected | bool | 否 | 默认 true |

输出：`{"status": "ok"}` 或 `{"status": "duplicate"}` 或 `{"status": "error", "message": "..."}`

---

### query

结构化查询存档（SQLite）。

```
omp media-editor query [--l1 <category>] [--date <YYYY-MM-DD>] [--source <x.com|reddit.com>] [--limit <n>]
```

参数：

| 参数 | 说明 | 默认 |
|------|------|------|
| `--l1` | L1 分类过滤 | 不过滤 |
| `--date` | 按采集日期过滤（YYYY-MM-DD）| 不过滤 |
| `--source` | 来源过滤 | 不过滤 |
| `--limit` | 返回条数上限 | 20 |

输出：JSON 数组。

---

### promote

将 daily archive 中的条目晋升至 root-archive，并更新用户偏好。

```
omp media-editor promote --url <url>
```

输出：`{"status": "ok"}` 或 `{"status": "duplicate"}` 或 `{"status": "not_found"}`

---

## 数据目录

默认路径：`~/.local/share/oh-my-superpowers/media-editor/`

可通过环境变量 `MEDIA_EDITOR_DATA_DIR` 覆盖。
