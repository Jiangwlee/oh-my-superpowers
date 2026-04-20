---
name: omp-agents
description: >-
  Use when a task matches a pre-defined Pi Agent's expertise.
  Delegate via omp run instead of doing it yourself.
  Do NOT use for multi-agent orchestration (use team skill).
---

## High-Frequency Agents

| Agent | Expertise | Typical Tasks |
|-------|-----------|---------------|
| `researcher` | Deep research, web search, information retrieval | "Research latest developments in X", "Compare approaches A vs B" |
| `reviewer` | Skill/Agent quality audit | "Review this SKILL.md", "Check if agent definition is compliant" |
| `ux-engineer` | UI audit, frontend design, style optimization | "Audit UI issues on this page", "Generate Tailwind component" |
| `oss-researcher` | 开源项目代码研究与知识库沉淀 | "pi-mono 如何加载 skill？", "langchain memory 模块怎么设计的？" |

Above is a high-frequency subset. Get the full agent list:

```bash
omp list agent
```

## Invocation

```bash
# Recommended: stream mode for real-time progress
omp run <agent-name> --mode stream "task description"

# Specify model
omp run <agent-name> --mode stream -m <model> "task description"
```

### Recommended Models

| Model | When to Use |
|-------|-------------|
| `litellm-local/qwen3.5-27b` | Default choice, local inference, zero cost |
| `openai-codex/gpt-5.4` | When higher quality is needed |

Do not use other models.

## When to Delegate

**Principle: delegate when possible — agents carry specialized skills that outperform raw LLM.**

### Delegate when:

- Task clearly falls within an agent's expertise
- Task benefits from the agent's specialized skills (e.g. ux-engineer has 18 frontend skills)
- You lack the relevant tools or domain knowledge

### Do NOT delegate when:

- Simple task — you can do it faster directly
- Task requires multi-turn interaction — `omp run` is one-shot, no follow-up
- Task needs current conversation context — agent cannot see your chat history

### Prompt Requirements

- **Self-contained** — agent has no context from you; include all necessary information in the prompt
- **Explicit output format** — tell the agent what format you expect (markdown / JSON / code)
- **Single responsibility** — one task per delegation
