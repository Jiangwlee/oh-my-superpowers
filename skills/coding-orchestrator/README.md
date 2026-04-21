# Coding Orchestrator

Spec-driven multi-agent coding coordination. The orchestrator breaks a feature into tasks, dispatches workers wave by wave, gates each task through review, and accepts when must-haves are verified.

For the executable protocol, read `SKILL.md`. This README is a human-facing map of the directory.

---

## Core Contract

The orchestrator runs in one of two modes, chosen in Phase 1 after exploration:

| Mode | Trigger | Orchestrator behavior |
|---|---|---|
| `inline` (default) | Files ≤ 10 or LOC ≤ 1000 | Writes code itself in a single wave; reviewer is still dispatched |
| `multi_wave` | Files > 10 **and** LOC > 1000 | Never writes code; delegates all coding, testing, debugging to sub-agents |

In both modes, the orchestrator owns only control-plane artifacts:

| Artifact | Role |
|---|---|
| `tasks.yaml` | Single source of truth for task state |
| `.handoff-context` | Structured checkpoint for compaction recovery |
| `tasks/task-NN.md` | Worker prompt specs (narrative only, no state) |
| `story-memory.md` | Accumulated patterns and gotchas for the story |
| `story.md` | Story narrative, `## Exploration` section, recorded `Mode` |

Reviewer sub-agent is dispatched for every task in both modes — review is never inlined.

> **Note — not the same as `skills/handoff/`.** That skill writes a session-level `.handover.md` to the project root before `/compact`. This orchestrator's `.handoff-context` is a **story-internal task checkpoint** written via `omp coding-orchestrator handoff update` on every material state change. Similar names, orthogonal mechanisms.

---

## Pipeline

```
Phase 1  Story Initialization
  └── Story Intake → Cheap Exploration → Mode Decision → Task Breakdown → Skeleton Review Gate

Phase 2  Wave Execution  [loop until all tasks completed]
  └── JIT Spec → Execute (inline writes / multi_wave dispatches) → Checkpoint → Review → Test → Accept → Advance Wave

Phase 3  E2E Testing & Acceptance
  └── E2E Test → Debug → Rerun → Accept
```

Step-by-step protocol lives in `SKILL.md`. Each phase links to its reference file for detail.

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
│   ├── constitution.md              # Karpathy's 4 principles — every sub-agent reads
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
    ├── story.py                     # story init / summarize
    ├── task.py                      # task update / show
    ├── review.py                    # review create (outputs task context fragment)
    ├── handoff.py                   # handoff update
    └── archive.py                   # archive aged / legacy stories (sweep)
```

---

## Skill-Local Agents

These agents are **not** installed globally or at project level. They live in `agents/` and are referenced by path in `SKILL.md`.

Dispatch pattern: read the agent file (body = protocol), then pass `<protocol body>\n\n<task-specific context>` as the prompt to a `general-purpose` sub-agent, stating the declared model and tool constraints explicitly.

| Agent | Model | Tools | Role |
|---|---|---|---|
| `code-reviewer` | Sonnet | Read, Grep, Glob, Bash | Review implementation vs spec; PASS / NEEDS_FIX / BLOCKED |
| `task-skeleton-reviewer` | Opus | Read, Grep, Glob, Bash | Audit skeleton; returns merge / split / rewave JSON |

---

## Key CLI Commands

```bash
# Story init — create stories/<YYYY-MM-DD>-<slug>/ from templates
omp coding-orchestrator story init --story-dir <PROJECT_ROOT>/stories --slug <name> \
  [--date <YYYY-MM-DD>] [--design-doc <path>] [--force]

# Task state
omp coding-orchestrator task update --story-dir <PROJECT_ROOT>/stories --story <slug> --id <NN> \
  --status <pending|executing|reviewing|testing|completed|blocked> \
  [--worker <id>] [--reviewer <id>] [--commit <sha>] [--note <str>] \
  [--usage-kind <worker|reviewer> --model <name> --tokens <N> --tool-uses <N> --duration-ms <N>]

# Task inspection
omp coding-orchestrator task show --story-dir <PROJECT_ROOT>/stories --story <slug> [--id <NN>]

# Handoff checkpoint
omp coding-orchestrator handoff update --story-dir <PROJECT_ROOT>/stories --story <slug> \
  --task-id <NN> --phase <executing|reviewing|accepting|advancing> \
  --next-action "<one sentence>" \
  [--worker-agent-id <id>] [--reviewer-agent-id <id>] [--commit <sha>] [--deviation <note>]

# Review context fragment (dispatch to code-reviewer agent)
omp coding-orchestrator review create --story-dir <PROJECT_ROOT>/stories --story <slug> \
  --task-id <NN> [--additional <str>] [--out <path>]

# Story-level usage report (after acceptance)
omp coding-orchestrator story summarize <slug> --story-dir <PROJECT_ROOT>/stories

# Archive aged (>1d) or legacy (no YYYY-MM-DD prefix) stories — sweep, no --story arg
omp coding-orchestrator archive --story-dir <PROJECT_ROOT>/stories [--threshold-days N] [--dry-run]
```

---

## Design Principles

| Principle | What it means |
|---|---|
| **Single source of truth** | All task state lives in `tasks.yaml`; specs are narrative only. The CLI refuses to flip a task to `executing` if `spec` is null. |
| **JIT over upfront** | Wave ≥ 2 specs stay null until prior waves complete. Upfront spec-writing ignores what workers actually learn. |
| **Gate before dispatch** | The skeleton review gate is mandatory. The orchestrator must explicitly apply or reject every merge / split / rewave suggestion before wave 1. |
| **Story memory as institutional knowledge** | `story-memory.md` accumulates patterns, gotchas, and false positives discovered during the story. Workers read it before executing; orchestrator curates it after each wave. |
