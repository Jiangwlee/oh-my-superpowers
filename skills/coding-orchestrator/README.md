# Coding Orchestrator

Spec-driven multi-agent coding coordination. The orchestrator breaks a feature into tasks, dispatches workers wave by wave, gates each task through review, and accepts when must-haves are verified.

---

## Core Contract

**The orchestrator never writes code.** It owns only control-plane artifacts:

- `tasks.yaml` — single source of truth for task state
- `.handoff-context` — structured checkpoint for compaction recovery
- `tasks/task-NN.md` — worker prompt specs (narrative only, no state)
- `story-memory.md` — accumulated patterns and gotchas for the story

All implementation, testing, and debugging is delegated to sub-agents.

---

## Pipeline

```
Phase 1  Story Initialization
  └── Story Intake → Task Skeleton → Skeleton Review Gate (mandatory)

Phase 2  Wave Execution  [loop until all tasks completed]
  └── Write JIT Spec → Execute → Checkpoint → Review → Test → Accept → Advance Wave

Phase 3  E2E Testing & Acceptance
  └── E2E Test → Debug → Rerun → Accept
```

### Phase 1 details

**Story Intake** (`references/story-intake.md`): resolve `PROJECT_ROOT` via `git rev-parse`, create `stories/<YYYY-MM-DD>-<slug>/` under the target project, populate `story.md` and a `tasks.yaml` skeleton.

**Task Breakdown** (`references/task-decomposition-rules.md`): decompose into tasks assigned to waves. Wave ≥ 2 leave `spec: null` — specs are written JIT once prior waves complete.

**Skeleton Review Gate**: dispatch `task-skeleton-reviewer` agent before wave 1 begins. Returns JSON with `merge`, `split`, `rewave` suggestions. Orchestrator applies or explicitly rejects each before dispatching.

### Phase 2 details

- **JIT Spec**: for each upcoming wave, copy `templates/task.md`, fill Objective / Read First / File Scope / Acceptance Criteria / Test Plan. Set `spec:` in `tasks.yaml`. Only then flip status to `executing`.
- **Execute**: route worker by capability level (see Routing). Write prompt to `/tmp/orchestrator-task-NN.md`, dispatch sub-agent or tmux session.
- **Checkpoint**: after each state change, update `.handoff-context` via `omp coding-orchestrator handoff update ...` — enables compaction recovery.
- **Review**: generate task context via `omp coding-orchestrator review create ...`, dispatch `code-reviewer` agent (see Agents). Apply second judgment; workers execute any fixes.
- **Accept** (`references/acceptance.md`): verify all must-haves; mark `completed`.

---

## Directory Layout

```
coding-orchestrator/
├── SKILL.md                         # Orchestrator instructions (loaded by Claude Code)
├── README.md                        # This file
│
├── agents/                          # Skill-local agents (not distributed globally)
│   ├── code-reviewer.md             # Sonnet · Read/Grep/Glob/Bash only
│   └── task-skeleton-reviewer.md    # Opus  · Read/Grep/Glob/Bash only
│
├── references/                      # Protocol documents (loaded on demand)
│   ├── constitution.md              # Karpathy's 4 principles — all agents must read
│   ├── dispatch-routes.md           # Capability routing + review/test/debug protocol
│   ├── task-decomposition-rules.md  # 5 decomposition rules + JIT spec protocol
│   ├── storage-layout.md            # PROJECT_ROOT resolution + stories/ layout
│   ├── story-intake.md              # Story initialization steps
│   ├── acceptance.md                # Task acceptance protocol
│   ├── story-memory-guideline.md    # What to capture in story-memory.md
│   ├── handoff-guideline.md         # Compaction recovery protocol
│   └── commands.md                  # tmux spawn commands for external runtimes
│
├── templates/                       # Copy-and-fill templates
│   ├── task.md                      # Worker prompt template
│   ├── story.md                     # Story narrative template
│   ├── tasks.yaml                   # tasks.yaml skeleton
│   └── handoff-context.yaml         # .handoff-context skeleton
│
├── worker-refs/                     # Behavioral docs injected into worker prompts
│   ├── worker-guideline.md          # Worker behavioral protocol
│   └── debugging-guideline.md       # Debugging + escalation protocol
│
└── scripts/                         # CLI backends (invoked via `omp coding-orchestrator`)
    ├── common.py                    # Shared utilities (load_yaml, require_story_dir)
    ├── story.py                     # story init/list
    ├── task.py                      # task update/list/show
    ├── review.py                    # review create (outputs task context fragment)
    ├── handoff.py                   # handoff update/show
    └── archive.py                   # archive completed stories
```

---

## Skill-Local Agents

These agents are **not** installed globally or at project level. They live in `agents/` and are referenced by path in SKILL.md's Agents table.

**Dispatch pattern**: read the agent file to load the protocol body → pass `<protocol body>\n\n<task-specific context>` as the dispatch prompt to a `general-purpose` sub-agent with the agent's declared model and tool constraints stated explicitly.

| Agent | Model | Tools | Role |
|---|---|---|---|
| `code-reviewer` | Sonnet | Read, Grep, Glob, Bash | Review implementation vs spec; PASS/NEEDS_FIX/BLOCKED |
| `task-skeleton-reviewer` | Opus | Read, Grep, Glob, Bash | Audit task skeleton; returns merge/split/rewave JSON |

---

## Capability Routing

Route workers and reviewers by task complexity, not by preference.

| Level | Use for | Claude | Codex |
|---|---|---|---|
| L1 | Templates, low-risk mechanical work | Haiku 4.5 | gpt-5.4-mini |
| L2 | Standard feature coding and review | Sonnet 4.6 | gpt-5.4-mini / gpt-5.3-codex |
| L3 | Concurrency, async boundaries, skeleton review | Opus 4.7 | gpt-5.4 |
| L4 | Frontier coding spikes | — | gpt-5.4 |

**Route decision**: use native sub-agent (`Agent()`) when the task runs in the same runtime. Use tmux (`references/commands.md`) when targeting a different runtime or when the task needs isolation.

---

## Task Decomposition Rules (summary)

Full protocol: `references/task-decomposition-rules.md`.

| Rule | Constraint |
|---|---|
| **1. Test Layer Match** | First red test must be at the highest layer the acceptance criteria touch. No unit tests for integration-level acceptance. |
| **2. Cross-Layer Wiring** | Adding a shared API and wiring its first consumer must happen in the same task. Never split "add store action" from "wire component". |
| **3. Surgical Fix Batching** | Fixes ≤ 30 lines, sharing one verification cycle, up to 3 per batch → single fix-batch task. |
| **4. Verification Ownership** | Implementation task owns its E2E verification. No standalone "run and verify" tasks. |
| **5. Vertical Slice Sizing** | One task = one vertical slice (model + API + view + test). Split vertically, never horizontally. Max ~5 files. |

---

## Key CLI Commands

```bash
# Story
omp coding-orchestrator story init --story-dir <PROJECT_ROOT>/stories --slug <name>

# Task state
omp coding-orchestrator task update --story-dir <dir> --story <slug> --id <NN> \
  --status <pending|executing|reviewing|testing|completed> \
  [--worker <id>] [--reviewer <id>] [--commit <sha>] [--note <str>]

# Handoff checkpoint
omp coding-orchestrator handoff update --story-dir <dir> --story <slug> \
  --task-id <NN> --phase <executing|reviewing|accepting|advancing> \
  --next-action "<one sentence>"

# Review context fragment (dispatch to code-reviewer agent)
omp coding-orchestrator review create --story-dir <dir> --story <slug> \
  --task-id <NN> [--additional <str>] [--out <path>]

# Archive completed story
omp coding-orchestrator archive --story-dir <dir> --story <slug>
```

---

## Compaction Recovery

On context compaction or session resume, read `.handoff-context` first. The `next_action` field is the primary recovery signal. Full protocol: `references/handoff-guideline.md`.

---

## Design Principles

**Single source of truth**: all task state lives in `tasks.yaml`; task specs are narrative only. The CLI enforces this — it refuses to flip a task to `executing` if `spec` is null.

**JIT over upfront**: wave ≥ 2 specs are intentionally left null until prior waves complete. Upfront spec-writing ignores what workers actually learn.

**Gate before dispatch**: the skeleton review gate is mandatory, not optional. The orchestrator must explicitly apply or reject every merge/split/rewave suggestion before wave 1 begins.

**Story memory as institutional knowledge**: `story-memory.md` accumulates patterns, gotchas, and false positives discovered during the story. Every worker reads it before executing; the orchestrator updates it after each wave.
