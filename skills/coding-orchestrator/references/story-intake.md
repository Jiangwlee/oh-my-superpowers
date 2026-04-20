# Story Intake

Two entry paths for Pipeline step 1.

## Path A — intake from brainstorming (default)

When brainstorming S3 has produced a design doc at `docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md`, generate the story skeleton from it:

1. **Archive first** (keeps active `stories/` uncluttered):
   `omp coding-orchestrator archive --story-dir <PROJECT_ROOT>/stories`
   Moves any story whose `tasks.yaml:updated` is older than 1 day (and any legacy dir missing the `YYYY-MM-DD-` prefix) into `stories/archives/`.
2. **Create the story directory** `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/` — the date prefix must match the design doc's.
3. Copy `templates/story.md` to `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story.md` and fill it in from the design doc. **First line after the title must be the design doc backlink**:
   ```markdown
   # Story: <slug>

   > Design: /docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md
   ```
4. Create `story-memory.md` placeholder (three section headers: Patterns / Gotchas / Known False Positives). See `story-memory-guideline.md` for write rules.
5. Proceed to Task Breakdown (Phase 1 step 2) — decompose the design doc into `tasks.yaml` per `task-decomposition-rules.md`.

Orchestrator never modifies the design doc. If rationale needs revision, return to brainstorming.

## Path B — self-created (fallback)

When there is no brainstorming skeleton (hotfix, direct request):

**Scale self-check** (run before continuing): if the task spans ≤ 1 wave and touches fewer than 5 files, the full orchestrator ceremony adds more overhead than value — recommend the user code directly with the main agent instead, and exit.


1. **Archive first** (keeps active `stories/` uncluttered):
   `omp coding-orchestrator archive --story-dir <PROJECT_ROOT>/stories`
   Moves any story whose `tasks.yaml:updated` is older than 1 day (and any legacy dir missing the `YYYY-MM-DD-` prefix) into `stories/archives/`.
2. **Name the directory** `<YYYY-MM-DD>-<slug>` — the date prefix is required by the archive rule and lets the orchestrator see chronology at a glance.
3. Copy `templates/story.md` to `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story.md` and fill it in.
4. Create an empty `story-memory.md` placeholder (three section headers: Patterns / Gotchas / Known False Positives).
