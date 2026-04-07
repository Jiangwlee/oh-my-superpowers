#!/usr/bin/env bash
# round.sh — Round Table round 级命令
#
# 职责：对当前 round 执行 collect / spawn / run / watch / attach
# 用法：round.sh <collect|spawn|run|watch|attach> [args]
# 所有命令自动使用 current_round，无需传参
# 依赖：jq
#
# 环境变量：
#   ROUND_TABLE_SESSION  当前 session-id（可选，未设置时自动取最新）
#   RT_DATA_DIR          数据根目录（默认 ~/.local/share/oh-my-superpowers/round-table）

set -euo pipefail

# --- 路径定位 ---
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- 常量 ---
RT_DATA_DIR="${RT_DATA_DIR:-$HOME/.local/share/oh-my-superpowers/round-table}"

# --- 依赖检查 ---
if ! command -v jq &>/dev/null; then
  echo "错误：需要 jq 但未安装。请运行: sudo apt install jq" >&2
  exit 1
fi

# --- 辅助函数 ---

# 获取当前 session 目录
_session_dir() {
  local sid="${ROUND_TABLE_SESSION:-}"
  if [[ -z "$sid" ]]; then
    sid=$(ls -1 "$RT_DATA_DIR" 2>/dev/null | sort -r | head -1)
    if [[ -z "$sid" ]]; then
      echo "错误：没有找到任何 session。请先运行: omp round-table session init <topic>" >&2
      exit 1
    fi
  fi
  echo "$RT_DATA_DIR/$sid"
}

# 从 meta.json 读取 current_round
_current_round() {
  local session_dir
  session_dir=$(_session_dir)
  jq -r '.current_round' "$session_dir/meta.json"
}

# --- 命令实现 ---

cmd_collect() {
  local session_dir
  session_dir=$(_session_dir)
  local meta="$session_dir/meta.json"

  local round
  round=$(_current_round)

  echo "▶ 收集 round ${round} 的响应..." >&2

  local collected_json='[]'
  local failed_json='[]'

  # 扫描本 round 的所有 response 文件
  local response_dir="$session_dir/responses"
  local pattern="round-${round}-*.md"

  # 收集匹配文件列表（允许无文件时优雅退出）
  local files=()
  while IFS= read -r -d '' f; do
    files+=("$f")
  done < <(find "$response_dir" -maxdepth 1 -name "$pattern" -print0 2>/dev/null || true)

  if [[ ${#files[@]} -eq 0 ]]; then
    echo "警告：round ${round} 没有找到任何响应文件（${response_dir}/${pattern}）" >&2
  fi

  for file in "${files[@]}"; do
    local filename
    filename=$(basename "$file")

    # 从文件名提取 role_id：round-N-<role-id>.md → <role-id>
    local role_id
    role_id="${filename#round-${round}-}"
    role_id="${role_id%.md}"

    echo "  处理: ${role_id}" >&2

    # 从 meta.json participants 中查找 name
    local name
    name=$(jq -r --arg id "$role_id" \
      '.participants[] | select(.id == $id) | .name' "$meta" 2>/dev/null || true)

    if [[ -z "$name" ]]; then
      echo "  警告：在 meta.json 中找不到 role_id='${role_id}'，跳过" >&2
      failed_json=$(echo "$failed_json" | jq --arg r "$role_id" '. + [$r]')
      continue
    fi

    # 解析文件内容：提取 action（【名字】【action】 格式）
    local action
    # 匹配第二个【...】中的内容
    action=$(grep -oP '】【\K[^】]+(?=】)' "$file" 2>/dev/null | head -1 || true)

    # 解析 summary（**简言之**：... 格式）
    local summary
    summary=$(grep -oP '\*\*简言之\*\*：\K.+' "$file" 2>/dev/null | head -1 || true)

    # Fallback：正则未匹配时使用默认值
    if [[ -z "$action" ]]; then
      action="陈述"
      echo "  提示：未能从 ${filename} 解析 action，使用默认值 '陈述'" >&2
    fi

    if [[ -z "$summary" ]]; then
      # 取首行前 80 字符作为 summary
      local first_line
      first_line=$(head -1 "$file" 2>/dev/null || true)
      summary="${first_line:0:80}"
      echo "  提示：未能从 ${filename} 解析 summary，使用首行截断" >&2
    fi

    # 调用 session.sh post-message 写入 messages.jsonl
    if bash "$SKILL_DIR/scripts/session.sh" post-message "$role_id" "$file" \
        --round "$round" --name "$name" --action "$action" --summary "$summary" >&2; then
      collected_json=$(echo "$collected_json" | jq \
        --arg rid "$role_id" \
        --arg n "$name" \
        --arg a "$action" \
        --arg s "$summary" \
        '. + [{"role_id": $rid, "name": $n, "action": $a, "summary": $s}]')
      echo "  ✓ 已收录: ${name}【${action}】" >&2
    else
      echo "  ✗ post-message 失败: ${role_id}" >&2
      failed_json=$(echo "$failed_json" | jq --arg r "$role_id" '. + [$r]')
    fi
  done

  # 输出最终 JSON 到 stdout
  jq -n \
    --argjson round "$round" \
    --argjson collected "$collected_json" \
    --argjson failed "$failed_json" \
    '{round: $round, collected: $collected, failed: $failed}'
}

cmd_spawn() {
  local current_round
  current_round=$(_current_round)
  local next_round=$((current_round + 1))
  exec bash "$SKILL_DIR/scripts/spawn.sh" "$next_round" "$@"
}

cmd_run() {
  local current_round
  current_round=$(_current_round)
  local next_round=$((current_round + 1))

  echo "▶ 启动 round ${next_round}（spawn 阻塞中）..." >&2

  # spawn 是阻塞的（内部有等待逻辑），进度信息到 stderr
  bash "$SKILL_DIR/scripts/spawn.sh" "$next_round" "$@" >&2

  # spawn 完成后 current_round 已更新，直接 collect
  echo "▶ spawn 完成，开始 collect..." >&2
  cmd_collect
}

cmd_watch() {
  exec bash "$SKILL_DIR/scripts/session.sh" watch "$@"
}

cmd_attach() {
  exec bash "$SKILL_DIR/scripts/session.sh" attach "$@"
}

# --- 主入口 ---

cmd="${1:-}"
shift || true

case "$cmd" in
  collect) cmd_collect "$@" ;;
  spawn)   cmd_spawn "$@" ;;
  run)     cmd_run "$@" ;;
  watch)   cmd_watch "$@" ;;
  attach)  cmd_attach "$@" ;;
  *)
    echo "用法：round.sh <collect|spawn|run|watch|attach>" >&2
    echo "" >&2
    echo "子命令说明：" >&2
    echo "  collect  解析当前 round 的 response 文件，写入 messages.jsonl" >&2
    echo "  spawn    启动下一 round（在 tmux 中并行运行所有参与者）" >&2
    echo "  run      spawn + collect 的组合（阻塞直到全部完成）" >&2
    echo "  watch    观察当前 session 的消息流" >&2
    echo "  attach   附加到正在运行的 session" >&2
    exit 1
    ;;
esac
