#!/usr/bin/env bash
# T1 静态检查 — evolution skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_MD="$SKILL_DIR/SKILL.md"

pass=0
fail=0

check() {
  if eval "$1" >/dev/null 2>&1; then
    echo "  PASS: $desc"
    pass=$((pass + 1))
  else
    echo "  FAIL: $desc"
    fail=$((fail + 1))
  fi
}

echo "=== Evolution Skill T1 Static Checks ==="
echo ""

# --- SKILL.md ---
echo "[SKILL.md]"

desc="SKILL.md exists"
check "test -f '$SKILL_MD'"

desc="SKILL.md has frontmatter"
check "head -1 '$SKILL_MD' | grep -q '^---'"

desc="SKILL.md has name field"
check "grep -q '^name:' '$SKILL_MD'"

desc="SKILL.md has description field"
check "grep -q '^description:' '$SKILL_MD'"

desc="SKILL.md name matches directory"
check "grep -q 'name: evolution' '$SKILL_MD'"

desc="SKILL.md references omp-evolution scan"
check "grep -q 'omp-evolution scan' '$SKILL_MD'"

desc="SKILL.md references omp-evolution history"
check "grep -q 'omp-evolution history' '$SKILL_MD'"

desc="SKILL.md has no relative script paths"
check "! grep -qE 'bash scripts/|python scripts/' '$SKILL_MD'"

echo ""

# --- References ---
echo "[References]"

desc="references/README.md exists"
check "test -f '$SKILL_DIR/references/README.md'"

desc="references/evidence-sources.md exists"
check "test -f '$SKILL_DIR/references/evidence-sources.md'"

desc="references/mutation-operators.md exists"
check "test -f '$SKILL_DIR/references/mutation-operators.md'"

desc="references/guard-checks.md exists"
check "test -f '$SKILL_DIR/references/guard-checks.md'"

desc="references/memory-validity.md exists"
check "test -f '$SKILL_DIR/references/memory-validity.md'"

desc="SKILL.md contains 阶段三"
check "grep -q '阶段三' '$SKILL_MD'"

echo ""

# --- Scripts ---
echo "[Scripts]"

desc="scripts/scan.py exists"
check "test -f '$SKILL_DIR/scripts/scan.py'"

desc="scripts/history.py exists"
check "test -f '$SKILL_DIR/scripts/history.py'"

desc="scan.py has no syntax errors"
check "python3 -c \"import py_compile; py_compile.compile('$SKILL_DIR/scripts/scan.py', doraise=True)\""

desc="history.py has no syntax errors"
check "python3 -c \"import py_compile; py_compile.compile('$SKILL_DIR/scripts/history.py', doraise=True)\""

echo ""

# --- bin ---
echo "[bin]"

BIN_FILE="$SKILL_DIR/../../bin/omp-evolution"
desc="bin/omp-evolution exists"
check "test -f '$BIN_FILE'"

desc="bin/omp-evolution is executable"
check "test -x '$BIN_FILE'"

desc="bin/omp-evolution has bash shebang"
check "head -1 '$BIN_FILE' | grep -q '#!/usr/bin/env bash'"

echo ""

# --- Summary ---
total=$((pass + fail))
echo "=== Results: $pass/$total passed ==="
if [ "$fail" -gt 0 ]; then
  exit 1
fi
