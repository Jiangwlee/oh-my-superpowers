# Acceptance

How the orchestrator verifies that a completed task meets its spec.

## Per-Task Verification

For each completed task:

1. Read `## Acceptance Criteria / ### Must-Haves` in the task spec.
2. Verify each item present (not all three are required in every task):
   - **Truths** — is each stated behavior observable?
   - **Artifacts** — does each file exist with the expected content/pattern?
   - **Key Links** — does each cross-file connection match the declared regex pattern?
3. All present items pass →
   `omp coding-orchestrator task update --story-dir <PROJECT_ROOT>/stories --story <slug> --id <NN> --status completed`
   (append `--commit <hash>` when relevant)

## Story Complete

When all tasks in `tasks.yaml` show `status: completed` → story is complete.
