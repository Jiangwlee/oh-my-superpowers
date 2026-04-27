#!/usr/bin/env bash
# t1_static.sh — T1 static checks for the team skill (orchestration patterns)
#
# Validates: directory structure, SKILL.md content, references files,
#            and that all dispatch references point to omp dispatch (not omp team).
#
# Usage: bash tests/skills/team/t1_static.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SKILL_DIR="$PROJECT_ROOT/skills/team"
PASS=0
FAIL=0

pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }
check() { if "$@" 2>/dev/null; then pass "$desc"; else fail "$desc"; fi; }

echo "=== Team Skill T1 Static Checks ==="

# ── 1. Directory structure ────────────────────────────
echo ""
echo "--- Directory Structure ---"

for dir in references references/patterns references/scenarios references/prompts; do
  desc="directory exists: $dir"
  check test -d "$SKILL_DIR/$dir"
done

desc="scripts/ directory removed (logic lives in lib/dispatch)"
if [[ -d "$SKILL_DIR/scripts" ]]; then
  fail "$desc"
else
  pass "$desc"
fi

# ── 2. Required files ────────────────────────────────
echo ""
echo "--- Required Files ---"

REQUIRED_FILES=(
  "SKILL.md"
  "references/README.md"
  "references/runtime-reference.md"
  "references/patterns/pipeline.md"
  "references/patterns/fan-out-fan-in.md"
  "references/patterns/discussion.md"
  "references/patterns/batch.md"
  "references/scenarios/code-and-review.md"
  "references/scenarios/debate.md"
  "references/prompts/coding-task.md"
  "references/prompts/code-review.md"
  "references/prompts/role-activation.md"
)

for f in "${REQUIRED_FILES[@]}"; do
  desc="file exists: $f"
  check test -f "$SKILL_DIR/$f"
done

# ── 3. CLI entry point ───────────────────────────────
echo ""
echo "--- CLI Entry Point ---"

BIN_FILE="$PROJECT_ROOT/bin/omp"
desc="bin/omp exists"
check test -f "$BIN_FILE"

desc="bin/omp is executable"
check test -x "$BIN_FILE"

DISPATCH_CLI="$PROJECT_ROOT/cli/dispatch/main.py"
desc="cli/dispatch/main.py exists (team underlying primitive)"
check test -f "$DISPATCH_CLI"

# ── 4. SKILL.md content checks ───────────────────────
echo ""
echo "--- SKILL.md Content ---"

SKILL_MD="$SKILL_DIR/SKILL.md"

desc="SKILL.md has frontmatter"
check grep -q '^---' "$SKILL_MD"

desc="SKILL.md has name field"
check grep -q '^name:' "$SKILL_MD"

desc="SKILL.md has description field"
check grep -q '^description:' "$SKILL_MD"

desc="SKILL.md references omp dispatch run"
check grep -q 'omp dispatch run' "$SKILL_MD"

desc="SKILL.md references omp dispatch spawn (parallel)"
check grep -q 'omp dispatch spawn' "$SKILL_MD"

desc="SKILL.md no longer references omp team run (renamed)"
if grep -q 'omp team run' "$SKILL_MD"; then
  fail "$desc"
else
  pass "$desc"
fi

# ── 5. No relative path calls in SKILL.md ────────────
echo ""
echo "--- No Relative Path Calls ---"

FORBIDDEN_PATTERNS=(
  "bash scripts/"
  "sh scripts/"
  "./scripts/"
)

for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
  desc="SKILL.md has no '$pattern'"
  if grep -q "$pattern" "$SKILL_MD"; then
    fail "$desc"
  else
    pass "$desc"
  fi
done

# ── 6. No omp team residue across team docs ──────────
echo ""
echo "--- omp team → omp dispatch migration completeness ---"

residues=$(grep -rn "omp team " "$SKILL_DIR" 2>/dev/null || true)
desc="no 'omp team ' references remain in skills/team/"
if [[ -n "$residues" ]]; then
  fail "$desc"
  echo "$residues" | sed 's/^/    /' >&2
else
  pass "$desc"
fi

# ── Summary ───────────────────────────────────────────
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
