#!/usr/bin/env bash
# test_session.sh — session.sh 的 T1 测试
#
# 使用临时目录作为数据根，不污染真实数据
# 用法：bash test_session.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_SCRIPT="$SCRIPT_DIR/../scripts/session.sh"

# --- 测试框架 ---
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# 临时数据目录
TEST_DATA_DIR=$(mktemp -d)
export RT_DATA_DIR="$TEST_DATA_DIR"

cleanup() {
  rm -rf "$TEST_DATA_DIR"
}
trap cleanup EXIT

assert_eq() {
  local expected="$1" actual="$2" msg="${3:-}"
  if [[ "$expected" == "$actual" ]]; then
    return 0
  else
    echo "  FAIL: $msg"
    echo "    expected: $expected"
    echo "    actual:   $actual"
    return 1
  fi
}

assert_file_exists() {
  local path="$1" msg="${2:-}"
  if [[ -f "$path" ]]; then
    return 0
  else
    echo "  FAIL: $msg — 文件不存在: $path"
    return 1
  fi
}

assert_contains() {
  local haystack="$1" needle="$2" msg="${3:-}"
  if echo "$haystack" | grep -qF "$needle"; then
    return 0
  else
    echo "  FAIL: $msg"
    echo "    expected to contain: $needle"
    echo "    actual: $(echo "$haystack" | head -3)"
    return 1
  fi
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

test_init_creates_session() {
  local session_id
  session_id=$(bash "$SESSION_SCRIPT" init "测试议题")

  # session-id 非空
  [[ -n "$session_id" ]] || { echo "  FAIL: session_id 为空"; return 1; }

  # 目录和文件存在
  local session_dir="$TEST_DATA_DIR/$session_id"
  assert_file_exists "$session_dir/meta.json" "meta.json 应存在" || return 1
  assert_file_exists "$session_dir/context.md" "context.md 应存在" || return 1
  assert_file_exists "$session_dir/plan.md" "plan.md 应存在" || return 1
  assert_file_exists "$session_dir/messages.jsonl" "messages.jsonl 应存在" || return 1

  # meta.json 内容正确
  local topic
  topic=$(jq -r '.topic' "$session_dir/meta.json")
  assert_eq "测试议题" "$topic" "topic 应为测试议题" || return 1

  local status
  status=$(jq -r '.status' "$session_dir/meta.json")
  assert_eq "active" "$status" "status 应为 active" || return 1

  export ROUND_TABLE_SESSION="$session_id"
}

test_init_with_participants() {
  local participants='[{"id":"test-role","name":"Test Person","role":"Tester","runtime":"claude","model":"sonnet"}]'
  local session_id
  session_id=$(bash "$SESSION_SCRIPT" init "带参与者的议题" --participants "$participants")

  local session_dir="$TEST_DATA_DIR/$session_id"
  local count
  count=$(jq '.participants | length' "$session_dir/meta.json")
  assert_eq "1" "$count" "应有 1 个参与者" || return 1

  local role_id
  role_id=$(jq -r '.participants[0].id' "$session_dir/meta.json")
  assert_eq "test-role" "$role_id" "参与者 id 应为 test-role" || return 1
}

test_get_context() {
  # 使用最新 session
  local session_dir
  session_dir=$(ls -1d "$TEST_DATA_DIR"/*/ | sort -r | head -1)

  # 写入更多内容到 context.md
  cat > "${session_dir}context.md" <<'EOF'
# 讨论背景

**议题**：是否需要独立 Agent 框架

## 详细背景

团队 3 人，3 个月交付。
当前没有统一的 agent 运行时。
需要支持 claude/codex/pi 三种 runtime。

## 约束条件

- 预算有限
- 必须兼容现有工具链
EOF

  # brief 模式
  local brief
  brief=$(bash "$SESSION_SCRIPT" get-context brief)
  assert_contains "$brief" "讨论背景" "brief 应包含标题" || return 1

  # detail 模式
  local detail
  detail=$(bash "$SESSION_SCRIPT" get-context detail)
  assert_contains "$detail" "约束条件" "detail 应包含完整内容" || return 1
}

test_post_message_appends() {
  # 找到最新 session
  local session_id
  session_id=$(ls -1 "$TEST_DATA_DIR" | sort -r | head -1)
  export ROUND_TABLE_SESSION="$session_id"
  local session_dir="$TEST_DATA_DIR/$session_id"

  # 创建临时 content 文件
  local content_file
  content_file=$(mktemp)
  echo "这是 Steve Jobs 的发言内容。设计不只是外观。" > "$content_file"

  local msg_id
  msg_id=$(bash "$SESSION_SCRIPT" post-message steve-jobs "$content_file" \
    --round 1 --name "Steve Jobs" --action "陈述" --summary "设计是核心")

  assert_eq "msg-001" "$msg_id" "第一条消息 id 应为 msg-001" || return 1

  # 验证 jsonl 内容
  local jsonl="$session_dir/messages.jsonl"
  local stored_role
  stored_role=$(jq -r '.role' "$jsonl")
  assert_eq "steve-jobs" "$stored_role" "role 应为 steve-jobs" || return 1

  # 追加第二条
  echo "Elon Musk 的反驳。" > "$content_file"
  msg_id=$(bash "$SESSION_SCRIPT" post-message elon-musk "$content_file" \
    --round 1 --name "Elon Musk" --action "反驳" --summary "第一性原理")

  assert_eq "msg-002" "$msg_id" "第二条消息 id 应为 msg-002" || return 1

  local line_count
  line_count=$(wc -l < "$jsonl")
  assert_eq "2" "$line_count" "应有 2 行消息" || return 1

  rm -f "$content_file"
}

test_get_messages_default() {
  local session_id
  session_id=$(ls -1 "$TEST_DATA_DIR" | sort -r | head -1)
  export ROUND_TABLE_SESSION="$session_id"

  # 先添加一条 moderator 综合消息
  local content_file
  content_file=$(mktemp)
  echo "本轮核心争议在于框架的必要性。" > "$content_file"
  bash "$SESSION_SCRIPT" post-message moderator "$content_file" \
    --round 1 --name "主持人" --action "综合" --summary "框架必要性存在争议" >/dev/null

  local output
  output=$(bash "$SESSION_SCRIPT" get-messages)

  # 应包含历史摘要
  assert_contains "$output" "历史摘要" "应包含历史摘要标题" || return 1
  assert_contains "$output" "框架必要性存在争议" "应包含 moderator 摘要" || return 1

  # 应包含最近一轮消息
  assert_contains "$output" "Round 1" "应包含最近一轮标题" || return 1
  assert_contains "$output" "Steve Jobs" "应包含参与者名字" || return 1

  rm -f "$content_file"
}

test_get_messages_by_id() {
  local session_id
  session_id=$(ls -1 "$TEST_DATA_DIR" | sort -r | head -1)
  export ROUND_TABLE_SESSION="$session_id"

  local output
  output=$(bash "$SESSION_SCRIPT" get-messages msg-001)

  assert_contains "$output" "msg-001" "应包含 msg-id" || return 1
  assert_contains "$output" "Steve Jobs" "应包含人物名" || return 1
  assert_contains "$output" "设计不只是外观" "应包含完整内容" || return 1
}

test_end_generates_doc() {
  local session_id
  session_id=$(ls -1 "$TEST_DATA_DIR" | sort -r | head -1)
  export ROUND_TABLE_SESSION="$session_id"

  local output_dir
  output_dir=$(mktemp -d)

  local result
  result=$(bash "$SESSION_SCRIPT" end --output-dir "$output_dir")

  assert_contains "$result" "文档已生成" "应报告文档路径" || return 1

  # 验证文档文件存在
  local doc_count
  doc_count=$(ls -1 "$output_dir"/*.md 2>/dev/null | wc -l)
  [[ "$doc_count" -ge 1 ]] || { echo "  FAIL: 应至少生成 1 个 md 文件"; return 1; }

  # 验证 meta.json status 更新
  local session_dir="$TEST_DATA_DIR/$session_id"
  local status
  status=$(jq -r '.status' "$session_dir/meta.json")
  assert_eq "completed" "$status" "status 应更新为 completed" || return 1

  rm -rf "$output_dir"
}

# --- 执行 ---

echo "=== Round Table session.sh 测试 ==="
echo ""

run_test test_init_creates_session
run_test test_init_with_participants
run_test test_get_context
run_test test_post_message_appends
run_test test_get_messages_default
run_test test_get_messages_by_id
run_test test_end_generates_doc

echo ""
echo "=== 结果：$TESTS_PASSED/$TESTS_RUN 通过，$TESTS_FAILED 失败 ==="

[[ "$TESTS_FAILED" -eq 0 ]] || exit 1
