# Storage Layout

<HARD-RULE>
`stories/` MUST live at the **target project's root directory** — NEVER at the orchestrator's cwd, NEVER inside the skill's own repo, NEVER inside a sub-directory of the project. The orchestrator's cwd at invocation time is unreliable (it may be the skill directory, a worktree, or anywhere else the user happened to be).
</HARD-RULE>

## Resolving `<PROJECT_ROOT>`

Before creating any story file, resolve the project root **deterministically**:

1. If the user explicitly named a project path → use it.
2. Otherwise run `git rev-parse --show-toplevel` from the user's working context.
   - If it returns a path → that is `<PROJECT_ROOT>`.
   - If it errors (no git repo) → STOP and ask the user "where should `stories/` live?". Do not guess, do not fall back to cwd.
3. Sanity-check the resolved path is NOT inside the skill's own repo (`~/Projects/oh-my-superpowers/` or wherever this skill is installed). If it is → STOP and ask the user. The skill repo is never a valid target.

Record the resolved `<PROJECT_ROOT>` in the first task you create and reuse it for the entire story — do not re-resolve mid-story.

## Layout

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

## .gitignore check (one-time per project)

After resolving `<PROJECT_ROOT>`, verify `stories/` (or `/stories/`) is in `<PROJECT_ROOT>/.gitignore`. If not, append it before creating any story file. This prevents orchestrator working files from leaking into project commits.
