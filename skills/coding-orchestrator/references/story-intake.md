# Story Intake

Two entry paths for Pipeline step 1.

## Path A — handoff from brainstorming (default)

When `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/` already exists with the four-artifact chain written by brainstorming S3 (see `skills/brainstorming/scenarios/feature.md`), **do not create — validate**:

1. Assert the four artifacts exist: `story.md`, `tasks.yaml`, `story-memory.md`, `tasks/task-01.md`.
2. Assert `story.md` has the `> Design: /docs/brainstorming/specs/<...>.md` backlink on its first non-title line.
3. Run the task-decomposition self-check at the bottom of `task-decomposition-rules.md` against the incoming skeleton. Any "no" answer → return control to brainstorming with the specific failure, do not silently reshape the skeleton.
4. Assert wave-1 tasks have non-null `spec` pointing to an existing `tasks/task-NN.md`; wave≥2 tasks have `spec: null` (JIT slots).
5. Proceed to Task Breakdown § Wave 1.

Orchestrator never modifies `story.md` or the design doc. If rationale needs revision, return to brainstorming.

## Path B — self-created (fallback)

When there is no brainstorming skeleton (hotfix, direct request):

1. **Archive first** (keeps active `stories/` uncluttered):
   `omp coding-orchestrator archive --story-dir <PROJECT_ROOT>/stories`
   Moves any story whose `tasks.yaml:updated` is older than 1 day (and any legacy dir missing the `YYYY-MM-DD-` prefix) into `stories/archives/`.
2. **Name the directory** `<YYYY-MM-DD>-<slug>` — the date prefix is required by the archive rule and lets the orchestrator see chronology at a glance.
3. Copy `../templates/story.md` to `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story.md` and fill it in.
4. Create an empty `story-memory.md` placeholder (three section headers: Patterns / Gotchas / Known False Positives).
