#!/usr/bin/env bash
# spawn.sh — Round Table 参与者并行启动脚本
#
# 职责：在 tmux 中并行启动多个 AI agent（claude/codex/pi），收集 stdout 输出
# 用法：spawn.sh <round-number>
# 依赖：jq, tmux
#
# 环境变量：
#   ROUND_TABLE_SESSION  当前 session-id（必须设置或有活跃 session）
#   RT_DATA_DIR          数据根目录（默认 ~/.local/share/oh-my-superpowers/round-table）
#   RT_TIMEOUT           单参与者超时秒数（默认 300）
#   RT_MOCK_RUNTIME      设为 1 启用 mock 模式（测试用）

set -euo pipefail

# --- 常量 ---
RT_DATA_DIR="${RT_DATA_DIR:-$HOME/.local/share/oh-my-superpowers/round-table}"
RT_TIMEOUT="${RT_TIMEOUT:-300}"
RT_MOCK_RUNTIME="${RT_MOCK_RUNTIME:-0}"

# --- 依赖检查 ---
for cmd in jq tmux; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "错误：需要 $cmd 但未安装。" >&2
    exit 1
  fi
done

# --- 辅助函数 ---

_session_dir() {
  local sid="${ROUND_TABLE_SESSION:-}"
  if [[ -z "$sid" ]]; then
    sid=$(ls -1 "$RT_DATA_DIR" 2>/dev/null | sort -r | head -1)
    if [[ -z "$sid" ]]; then
      echo "错误：没有活跃的 session。请先运行: omp-round-table start <topic>" >&2
      exit 1
    fi
  fi
  echo "$RT_DATA_DIR/$sid"
}

# 根据 runtime 构建执行命令
_build_runtime_cmd() {
  local runtime="$1"
  local model="$2"
  local prompt_file="$3"
  local output_file="$4"

  if [[ "$RT_MOCK_RUNTIME" == "1" ]]; then
    echo "echo 'mock response' > '$output_file'"
    return
  fi

  case "$runtime" in
    claude)
      echo "cat '$prompt_file' | claude -p --model '$model' > '$output_file' 2>&1"
      ;;
    codex)
      echo "codex exec \"\$(cat '$prompt_file')\" > '$output_file' 2>&1"
      ;;
    pi)
      echo "pi -p \"\$(cat '$prompt_file')\" --model '$model' > '$output_file' 2>&1"
      ;;
    *)
      echo "echo '错误：未知 runtime: $runtime' > '$output_file'"
      ;;
  esac
}

# --- 主逻辑 ---

main() {
  local round="${1:-}"
  if [[ -z "$round" ]]; then
    echo "用法：spawn.sh <round-number>" >&2
    exit 1
  fi

  local session_dir
  session_dir=$(_session_dir)
  local meta="$session_dir/meta.json"
  local responses_dir="$session_dir/responses"
  mkdir -p "$responses_dir"

  # 读取参与者列表
  local participant_count
  participant_count=$(jq '.participants | length' "$meta")
  if [[ "$participant_count" -eq 0 ]]; then
    echo "错误：没有参与者。请在 meta.json 中配置 participants。" >&2
    exit 1
  fi

  # 获取上下文（供 prompt 拼接）
  local context_brief=""
  local messages_history=""
  local omp_rt="omp-round-table"
  if command -v "$omp_rt" &>/dev/null; then
    context_brief=$($omp_rt get-context brief 2>/dev/null || true)
    messages_history=$($omp_rt get-messages 2>/dev/null || true)
  fi

  # tmux session 名
  local sid
  sid=$(jq -r '.session_id' "$meta")
  local tmux_session="rt-${sid}"

  # 创建 tmux session（如果不存在）
  if ! tmux has-session -t "$tmux_session" 2>/dev/null; then
    tmux new-session -d -s "$tmux_session" -n "control" "sleep 1"
  fi

  local completed=()
  local failed=()
  local pids=()

  # 为每个参与者启动进程
  for i in $(seq 0 $((participant_count - 1))); do
    local role_id name runtime model
    role_id=$(jq -r ".participants[$i].id" "$meta")
    name=$(jq -r ".participants[$i].name" "$meta")
    runtime=$(jq -r ".participants[$i].runtime" "$meta")
    model=$(jq -r ".participants[$i].model" "$meta")

    local participant_prompt="$session_dir/participants/${role_id}.md"
    local output_file="$responses_dir/round-${round}-${role_id}.md"

    # 拼接完整 prompt 到临时文件
    local prompt_file="/tmp/rt-${sid}-${role_id}.txt"
    {
      # Layer 1: 角色身份
      if [[ -f "$participant_prompt" ]]; then
        cat "$participant_prompt"
      else
        echo "你是 $name。请以该身份参与讨论。"
      fi
      echo ""
      echo "---"
      echo ""

      # Layer 2: 讨论背景
      echo "## 讨论背景"
      echo "$context_brief"
      echo ""

      # Layer 3: 对话历史
      echo "## 对话历史"
      echo "$messages_history"
      echo ""

      # Layer 4: 本轮指令
      echo "## 本轮任务"
      echo ""
      echo "请以【${name}】的身份发言。"
      echo "选择一个行动标签（陈述/质疑/补充/反驳/修正/综合），回应前序发言。"
      echo ""
      echo "输出格式："
      echo "【${name}】【行动标签】：你的发言内容"
      echo ""
      echo "**简言之**：一句话总结"
    } > "$prompt_file"

    # 构建 runtime 命令
    local cmd
    cmd=$(_build_runtime_cmd "$runtime" "$model" "$prompt_file" "$output_file")

    # 在 tmux 中启动
    tmux new-window -t "$tmux_session" -n "$role_id" "$cmd; exit"

    echo "已启动: $name ($runtime/$model) → round-${round}-${role_id}.md"
  done

  # 等待所有参与者完成
  echo ""
  echo "等待所有参与者完成（超时: ${RT_TIMEOUT}s）..."

  local elapsed=0
  local check_interval=5

  while true; do
    # 检查是否还有活跃的参与者 window
    local active_windows
    active_windows=$(tmux list-windows -t "$tmux_session" 2>/dev/null \
      | grep -v "control" \
      | wc -l || echo "0")

    if [[ "$active_windows" -eq 0 ]]; then
      break
    fi

    if [[ "$elapsed" -ge "$RT_TIMEOUT" ]]; then
      echo "警告：超时，终止剩余参与者..." >&2
      # kill 剩余 windows
      for win in $(tmux list-windows -t "$tmux_session" -F '#{window_name}' 2>/dev/null | grep -v "control"); do
        tmux kill-window -t "$tmux_session:$win" 2>/dev/null || true
        failed+=("$win")
      done
      break
    fi

    sleep "$check_interval"
    elapsed=$((elapsed + check_interval))
    echo "  ... 已等待 ${elapsed}s，剩余 ${active_windows} 个参与者"
  done

  # 收集结果
  for i in $(seq 0 $((participant_count - 1))); do
    local role_id
    role_id=$(jq -r ".participants[$i].id" "$meta")
    local output_file="$responses_dir/round-${round}-${role_id}.md"

    if [[ -f "$output_file" ]] && [[ -s "$output_file" ]]; then
      completed+=("$role_id")
    else
      # 检查是否已在 failed 中
      local already_failed=false
      for f in "${failed[@]+"${failed[@]}"}"; do
        if [[ "$f" == "$role_id" ]]; then
          already_failed=true
          break
        fi
      done
      if ! $already_failed; then
        failed+=("$role_id")
      fi
    fi
  done

  # 清理 tmux session（如果所有 window 都结束了）
  local remaining
  remaining=$(tmux list-windows -t "$tmux_session" 2>/dev/null | wc -l || echo "0")
  if [[ "$remaining" -le 1 ]]; then
    tmux kill-session -t "$tmux_session" 2>/dev/null || true
  fi

  # 输出 JSON 结果
  local completed_json
  completed_json=$(printf '%s\n' "${completed[@]+"${completed[@]}"}" | jq -Rsc 'split("\n") | map(select(. != ""))')
  local failed_json
  failed_json=$(printf '%s\n' "${failed[@]+"${failed[@]}"}" | jq -Rsc 'split("\n") | map(select(. != ""))')

  jq -nc \
    --argjson round "$round" \
    --argjson completed "$completed_json" \
    --argjson failed "$failed_json" \
    --arg responses_dir "$responses_dir" \
    '{round: $round, completed: $completed, failed: $failed, responses_dir: $responses_dir}'
}

main "$@"
