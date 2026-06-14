# Source Strategy

Use complementary sources. Do not let one platform or one language define the answer.

## Priority

Prefer primary and verifiable sources:

1. Official docs, official blogs, original repos, original papers
2. Research institutions, industry reports, reliable media
3. Technical blogs, case studies, long-form analysis
4. Community discussion: Reddit, HN, forums
5. Social media: X and similar platforms

Lower-priority sources can add viewpoints, but should not be the only evidence for a key conclusion.

## Query Mix

Each round should mix query intent:

| Intent | Use for |
|---|---|
| Overview | map the topic and vocabulary |
| Fact/data | find numbers, benchmarks, market size, timelines |
| Comparison | find alternatives and tradeoffs |
| Case | find adoption, implementation, failures |
| Critical | find limitations, criticism, risks |
| Recent | find latest changes and current status |

## Full-text Reading

Read full text when a source is authoritative, repeatedly cited, data-heavy, or needed to answer a key subquestion.

```bash
omp web-operator read-url <url> --limit 15000
```

`read-url` handles dynamic sites through site-specific paths. Do not replace it with curl or custom CDP.

## Language Coverage

Search Chinese and English at least once unless the topic is explicitly single-language.

| Topic | Platform mix |
|---|---|
| Tech / OSS | Google + GitHub + Reddit + X |
| Chinese finance | Baidu + 雪球 + 淘股吧 |
| Chinese policy / current events | Baidu + 微信搜狗 |
| Social sentiment | X + Reddit |
| General research | Google + Baidu + DuckDuckGo |

When unsure, use at least one English platform and one Chinese platform.

## Search Command

Prefer one `search-multi` call per round:

```bash
omp web-operator search-multi \
  --google "Claude Code memory" \
  --github "Claude Code memory" \
  --reddit "Claude Code memory" \
  --limit 5
```

Use single-platform `search` only for precise follow-up or platform-specific options. Its arguments are positional:

```bash
omp web-operator search google "Claude Code memory" 5
```

Do not use non-existent option forms such as `--platform google`, `--query`, or `--limit` with `search`.

## Evidence Check

Before reporting a conclusion, ask:

- Do at least two independent sources support it?
- Is it only one community or one author’s view?
- Is there a contradiction?
- Is the source outdated?

Mark single-source conclusions as `未充分验证`.
