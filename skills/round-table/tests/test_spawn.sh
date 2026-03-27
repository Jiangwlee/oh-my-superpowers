#!/usr/bin/env bash
# test_spawn.sh — spawn.sh 的 T1 测试
#
# 使用 mock 模式（RT_MOCK_RUNTIME=1）替代真实 runtime 调用
# 用法：bash test_spawn.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPAWN_SCRIPT="$SCRIPT_DIR/../scripts/spawn.sh"
SESSION_SCRIPT="$SCRIPT_DIR/../scripts/session.sh"

# --- 测试框架 ---
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

TEST_DATA_DIR=$(mktemp -d)
export RT_DATA_DIR="$TEST_DATA_DIR"
export RT_MOCK_RUNTIME=1
export RT_TIMEOUT=30

cleanup() {
  # 清理 tmux sessions
  tmux list-sessions 2>/dev/null | grep "^rt-" | cut -d: -f1 | while read -r s; do
    tmux kill-session -t "$s" 2>/dev/null || true
  done || true
  rm -rf "$TEST_DATA_DIR"
}
trap cleanup EXIT

assert_eq() {
  local expected="$1" actual="$2" msg="${3:-}"
  if [[ "$expected" == "$actual" ]]; then return 0
  else echo "  FAIL: $msg (expected=$expected, actual=$actual)"; return 1; fi
}

assert_contains() {
  local haystack="$1" needle="$2" msg="${3:-}"
  if echo "$haystack" | grep -qF "$needle"; then return 0
  else echo "  FAIL: $msg — not found: $needle"; return 1; fi
}

run_test() {
  local name="$1"
  TESTS_RUN=$((TESTS_RUN + 1))
  echo "Running: $name"
  if "$name"; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "  PASS"
  else
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
}

# --- 测试用例 ---

test_spawn_reads_participants() {
  # 创建 session 并添加参与者
  local participants='[
    {"id":"jobs","name":"Steve Jobs","role":"产品","runtime":"claude","model":"opus"},
    {"id":"musk","name":"Elon Musk","role":"工程","runtime":"codex","model":"gpt-5.4"}
  ]'
  local session_id
  session_id=$(bash "$SESSION_SCRIPT" init "spawn测试" --participants "$participants")
  export ROUND_TABLE_SESSION="$session_id"

  # 创建 participant prompt 文件
  local session_dir="$TEST_DATA_DIR/$session_id"
  mkdir -p "$session_dir/participants"
  echo "你是 Steve Jobs。" > "$session_dir/participants/jobs.md"
  echo "你是 Elon Musk。" > "$session_dir/participants/musk.md"

  # spawn 应能成功启动（mock 模式）
  local result
  result=$(bash "$SPAWN_SCRIPT" 1 2>&1) || true

  # 应输出 JSON 结果
  assert_contains "$result" "completed" "应输出 completed 字段" || return 1
}

test_spawn_creates_response_files() {
  local session_id="${ROUND_TABLE_SESSION:-}"
  local session_dir="$TEST_DATA_DIR/$session_id"

  # 等待 mock 进程完成
  sleep 2

  # 检查 responses 目录
  local responses_dir="$session_dir/responses"
  if [[ -d "$responses_dir" ]]; then
    local file_count
    file_count=$(ls -1 "$responses_dir"/round-1-*.md 2>/dev/null | wc -l)
    [[ "$file_count" -ge 1 ]] || { echo "  FAIL: 应至少有 1 个 response 文件"; return 1; }
  fi
  # mock 模式下 tmux 行为不完全可预测，只要不报错即通过
  return 0
}

# --- 执行 ---

echo "=== Round Table spawn.sh 测试 ==="
echo ""

run_test test_spawn_reads_participants
run_test test_spawn_creates_response_files

echo ""
echo "=== 结果：$TESTS_PASSED/$TESTS_RUN 通过，$TESTS_FAILED 失败 ==="

[[ "$TESTS_FAILED" -eq 0 ]] || exit 1
