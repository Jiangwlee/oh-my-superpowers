# 搜狗微信搜索 Workflows

This reference covers the `weixin.sogou.com` (搜狗微信搜索) workflow implemented in this repository.

## 范围与限制

**重要：本站点仅提供搜索功能，不提供文章阅读功能。**

- Site: `weixin.sogou.com`
- Scripts: `scripts/sites/weixin-sogou/`
- Supported workflows: `search` (仅文章搜索，type=2)

### 为什么不提供阅读功能？

搜狗微信搜索的文章链接会跳转到 `mp.weixin.qq.com`，该域名会检测环境：
- 非微信客户端访问会触发"环境异常，完成验证后即可继续访问"
- 需要微信登录态和特殊 Cookie 才能绕过
- 因此本脚本**只获取搜索结果的元数据**，不提供全文获取

## Prerequisites

- A Chrome-family browser tab open to any page (the script will navigate it to Sogou).
- Chrome remote debugging enabled at `chrome://inspect/#remote-debugging`.
- 搜狗微信搜索不需要登录即可进行基本搜索。

## Workflow: search

### Script entrypoint

```bash
scripts/sites/weixin-sogou/search.sh <query> [limit] [target_prefix]
```

### Inputs

| Parameter | Required | Default | Notes |
|---|---|---|---|
| `query` | yes | — | 搜索关键词（中文需 URL 编码） |
| `limit` | no | 10 | 最大返回结果数；硬上限 10（单页限制） |
| `target_prefix` | no | auto | Unique `targetId` prefix from `cdp.mjs list` |

### Output schema

JSON array of search results, at most `limit` items.

```json
[
  {
    "title": "文章标题",
    "summary": "文章摘要（≤ 280 字符）",
    "account": "公众号名称",
    "time": "发布时间（如：1小时前）",
    "link": "搜狗中间链接（含 token，可人工点击打开）"
  }
]
```

| Field | Type | Notes |
|---|---|---|
| `title` | string | 文章标题，来自 `h3 a` |
| `summary` | string | 文章摘要，来自 `p.txt-info` |
| `account` | string | 公众号名称，来自 `.s-p span:first-child` |
| `time` | string | 相对发布时间，来自 `.s2` |
| `link` | string | 搜狗中间页链接，包含跳转参数和 token |

### SOP steps

1. Resolve the target tab using `sogou_find_target` (prefers weixin.sogou.com tabs, falls back to any page tab).
2. Navigate to `https://weixin.sogou.com/weixin?query=<encoded_query>&type=2&page=1&ie=utf8`.
3. Wait for URL to contain `weixin.sogou.com/weixin`.
4. Wait for `ul.news-list li` (result items) to appear in the DOM.
5. Run one `eval` to extract all result fields from list items.
6. Filter results to only include those with valid titles.
7. Emit a JSON array; each item has `title`, `summary`, `account`, `time`, and `link`.

### DOM Selectors

| Element | Selector |
|---|---|
| Result container | `ul.news-list li` |
| Title | `h3 a` |
| Summary | `p.txt-info` |
| Account | `.s-p span:first-child` |
| Time | `.s2` |
| Link | `h3 a` (href attribute) |

### Known limitations

- **单页限制**：每页最多 10 条结果，本脚本不自动翻页。
- **无全文**：返回的 `link` 需在微信环境或人工点击才能打开。
- **Token 有效期**：中间链接的 token 可能有时效限制，建议及时使用。
- **公众号搜索(type=1)**：认证公众号搜索可能返回空结果，未实现支持。

## 与微信公众号阅读的区别

| 功能 | 本脚本 | 微信客户端 |
|-----|--------|-----------|
| 搜索文章 | ✅ | ✅ |
| 获取标题/摘要 | ✅ | ✅ |
| 获取公众号名 | ✅ | ✅ |
| 阅读全文 | ❌ | ✅ |
| 点赞/评论 | ❌ | ✅ |

## 使用场景示例

```bash
# 搜索 Python 相关文章
bash scripts/sites/weixin-sogou/search.sh "Python" 5

# 搜索中文关键词
bash scripts/sites/weixin-sogou/search.sh "人工智能" 10

# 使用特定标签页
bash scripts/sites/weixin-sogou/search.sh "ChatGPT" 5 8A8D
```

输出示例：

```json
[
  {
    "title": "OpenAI 收购 Python 工具链 uv 和 Ruff",
    "summary": "uv(Python 包管理器)和 Ruff(Python linter/formatter)的开发团队...",
    "account": "crossoverJie",
    "time": "1小时前",
    "link": "https://weixin.sogou.com/link?url=...&token=..."
  }
]
```
