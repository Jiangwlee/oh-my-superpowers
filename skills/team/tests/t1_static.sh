#!/usr/bin/env bash
# t1_static.sh — T1 static checks for the team skill
#
# Validates: directory structure, SKILL.md content, script shebangs,
#            no relative path calls, CLI entry point.
#
# Usage: bash skills/team/tests/t1_static.sh

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0

pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }
check() { if "$@" 2>/dev/null; then pass "$desc"; else fail "$desc"; fi; }

echo "=== Team Skill T1 Static Checks ==="

# ── 1. Directory structure ────────────────────────────
echo ""
echo "--- Directory Structure ---"

for dir in scripts references references/patterns references/scenarios references/prompts tests; do
  desc="directory exists: $dir"
  check test -d "$SKILL_DIR/$dir"
done

# ── 2. Required files ────────────────────────────────
echo ""
echo "--- Required Files ---"

REQUIRED_FILES=(
  "SKILL.md"
  "scripts/run.sh"
  "scripts/clean.sh"
  "scripts/status.sh"
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

BIN_FILE="$SKILL_DIR/../../bin/omp"
desc="bin/omp exists"
check test -f "$BIN_FILE"

desc="bin/omp is executable"
check test -x "$BIN_FILE"

# ── 4. Script shebangs ───────────────────────────────
echo ""
echo "--- Script Shebangs ---"

for script in scripts/run.sh scripts/clean.sh scripts/status.sh; do
  desc="$script has bash shebang"
  check grep -q '#!/usr/bin/env bash' "$SKILL_DIR/$script"
done

# ── 5. SKILL.md content checks ───────────────────────
echo ""
echo "--- SKILL.md Content ---"

SKILL_MD="$SKILL_DIR/SKILL.md"

desc="SKILL.md has frontmatter"
check grep -q '^---' "$SKILL_MD"

desc="SKILL.md has name field"
check grep -q '^name:' "$SKILL_MD"

desc="SKILL.md has description field"
check grep -q '^description:' "$SKILL_MD"

desc="SKILL.md references omp team run"
check grep -q 'omp team run' "$SKILL_MD"

desc="SKILL.md references omp team status"
check grep -q 'omp team status' "$SKILL_MD"

desc="SKILL.md references omp team clean"
check grep -q 'omp team clean' "$SKILL_MD"

# ── 6. No relative path calls in SKILL.md ────────────
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

# ── 7. run.sh uses safe prompt passing ───────────────
echo ""
echo "--- Safe Prompt Passing ---"

RUN_SH="$SKILL_DIR/scripts/run.sh"

desc="run.sh uses 'cat file | claude -p' (not \$(cat))"
check grep -q 'cat.*| claude -p' "$RUN_SH"

desc="run.sh uses 'cat file | codex exec -' (not \$(cat))"
check grep -q 'cat.*| codex exec' "$RUN_SH"

desc="run.sh uses pi @file syntax"
check grep -q '@${prompt_file}' "$RUN_SH"

desc="run.sh has no \$(cat) argument embedding"
if grep -qE '\$\(cat [^)]+\)' "$RUN_SH"; then
  fail "$desc"
else
  pass "$desc"
fi

# ── Summary ───────────────────────────────────────────
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
