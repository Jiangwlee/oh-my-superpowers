---
name: team
description: >-
  Multi-runtime orchestration patterns and prompt templates for composing
  pipelines / fan-out / discussion / batch workflows over `omp dispatch`.
  Use when planning multi-step or multi-agent workflows across claude/codex/pi.
  Do NOT use for single one-off calls (call `omp dispatch run` directly).
---

# Team: Multi-Runtime Orchestration Patterns

## Protocol

`omp dispatch run` is the **stateless transport primitive** under everything in this skill — it spawns one AI runtime in a tmux session, waits for completion, and returns ANSI-clean output. No state is persisted between calls.

The team skill layers on top: orchestration patterns (pipeline / fan-out / discussion / batch), prompt templates, and runtime selection guidance.

### Interface

```
omp dispatch run <runtime> [prompt] [options] → stdout (worker output)
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `runtime` | yes | `claude`, `codex`, or `pi` |
| `prompt` | one of | Inline prompt string (mutually exclusive with `--prompt-file`) |
| `--prompt-file` | one of | Path to prompt file (recommended for non-trivial prompts) |
| `--model` | no | Override default model |
| `--timeout` | no | Seconds before kill (default: 300) |
| `--output-file` | no | Write output to file (default: temp file) |
| `--cwd` | no | Worker's working directory (default: `$PWD`) |

### Exit Codes

| Code | Meaning | Orchestrator Action |
|------|---------|---------------------|
| `0` | Success | Read stdout / output file |
| `1` | Worker error | Check stderr, revise prompt or retry |
| `124` | Timeout | Increase `--timeout`, or split task |

### Prompt Delivery

| Runtime | Mechanism | Why |
|---------|-----------|-----|
| claude | stdin pipe (`cat file \| claude -p`) | Safe for special chars, no length limit |
| codex | stdin pipe (`cat file \| codex exec -`) | Same |
| pi | `@file` native syntax (`pi -p @file`) | Pi reads file directly |

**Never pass prompts as inline bash arguments.** Use `--prompt-file` or pipe from file.

### Runtime Details

See `references/runtime-reference.md` for per-runtime CLI flags and known limitations.

## Quick Reference

```bash
# One-shot execution
omp dispatch run <runtime> --prompt-file <path>
omp dispatch run <runtime> "<short prompt>"

# Status and cleanup
omp dispatch status [session-name]
omp dispatch clean <file>
```

> Run `omp dispatch <subcommand> --help` for full usage.

## Runtime Selection

| Runtime | Best for | Traits |
|---------|----------|--------|
| `codex` | Coding, file modification, refactoring | YOLO mode, no confirmation, direct file ops |
| `claude` | Design, review, complex reasoning | Deep thinking, judgment-heavy tasks |
| `pi` | Lightweight tasks, quick validation | Fast, low cost, simple instructions |

## Prompt Principles

One-shot execution has no retry loop — the prompt must be right the first time:

1. **Self-contained** — Worker has no memory. Include all context, code, and files in the prompt.
2. **Explicit output format** — Tell the worker what to produce (markdown / JSON / code).
3. **Working directory** — Use `--cwd` and describe project structure in the prompt.
4. **Single responsibility** — One prompt = one task. Chain multi-step work via patterns.
5. **Use templates** — See `references/prompts/` for reusable prompt structures.

## Orchestration Patterns

> How to compose multiple `omp dispatch run` calls. Load on demand.

| Pattern | Document | Topology | When to use |
|---------|----------|----------|-------------|
| Pipeline | `references/patterns/pipeline.md` | A → B → C | Sequential stages with intermediate decisions |
| Fan-out/Fan-in | `references/patterns/fan-out-fan-in.md` | Parallel → Aggregate | Multi-perspective analysis |
| Discussion | `references/patterns/discussion.md` | Multi-round convergence | Iterative multi-agent debate |
| Batch | `references/patterns/batch.md` | N parallel independent | Bulk similar tasks |

### Parallel Dispatch (all fan-out patterns)

Use `omp dispatch spawn` (returns session id immediately) + `omp dispatch wait --mode all` (or `any`):

```bash
SID_A=$(omp dispatch spawn claude --prompt-file task-a.md --session-name task-a)
SID_B=$(omp dispatch spawn codex  --prompt-file task-b.md --session-name task-b)

# Wait for all to finish
omp dispatch wait "$SID_A" "$SID_B" --mode all --timeout 600

# Collect outputs
omp dispatch tail "$SID_A"
omp dispatch tail "$SID_B"
```

Use `--mode any` to return as soon as the first finishes (others keep running).

## Prompt Templates

| Template | Document | Purpose |
|----------|----------|---------|
| Role Activation | `references/prompts/role-activation.md` | Define identity, stance, constraints for any role |
| Coding Task | `references/prompts/coding-task.md` | Assign coding implementation to worker |
| Code Review | `references/prompts/code-review.md` | Assign code review to worker |
