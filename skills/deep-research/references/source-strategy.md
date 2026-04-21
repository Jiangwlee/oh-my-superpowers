# Source Strategy

## Source Priority

默认优先级（越靠后越适合补视角，不适合作唯一证据）：

1. 官方文档 / 官方博客 / 原始仓库 / 原始论文
2. 权威研究机构 / 行业报告 / 可靠媒体
3. 技术博客 / 案例研究 / 深度文章
4. 社区讨论（Reddit / HN / 论坛）
5. 社交媒体（X 等）

## Query 类型混搭

每轮搜索优先混合以下类型，不要只用一种：

| 类型 | 示例关键词 |
|---|---|
| 概览型 | `what is`, `overview`, `state of` |
| 事实型 | `statistics`, `data`, `market size`, `benchmarks` |
| 对比型 | `vs`, `comparison`, `alternatives` |
| 案例型 | `case study`, `implementation`, `adoption` |
| 批判型 | `limitations`, `criticism`, `risks` |
| 时效型 | `2026`, `latest`, `recent` |

## 何时读全文

满足任一条件时优先读全文，不只看 snippet：

- 来源权威
- snippet 回答不了关键问题
- 含数据、案例、技术细节
- 多来源反复提到的关键节点

统一命令：

```bash
omp web-operator read-url <url> --limit 15000
```

自动处理动态渲染；reddit / x / xueqiu / taoguba 走专用提取路径。不要手搓 CDP 或 curl。

## 多语言覆盖

**同一主题中文和英文各搜至少一次**，不同语言社区信息差异往往很大。

- 英文：Google + GitHub + Reddit + X
- 中文：Baidu + 微信搜狗
- 日文 / 韩文等：涉及时也要覆盖
- 搜到足够结果也不能只停在一种语言

## 平台选择矩阵

按主题类型组合互补平台：

| 主题类型 | 推荐组合 |
|---|---|
| 技术 / 开源 | Google + GitHub + Reddit + X |
| 中文财经 | Baidu + 雪球 + 淘股吧 |
| 中文时事 / 政策 | Baidu + 微信搜狗 |
| 社交舆论 | X + Reddit |
| 通用研究 | Google + Baidu + DuckDuckGo |

不确定时至少一个英文平台 + 一个中文平台。

## 优先 search-multi

每轮用 `omp web-operator search-multi` 一次覆盖 2-3 个互补平台，不要逐平台串行搜。

```bash
omp web-operator search-multi \
  --google "Claude Code memory" \
  --github "Claude Code memory" \
  --reddit "Claude Code memory" \
  --x "Claude Code memory" \
  --limit 5
```

只有单平台精确搜索（翻页、特殊参数）才退到单平台 `search`。

## 跨来源校验

结论写入报告前检查：

- 是否至少两个独立来源支持
- 是否只是单一社区 / 单一作者的说法
- 是否存在明显矛盾
- 是否已过时

只有单一来源支持时，报告里必须标记"未充分验证"。
