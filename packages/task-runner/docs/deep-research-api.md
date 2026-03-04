# Deep Research API 使用指南

## 接口概述

`GET /ashare/deep-research/data` - 读取单只股票的深研数据

## 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `code` | string | 是 | - | 股票代码（如：002050） |
| `format` | string | 否 | json | 返回格式：`json` 或 `markdown` |

## 响应格式

### JSON 格式（默认）

返回完整的原始数据结构：

```json
{
  "status": "success",
  "result": {
    "code": "002050",
    "name": "三花智控",
    "last_collected_at": "2026-03-04 12:00:00",
    "raw_em": {
      "latest_posts": [...],
      "stock_infos": [...],
      "stock_notices_recent": [...]
    },
    "raw_tgb": {
      "stock_tags": [...],
      "quotes_posts": [...],
      "zh_recommend": [...]
    },
    "has_brief": false
  }
}
```

### Markdown 格式

返回格式化后的文本摘要，包含以下核心信息：

```markdown
# 三花智控 (002050)

## 基本信息

- **代码**: 002050
- **名称**: 三花智控
- **采集时间**: 2026-03-04 12:00:00

## 股票标签

- 机器人
- 热管理
- 绩优

## 东方财富股吧

### 最新帖子

1. **三花智控：机器人概念龙头** (2026-03-04 10:30:00)
2. **关注机器人板块机会** (2026-03-04 09:15:00)

## 淘股吧

### 讨论贴

| 序号 | 帖子标题 | 发帖时间 | 内容摘要 |
|------|----------|----------|----------|
| 1 | 深度分析三花智控未来走势 | 2026-03-04 11:20:00 | 从基本面看... |
```

Markdown 格式只保留核心信息：
- **股票信息**：名称、代码、采集时间
- **股票标签**：淘股吧标签列表
- **东方财富股吧**：列表形式展示帖子标题和发帖时间
- **淘股吧**：表格形式展示帖子标题、发帖时间和内容摘要（前 50 字）

## 错误响应

### 股票不存在

```json
{
  "status": "failed",
  "error": "not_found: 999999"
}
```

### 无效格式参数

```json
{
  "status": "failed",
  "error": "invalid_format: xml (supported: json, markdown)"
}
```

## 使用示例

### cURL 示例

```bash
# 获取 JSON 格式数据
curl "http://localhost:8000/ashare/deep-research/data?code=002050"

# 获取 Markdown 格式数据
curl "http://localhost:8000/ashare/deep-research/data?code=002050&format=markdown"
```

### Python 示例

```python
import requests

# JSON 格式
resp = requests.get("http://localhost:8000/ashare/deep-research/data", 
                    params={"code": "002050"})
data = resp.json()["result"]

# Markdown 格式
resp = requests.get("http://localhost:8000/ashare/deep-research/data", 
                    params={"code": "002050", "format": "markdown"})
md_content = resp.json()["result"]
```

## 限制说明

- 东方财富股吧帖子最多显示 20 条
- 淘股吧帖子最多显示 20 条
- 内容摘要是前 50 个字符，超过部分用 `...` 截断
- 特殊字符（如 `|`）会自动转义，防止破坏 Markdown 格式
