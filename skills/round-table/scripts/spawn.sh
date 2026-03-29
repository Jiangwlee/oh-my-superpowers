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
      echo "错误：没有活跃的 session。请先运行: omp-round-table session init <topic>" >&2
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
    echo "echo 'mock response' | tee '$output_file'"
    return
  fi

  # 使用 tee 同时输出到文件和 tmux 窗口，实现实时可观测
  case "$runtime" in
    claude)
      echo "cat '$prompt_file' | claude -p --model '$model' 2>&1 | tee '$output_file'"
      ;;
    codex)
      echo "cat '$prompt_file' | codex exec - 2>&1 | tee '$output_file'"
      ;;
    pi)
      echo "pi --no-session -p @'$prompt_file' --model '$model' 2>&1 | tee '$output_file'"
      ;;
    *)
      echo "echo '错误：未知 runtime: $runtime' | tee '$output_file'"
      ;;
  esac
}

_list_window_names() {
  local tmux_session="$1"
  awk 'NF { print }' < <(tmux list-windows -t "$tmux_session" -F '#{window_name}' 2>/dev/null || true)
}

_count_windows() {
  local tmux_session="$1"
  awk 'END { print NR + 0 }' < <(_list_window_names "$tmux_session")
}

_list_participant_windows() {
  local tmux_session="$1"
  awk '$0 != "control" { print }' < <(_list_window_names "$tmux_session")
}

_count_participant_windows() {
  local tmux_session="$1"
  awk 'END { print NR + 0 }' < <(_list_participant_windows "$tmux_session")
}

# --- 主逻辑 ---

main() {
  local round="${1:-}"

  if [[ -z "$round" ]]; then
    # 自动检测：current_round + 1
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
    context_brief=$($omp_rt session context brief 2>/dev/null || true)
    messages_history=$($omp_rt session messages 2>/dev/null || true)
  fi

  # tmux session 名
  local sid
  sid=$(jq -r '.session_id' "$meta")
  local tmux_session="rt-${sid}"

  # 更新 current_round
  local current
  current=$(jq -r '.current_round' "$meta")
  if [[ "$round" -gt "$current" ]]; then
    jq --argjson r "$round" '.current_round = $r' "$meta" > "$meta.tmp" && mv "$meta.tmp" "$meta"
  fi

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
  echo "提示：运行 omp-round-table round watch 实时查看输出，或 omp-round-table round attach 进入 tmux"
  echo ""

  local elapsed=0
  local check_interval=5

  while true; do
    # 检查是否还有活跃的参与者 window
    local active_windows
    active_windows=$(_count_participant_windows "$tmux_session")

    if [[ "$active_windows" -eq 0 ]]; then
      break
    fi

    if [[ "$elapsed" -ge "$RT_TIMEOUT" ]]; then
      echo "警告：超时，终止剩余参与者..." >&2
      # kill 剩余 windows
      for win in $(_list_participant_windows "$tmux_session"); do
        tmux kill-window -t "$tmux_session:$win" 2>/dev/null || true
        failed+=("$win")
      done
      break
    fi

    sleep "$check_interval"
    elapsed=$((elapsed + check_interval))

    # 显示每个参与者的实时状态
    local status_line=""
    for i in $(seq 0 $((participant_count - 1))); do
      local rid rname
      rid=$(jq -r ".participants[$i].id" "$meta")
      rname=$(jq -r ".participants[$i].name" "$meta")
      local ofile="$responses_dir/round-${round}-${rid}.md"

      # 检查 tmux window 是否还在运行
      local is_active=false
      if _list_participant_windows "$tmux_session" | grep -qx "$rid" 2>/dev/null; then
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

    echo "[${elapsed}s/${RT_TIMEOUT}s] 剩余 ${active_windows} 个参与者"
    echo "$status_line"
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
  remaining=$(_count_windows "$tmux_session")
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
