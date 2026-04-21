# Story Intake

Two entry paths for Pipeline step 1.

## Path A — intake from brainstorming (default)

When brainstorming S3 has produced a design doc at `docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md`, generate the story skeleton from it:

1. **Archive first** (keeps active `stories/` uncluttered):
   `omp coding-orchestrator archive --story-dir <PROJECT_ROOT>/stories`
   Moves any story whose `tasks.yaml:updated` is older than 1 day (and any legacy dir missing the `YYYY-MM-DD-` prefix) into `stories/archives/`.
2. **Create the story** with the CLI — date prefix matches the design doc's:
   ```bash
   omp coding-orchestrator story init \
     --story-dir <PROJECT_ROOT>/stories \
     --slug <slug> \
     --date <YYYY-MM-DD> \
     --design-doc /docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md
   ```
   This creates `stories/<YYYY-MM-DD>-<slug>/` with `story.md` (carrying the design backlink as the first line after the title), `tasks.yaml` (empty `tasks: []`), `story-memory.md` (Patterns / Gotchas / Known False Positives placeholders), and an empty `tasks/` directory.
3. Fill `story.md` Goal / Context / Scope sections from the design doc.
4. Proceed to Task Breakdown (Phase 1 step 2) — decompose the design doc into `tasks.yaml` per `task-decomposition-rules.md`. See `story-memory-guideline.md` for memory write rules.

Orchestrator never modifies the design doc. If rationale needs revision, return to brainstorming.

## Path B — self-created (fallback)

When there is no brainstorming skeleton (hotfix, direct request):

**Scale self-check** (run before continuing): if the task spans ≤ 1 wave and touches fewer than 5 files, the full orchestrator ceremony adds more overhead than value — recommend the user code directly with the main agent instead, and exit.

1. **Archive first** (keeps active `stories/` uncluttered):
   `omp coding-orchestrator archive --story-dir <PROJECT_ROOT>/stories`
2. **Create the story** with the CLI (omit `--design-doc`):
   ```bash
   omp coding-orchestrator story init --story-dir <PROJECT_ROOT>/stories --slug <slug>
   ```
   `--date` defaults to today; the date prefix is required by the archive rule and gives orchestrator chronology at a glance.
3. Fill `story.md` Goal / Context / Scope sections.
