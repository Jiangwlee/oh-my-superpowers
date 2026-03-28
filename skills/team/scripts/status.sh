#!/usr/bin/env bash
# status.sh — 查询 team tmux session 状态
#
# 无参数：列出所有 team-* 前缀的 tmux sessions
# 有参数：查询指定 session
#
# Usage:
#   status.sh                  列出所有 team sessions
#   status.sh <session-name>   查询指定 session

set -euo pipefail

if [[ $# -ge 1 ]]; then
  # 查询指定 session
  if tmux has-session -t "$1" 2>/dev/null; then
    tmux list-sessions -F '#{session_name} #{session_activity}' | grep "^$1 "
  else
    echo "Session '$1' not found" >&2
    exit 1
  fi
else
  # 列出所有 team-* sessions
  sessions=$(tmux list-sessions -F '#{session_name} #{session_activity}' 2>/dev/null | grep "^team-" || true)
  if [[ -z "$sessions" ]]; then
    echo "No active team sessions" >&2
    exit 0
  fi
  echo "$sessions"
fi
