---
name: coding-orchestrator
description: >-
  Spec-driven coding orchestration with sub-agent dispatch.
  Trigger: user says "orchestrate", acts as orchestrator, or invokes
  via slash command. Breaks work into task specs, dispatches sub-agents
  for coding/review/testing, tracks progress across context compactions.
---

# Coding Orchestrator: Spec-Driven Sub-Agent Orchestration

<HARD-GATE>
The orchestrator does NOT write code. All coding, design, testing, and
debugging is delegated to sub agents. If you catch yourself writing
implementation code, STOP — you are violating the orchestrator contract.
</HARD-GATE>

## Pipeline

**Before starting**: read `references/constitution.md` — applies to all roles including the orchestrator.

Create a task for each step and complete them in order:

1. **Story Intake** — understand the requirement, create `./stories/<name>/story.md`
2. **Task Breakdown** — decompose into tasks, create spec per task; read `templates/task.md`
3. **Execute** — dispatch sub agents for coding (worktree isolation for parallel)
4. **Review** — dispatch sub agent for code review + orchestrator second judgment
5. **Test & Debug** — on failure, sub agent reads `worker-refs/debugging-guideline.md`
6. **Acceptance** — verify must_haves from each task spec

<!--
  Load on demand, never all at once:

  references/ (orchestrator reads):
    - references/constitution.md             全局编码准则（全员必读，Karpathy 四原则）
    - references/task-decomposition-rules.md 任务拆分铁律（Test Layer Match / Cross-Layer Wiring / Fix Batching / etc.）
    - references/commands.md                 tmux dispatch 命令（走 tmux 路线时加载）
    - references/handoff-guideline.md        Handoff 格式 + 恢复流程

  worker-refs/ (worker reads, orchestrator only传路径):
    - worker-refs/worker-guideline.md     Worker 行为协议
    - worker-refs/debugging-guideline.md  日志驱动调试方法论

  templates/ (orchestrator复制填充):
    - templates/task.md                   Task Spec 模板
    - templates/story.md                  Story 模板
    - templates/handoff.md                Handoff 文件模板
-->

## Story Intake

Understand the user's intent. Copy `templates/story.md` to `./stories/<story-name>/story.md` and fill it in.

## Task Breakdown

**Before writing any task spec, read `references/task-decomposition-rules.md`.** It encodes hard rules for test-layer match, cross-layer API wiring, surgical-fix batching, and verification-task folding — all derived from real story post-mortems where ignoring them cost 5-10 extra fix-loop tasks.

Read `templates/task.md`, then for each task:

1. Define a clear, independently verifiable objective
2. List `Read First` files the sub agent must read before modifying anything
3. List `File Scope` — only these files may be modified
4. Write `Deviation Rules` — what the sub agent can auto-fix vs must ask about
5. Write `Must-Haves` — goal-backward acceptance (truths + artifacts + key_links)
6. Set `test_layer:` in frontmatter — the lowest layer that can falsify acceptance (per Rule 1)
7. Save as `./stories/<story-name>/tasks/task-NN.md`

**Sizing rule**: one task = one vertical slice. If a task touches more than 5 files, split it — but split **vertically** (two smaller features), not **horizontally** (all stores, then all components). See Rule 5 in `references/task-decomposition-rules.md`.

**Self-check before dispatching**: run the checklist at the bottom of `references/task-decomposition-rules.md` against your task list. Revise before dispatching if any answer is "no".

## Execute

For each task (orchestrator dispatches in dependency order):

<dispatch_protocol>

### Route Decision

Before dispatching, determine your dispatch route:

| Condition | Route | Example |
|-----------|-------|---------|
| You have native sub-agent AND task runs in same runtime | **Sub-agent** | Claude Code's `Agent()` tool |
| You need a different runtime OR no sub-agent mechanism | **tmux** | Read `references/commands.md` |

### Prompt Preparation (both routes)

Write a prompt file at `/tmp/orchestrator-task-<NN>.md` containing:
1. Path to the task spec file: `./stories/<story-name>/tasks/task-NN.md`
2. One sentence: "Read the spec, then read every file in its Worker Refs and Read First sections, then execute."

The task spec's **Worker Refs** section lists all behavioral docs (constitution, worker-guideline, etc.) the worker must read.

**No-spec fallback**: only when there is no spec file (e.g., urgent hotfix), inject the task description directly into the prompt.

### Sub-agent Route

Dispatch using your runtime's native sub-agent mechanism. Pass the prompt file path.

### tmux Route

Read `references/commands.md` for exact commands. Key steps:
1. Write prompt to file
2. Spawn tmux session with the appropriate runtime command
3. Poll until session exits
4. Read output file

**Parallel execution**: tasks without dependencies may run in parallel.
- Sub-agent route: use your runtime's isolation mechanism (e.g., worktree)
- tmux route: spawn multiple tmux sessions + git worktree (see `references/commands.md`)

</dispatch_protocol>

## Review

After each task's code is written:

1. Dispatch a reviewer (different from the coder when possible):
   - Write review prompt to `/tmp/orchestrator-review-<NN>.md` (include: task spec path, changed files, diff)
   - Use the same route decision as Execute: sub-agent or tmux
   - Recommended: use a reasoning-focused runtime for review (e.g., Claude for review, Codex for coding)
2. Orchestrator reads the review result and applies **second judgment**:
   - Confirmed issue → orchestrator fixes directly (small fix) or dispatches worker (large fix)
   - False positive → ignore, note in task progress
3. Update task progress

## Test & Debug

Sub agent runs tests defined in the task spec's Test Plan.

On failure:
1. Sub agent reads `worker-refs/debugging-guideline.md` (should already be in task spec's Worker Refs)
2. Follow log-driven debugging: list causes → add diagnostic logs → read logs → narrow scope → fix → clean up
3. **Iteration limit**: max 3 fix attempts per task

## Failure Escalation

```
Sub agent fails or 3 attempts exhausted
    → Escalate to a different sub agent
        → Orchestrator takes over (this task only)
```

Each escalation carries: error logs, attempted fixes, current hypothesis.

## Acceptance

For each completed task:
1. Read the task spec's `Must-Haves` section
2. Verify each `truth` — is the behavior observable?
3. Verify each `artifact` — does the file exist with expected content?
4. Verify each `key_link` — does the regex pattern match?
5. All pass → mark task complete in `story.md`

When all tasks pass → story complete.

## Compaction Recovery

If context was compressed, read `./stories/.handoff-context` to restore state.
For details on the handoff mechanism: read `references/handoff-guideline.md`.

## Storage

```
./stories/                          # add to .gitignore
├── .handoff-context                # PostCompact recovery file
└── <story-name>/
    ├── story.md                    # story overview + global progress
    ├── handoff.md                  # handoff state (auto/manual)
    └── tasks/
        ├── task-01.md              # task spec (with progress)
        ├── task-02.md
        └── ...
```
