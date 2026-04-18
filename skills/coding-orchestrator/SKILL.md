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

1. **Story Intake** — understand the requirement, create `<PROJECT_ROOT>/stories/<name>/story.md`
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
    - templates/story.md                  Story 模板（叙事，纯 markdown）
    - templates/tasks.yaml                任务状态模板（单一事实来源）
    - templates/task.md                   Task Spec 模板（worker prompt，不含 frontmatter）
    - templates/handoff.md                Handoff 文件模板
-->

## Story Intake

1. **Archive first** (keeps active `stories/` uncluttered):
   `omp coding-orchestrator archive --story-dir <PROJECT_ROOT>/stories`
   Moves any story whose `tasks.yaml:updated` is older than 1 day (and any
   legacy dir missing the `YYYY-MM-DD-` prefix) into `stories/archives/`.
2. **Name the directory** `<YYYY-MM-DD>-<slug>` — the date prefix is required
   by the archive rule and lets the orchestrator see chronology at a glance.
3. Copy `templates/story.md` to `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story.md` and fill it in.

## Task Breakdown

**Before writing any task spec, read `references/task-decomposition-rules.md`.** It encodes hard rules for test-layer match, cross-layer API wiring, surgical-fix batching, and verification-task folding — all derived from real story post-mortems where ignoring them cost 5-10 extra fix-loop tasks.

First write `tasks.yaml` (state), then one `task-NN.md` (worker prompt) per task.

1. Copy `templates/tasks.yaml` to `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/tasks.yaml`.
   Set `story`, `created`, `updated`, and one entry per task: `id`, `title`,
   `wave`, `depends_on`, `spec`, `files_modified`, `test_layer`.
   `test_layer` = the lowest layer that can falsify acceptance (per Rule 1).
2. For each task, copy `templates/task.md` to `tasks/task-NN.md` and fill:
   - `Objective`, `Read First`, `File Scope`
   - `Deviation Rules` — what the sub agent can auto-fix vs must ask about
   - `Must-Haves` — goal-backward acceptance (truths + artifacts + key_links)
   - `Test Plan` — first red test at the `test_layer` declared in tasks.yaml

**Freedom note**: appending, reordering, or removing tasks is a direct
`tasks.yaml` edit. The `omp coding-orchestrator task` command is only for
the high-frequency fields (status / worker / reviewer / commit / note).

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
1. Path to the task spec file: `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/tasks/task-NN.md`
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

1. Flip status to `reviewing` **before** dispatching the reviewer:
   `omp coding-orchestrator task update --story <slug> --id NN --status reviewing --reviewer <id>`
2. Dispatch a reviewer (different from the coder when possible):
   - Write review prompt to `/tmp/orchestrator-review-<NN>.md` (include: task spec path, changed files, diff)
   - Use the same route decision as Execute: sub-agent or tmux
   - Recommended: use a reasoning-focused runtime for review (e.g., Claude for review, Codex for coding)
3. Orchestrator reads the review result and applies **second judgment**:
   - Confirmed issue → orchestrator fixes directly (small fix) or dispatches worker (large fix);
     flip back to `executing` while the fix is in flight
   - False positive → ignore, add `--note "..."` explaining why
4. When the review is resolved, advance to the Test phase:
   `omp coding-orchestrator task update --story <slug> --id NN --status testing`
   (append `--commit <hash>` for any fix commit produced during review)

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
5. All pass →
   `omp coding-orchestrator task update --story <slug> --id NN --status completed`
   (appends commit hash with `--commit <hash>` when relevant)

When all tasks in `tasks.yaml` show `status: completed` → story complete.

## Compaction Recovery

If context was compressed, read `<PROJECT_ROOT>/stories/.handoff-context` to restore state.
For details on the handoff mechanism: read `references/handoff-guideline.md`.

## Storage

<HARD-RULE>
`stories/` MUST live at the **target project's root directory** — NEVER at the
orchestrator's cwd, NEVER inside the skill's own repo, NEVER inside a sub-directory
of the project. The orchestrator's cwd at invocation time is unreliable (it may be
the skill directory, a worktree, or anywhere else the user happened to be).
</HARD-RULE>

### Resolving `<PROJECT_ROOT>`

Before creating any story file, resolve the project root **deterministically**:

1. If the user explicitly named a project path → use it.
2. Otherwise run `git rev-parse --show-toplevel` from the user's working context.
   - If it returns a path → that is `<PROJECT_ROOT>`.
   - If it errors (no git repo) → STOP and ask the user "where should `stories/` live?". Do not guess, do not fall back to cwd.
3. Sanity-check the resolved path is NOT inside the skill's own repo
   (`~/Projects/oh-my-superpowers/` or wherever this skill is installed).
   If it is → STOP and ask the user. The skill repo is never a valid target.

Record the resolved `<PROJECT_ROOT>` in the first task you create and reuse it for the entire story — do not re-resolve mid-story.

### Layout

```
<PROJECT_ROOT>/stories/             # MUST be in project's .gitignore
├── .handoff-context                # PostCompact recovery file
├── archives/                       # auto-populated by `omp coding-orchestrator archive`
│   └── <YYYY-MM-DD>-<slug>/        # aged or legacy stories land here
└── <YYYY-MM-DD>-<slug>/            # active story (date prefix required)
    ├── story.md                    # story narrative (goal, context, scope)
    ├── tasks.yaml                  # single source of truth for task state
    ├── handoff.md                  # handoff state (auto/manual)
    └── tasks/
        ├── task-01.md              # worker prompt only (no frontmatter)
        ├── task-02.md
        └── ...
```

### .gitignore check (one-time per project)

After resolving `<PROJECT_ROOT>`, verify `stories/` (or `/stories/`) is in
`<PROJECT_ROOT>/.gitignore`. If not, append it before creating any story file.
This prevents orchestrator working files from leaking into project commits.
