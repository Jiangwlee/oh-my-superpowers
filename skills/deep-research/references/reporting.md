# Reporting

Write two Markdown reports first; `build-report` then generates the HTML page.

## `brief.md`

Purpose: decision-ready summary. Keep it short.

```markdown
# <研究主题>

## 核心结论
1. <结论>（来源：<url 或来源名>）

## 关键分歧 / 风险
- <分歧、限制或风险>

## 推荐下一步
- <可执行下一步>
```

Rules:

- Write 3-7 conclusions.
- Every conclusion must cite a source.
- Do not pad with background.

## `full-report.md`

Purpose: audit trail. Record how the conclusion was reached.

```markdown
# <研究主题>

## 研究目标
- <用户真正想知道的问题>

## 子问题分解
- [ ] <子问题>（状态：open|partial|answered）

## 研究日志

### Round 1
- 目标：<本轮验证什么>
- 平台 / 查询：<平台和 query>
- 来源：<关键 URL>
- 发现：<关键发现>
- 为什么继续：<继续或停止原因>

## 关键来源汇总

| 来源 | 平台 | 摘要 |
|------|------|------|
| <url> | <platform> | <一句话证据价值> |

## 综合结论
- 事实：<来源直接支持的事实>
- 观点：<来源中的判断>
- 推断：<跨来源综合后的判断>

## 未解决问题
- <仍待验证的问题>
```

Rules:

- Separate facts, opinions, and inferences.
- Each round must show platform, query, full-text sources, findings, and reason to continue or stop.
- Do not paste webpage full text.
