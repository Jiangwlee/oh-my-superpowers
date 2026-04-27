#!/usr/bin/env bash
# spawn.sh — Round Table 参与者并行启动脚本
#
# 职责：通过 omp dispatch 并行启动多个 AI agent（claude/codex/pi），等待完成
# 用法：spawn.sh <round-number>
# 依赖：jq, omp（omp dispatch）
#
# 每个参与者一个独立的 omp dispatch session：omp-rt-<sid>-<role_id>
# 旧的 "rt-<sid>" 单 tmux session + 多 window 拓扑已废弃。
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
for cmd in jq tmux omp; do
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
      echo "错误：没有活跃的 session。请先运行: omp round-table session init <topic>" >&2
      exit 1
    fi
  fi
  echo "$RT_DATA_DIR/$sid"
}

# 给参与者生成 dispatch session 名（不含 omp- 前缀，由 dispatch 自动加）
_session_name() {
  local sid="$1"
  local role_id="$2"
  echo "rt-${sid}-${role_id}"
}

# 完整 tmux session 名（含 omp- 前缀），用于 has-session 查询
_full_session() {
  echo "omp-$(_session_name "$1" "$2")"
}

# 通过 omp dispatch spawn 启动一个参与者
_dispatch_spawn() {
  local runtime="$1"
  local model="$2"
  local prompt_file="$3"
  local output_file="$4"
  local session_name="$5"
  local cwd="$6"

  if [[ "$RT_MOCK_RUNTIME" == "1" ]]; then
    # Mock 模式：用 sh + printf 模拟一个 dispatch session
    local full_session="omp-${session_name}"
    : > "$output_file"
    tmux new-session -d -s "$full_session" -c "$cwd" \
      "cat '$prompt_file' > /dev/null; printf 'mock response\n' | tee '$output_file'; exit"
    echo "$full_session"
    return
  fi

  local args=(
    "$runtime"
    --prompt-file "$prompt_file"
    --output-file "$output_file"
    --cwd "$cwd"
    --session-name "$session_name"
  )
  if [[ -n "$model" && "$model" != "null" ]]; then
    args+=(--model "$model")
  fi
  omp dispatch spawn "${args[@]}"
}

# --- 主逻辑 ---

main() {
  local round="${1:-}"

  if [[ -z "$round" ]]; then
    local session_dir
    session_dir=$(_session_dir)
    local meta="$session_dir/meta.json"
    local current
    current=$(jq -r '.current_round' "$meta")
    round=$((current + 1))
    echo "自动检测轮次：round ${round}（current_round=${current}）" >&2
  fi

  local session_dir
  session_dir=$(_session_dir)
  local meta="$session_dir/meta.json"
  local responses_dir="$session_dir/responses"
  mkdir -p "$responses_dir"

  local participant_count
  participant_count=$(jq '.participants | length' "$meta")
  if [[ "$participant_count" -eq 0 ]]; then
    echo "错误：没有参与者。请在 meta.json 中配置 participants。" >&2
    exit 1
  fi

  local context_brief=""
  local messages_history=""
  context_brief=$(omp round-table session context brief 2>/dev/null || true)
  messages_history=$(omp round-table session messages 2>/dev/null || true)

  local sid
  sid=$(jq -r '.session_id' "$meta")
  local cwd="$PWD"

  local current
  current=$(jq -r '.current_round' "$meta")
  if [[ "$round" -gt "$current" ]]; then
    jq --argjson r "$round" '.current_round = $r' "$meta" > "$meta.tmp" && mv "$meta.tmp" "$meta"
  fi

  local completed=()
  local failed=()
  local participants=()  # role_id 列表，用于状态显示

  # 启动每个参与者
  for i in $(seq 0 $((participant_count - 1))); do
    local role_id name runtime model
    role_id=$(jq -r ".participants[$i].id" "$meta")
    name=$(jq -r ".participants[$i].name" "$meta")
    runtime=$(jq -r ".participants[$i].runtime" "$meta")
    model=$(jq -r ".participants[$i].model" "$meta")

    local participant_prompt="$session_dir/participants/${role_id}.md"
    local output_file="$responses_dir/round-${round}-${role_id}.md"

    local prompt_file="/tmp/rt-${sid}-${role_id}.txt"
    {
      if [[ -f "$participant_prompt" ]]; then
        cat "$participant_prompt"
      else
        echo "你是 $name。请以该身份参与讨论。"
      fi
      echo ""
      echo "---"
      echo ""

      echo "## 讨论背景"
      echo "$context_brief"
      echo ""

      echo "## 对话历史"
      echo "$messages_history"
      echo ""

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

    local sname full_session
    sname=$(_session_name "$sid" "$role_id")
    full_session=$(_dispatch_spawn "$runtime" "$model" "$prompt_file" "$output_file" "$sname" "$cwd")
    participants+=("$role_id")

    echo "已启动: $name ($runtime/$model) → $full_session" >&2
  done

  # 等待所有参与者完成
  echo "" >&2
  echo "等待所有参与者完成（超时: ${RT_TIMEOUT}s）..." >&2
  echo "提示：omp round-table round watch 实时查看输出；omp dispatch tail omp-rt-<sid>-<role> -f 看单个参与者" >&2
  echo "" >&2

  local elapsed=0
  local check_interval=5

  while true; do
    local active_count=0
    for rid in "${participants[@]}"; do
      local full
      full=$(_full_session "$sid" "$rid")
      if tmux has-session -t "$full" 2>/dev/null; then
        active_count=$((active_count + 1))
      fi
    done

    if [[ "$active_count" -eq 0 ]]; then
      break
    fi

    if [[ "$elapsed" -ge "$RT_TIMEOUT" ]]; then
      echo "警告：超时，终止剩余参与者..." >&2
      for rid in "${participants[@]}"; do
        local full
        full=$(_full_session "$sid" "$rid")
        if tmux has-session -t "$full" 2>/dev/null; then
          omp dispatch kill "$full" >/dev/null 2>&1 || true
          failed+=("$rid")
        fi
      done
      break
    fi

    sleep "$check_interval"
    elapsed=$((elapsed + check_interval))

    # 实时状态显示
    local status_line=""
    for i in $(seq 0 $((participant_count - 1))); do
      local rid rname
      rid=$(jq -r ".participants[$i].id" "$meta")
      rname=$(jq -r ".participants[$i].name" "$meta")
      local ofile="$responses_dir/round-${round}-${rid}.md"
      local full
      full=$(_full_session "$sid" "$rid")

      local is_active=false
      if tmux has-session -t "$full" 2>/dev/null; then
        is_active=true
      fi

      if [[ -f "$ofile" ]] && [[ -s "$ofile" ]]; then
        local wc_chars
        wc_chars=$(wc -c < "$ofile")
        if $is_active; then
          status_line+="  ✍️  ${rname} 思考中（${wc_chars} 字节）"
        else
          status_line+="  ✅ ${rname} 完成（${wc_chars} 字节）"
        fi
      elif $is_active; then
        status_line+="  ⏳ ${rname} 等待模型响应..."
      else
        status_line+="  ❌ ${rname} 异常退出"
      fi
      status_line+=$'\n'
    done

    echo "[${elapsed}s/${RT_TIMEOUT}s] 剩余 ${active_count} 个参与者" >&2
    echo "$status_line" >&2
  done

  # 收集结果
  for i in $(seq 0 $((participant_count - 1))); do
    local role_id
    role_id=$(jq -r ".participants[$i].id" "$meta")
    local output_file="$responses_dir/round-${round}-${role_id}.md"

    if [[ -f "$output_file" ]] && [[ -s "$output_file" ]]; then
      completed+=("$role_id")
    else
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
