# Source Strategy

## Source Priority

默认优先级：

1. 官方文档 / 官方博客 / 原始仓库 / 原始论文
2. 权威研究机构 / 行业报告 / 可靠媒体
3. 技术博客 / 案例研究 / 深度文章
4. 社区讨论（Reddit / HN / 论坛）
5. 社交媒体（X 等）

越靠后，越适合补充视角，不适合作为唯一证据。

## What To Search For

研究时不要只搜一种类型的 query。优先混合：
- 概览型：`what is`, `overview`, `state of`
- 事实型：`statistics`, `data`, `market size`, `benchmarks`
- 对比型：`vs`, `comparison`, `alternatives`
- 案例型：`case study`, `implementation`, `adoption`
- 批判型：`limitations`, `criticism`, `risks`
- 时效型：`2026`, `latest`, `recent`

## When To Read Full Content

满足以下条件时，优先读全文：
- 来源看起来权威
- snippet 无法回答关键问题
- 包含数据、案例、技术细节
- 是多个来源反复提到的关键节点

读全文统一使用：

```bash
omp web-operator read-url <url> --limit 15000
```

该命令自动处理动态渲染页面，已适配站点（reddit/x/xueqiu/taoguba）走专用提取路径。不要手动拼凑 cdp 命令或使用 curl 读取页面。

## Multi-Language Search

同一主题必须用中文和英文各搜至少一次。不同语言社区的信息差异往往很大。

规则：
- 英文 query 优先用 Google + GitHub + Reddit + X
- 中文 query 优先用 Baidu + 微信搜狗
- 如果主题涉及特定语言社区（日文、韩文等），也要覆盖
- 不要只用一种语言就停下来——即使搜到了足够多的结果

## Platform Selection Matrix

根据主题类型选择互补平台组合：

| 主题类型 | 推荐平台组合 |
|---------|-------------|
| 技术/开源 | Google + GitHub + Reddit + X |
| 中文财经 | Baidu + 雪球 + 淘股吧 |
| 中文时事/政策 | Baidu + 微信搜狗 |
| 社交舆论 | X + Reddit |
| 通用研究 | Google + Baidu + DuckDuckGo |

不确定时，至少选一个英文平台 + 一个中文平台。

## Prefer search-multi

每轮搜索优先使用 `omp web-operator search-multi` 一次覆盖 2-3 个互补平台，而不是逐个平台串行搜索。

```bash
# 示例：技术主题
omp web-operator search-multi \
  --google "Claude Code memory" \
  --github "Claude Code memory" \
  --reddit "Claude Code memory" \
  --x "Claude Code memory" \
  --limit 5
```

只在需要对单个平台做精确搜索（翻页、特殊参数）时才用单平台 search。

## Cross-Source Validation

结论写入报告前，优先检查：
- 是否有至少两个独立来源支持
- 是否只是单一社区或单一作者的说法
- 是否存在明显矛盾
- 是否已经过时

如果只有单一来源支持，应在报告里标记为未充分验证。
