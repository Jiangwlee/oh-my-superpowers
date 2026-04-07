# save 命令 JSON 字段定义

`omp media-editor save --json '<item_json>'` 接受以下字段：

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
