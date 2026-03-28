#!/usr/bin/env bash
# run.sh — 核心脚本：spawn → wait → output 原子操作
#
# 在 tmux session 中启动指定 runtime（claude/codex/pi），等待完成，
# 返回 ANSI-clean 的输出到 stdout。stderr 输出状态日志。
#
# Usage:
#   run.sh <runtime> [prompt] [options]
#
# Options:
#   --prompt-file <path>   从文件读取 prompt（与 inline prompt 互斥）
#   --model <model>        覆盖默认模型
#   --timeout <seconds>    超时秒数（默认 300）
#   --output-file <path>   指定输出文件（默认临时文件）
#   --cwd <dir>            worker 工作目录（默认 $PWD）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 默认值 ──────────────────────────────────────────
runtime=""
prompt=""
prompt_file=""
model=""
timeout_secs=300
output_file=""
cwd="$PWD"

# ── 参数解析 ────────────────────────────────────────
if [[ $# -lt 1 ]]; then
  echo "错误：缺少 runtime 参数" >&2
  echo "用法：run.sh <runtime> [prompt] [options]" >&2
  exit 1
fi

runtime="$1"; shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt-file)
      prompt_file="$2"; shift 2 ;;
    --model)
      model="$2"; shift 2 ;;
    --timeout)
      timeout_secs="$2"; shift 2 ;;
    --output-file)
      output_file="$2"; shift 2 ;;
    --cwd)
      cwd="$2"; shift 2 ;;
    -*)
      echo "错误：未知选项 '$1'" >&2; exit 1 ;;
    *)
      # inline prompt（只取第一个非选项参数）
      if [[ -z "$prompt" ]]; then
        prompt="$1"
      else
        echo "错误：多余的位置参数 '$1'" >&2; exit 1
      fi
      shift ;;
  esac
done

# ── 0. PREPARE ──────────────────────────────────────

# 验证 runtime
case "$runtime" in
  claude|codex|pi) ;;
  *) echo "错误：不支持的 runtime '$runtime'（必须是 claude/codex/pi）" >&2; exit 1 ;;
esac

# 生成 session name
session_name="team-$(date +%Y%m%d%H%M%S)-$(head -c4 /dev/urandom | xxd -p)"

# 处理 prompt：inline prompt 写入临时文件，统一走 prompt_file 路径
if [[ -n "$prompt" && -n "$prompt_file" ]]; then
  echo "错误：inline prompt 与 --prompt-file 互斥" >&2
  exit 1
fi

if [[ -n "$prompt" ]]; then
  prompt_file="/tmp/team-${session_name}-prompt.md"
  printf '%s\n' "$prompt" > "$prompt_file"
elif [[ -z "$prompt_file" ]]; then
  echo "错误：必须提供 prompt 或 --prompt-file" >&2
  exit 1
fi

# 验证 prompt_file 存在
if [[ ! -f "$prompt_file" ]]; then
  echo "错误：prompt 文件不存在：$prompt_file" >&2
  exit 1
fi

# 生成 output_file 路径
if [[ -z "$output_file" ]]; then
  output_file="/tmp/team-${session_name}-output.txt"
fi

# ── 1. SPAWN ────────────────────────────────────────

# 按 runtime 构建命令
case "$runtime" in
  claude)
    if [[ -n "$model" ]]; then
      cmd="cat ${prompt_file} | claude -p --model ${model} 2>&1 | tee ${output_file}"
    else
      cmd="cat ${prompt_file} | claude -p 2>&1 | tee ${output_file}"
    fi
    ;;
  codex)
    cmd="cat ${prompt_file} | codex exec - 2>&1 | tee ${output_file}"
    ;;
  pi)
    if [[ -n "$model" ]]; then
      cmd="pi --no-session -p @${prompt_file} --model ${model} 2>&1 | tee ${output_file}"
    else
      cmd="pi --no-session -p @${prompt_file} 2>&1 | tee ${output_file}"
    fi
    ;;
esac

tmux new-session -d -s "$session_name" -c "$cwd" "$cmd; exit"
echo "[team] spawned $runtime in session $session_name" >&2

# ── 2. WAIT ─────────────────────────────────────────

elapsed=0
poll_interval=5
last_size=0
stall_count=0
stall_threshold=6  # 连续 6 次无变化（30s）触发 warning

while tmux has-session -t "$session_name" 2>/dev/null; do
  if [[ $elapsed -ge $timeout_secs ]]; then
    echo "[team] timeout after ${timeout_secs}s, killing session $session_name" >&2
    tmux kill-session -t "$session_name" 2>/dev/null || true
    echo "TIMEOUT" > "$output_file"
    # 输出 TIMEOUT 到 stdout 并以 124 退出
    bash "$SCRIPT_DIR/clean.sh" "$output_file"
    exit 124
  fi

  # Heartbeat: 检查 output_file 大小变化
  curr_size=$(stat -c%s "$output_file" 2>/dev/null || echo 0)
  if [[ "$curr_size" -eq "$last_size" ]]; then
    stall_count=$((stall_count + 1))
    if [[ $stall_count -ge $stall_threshold ]]; then
      echo "[team] warning: worker stalled (no output for $((stall_count * poll_interval))s)" >&2
    fi
  else
    stall_count=0
    last_size=$curr_size
  fi

  echo "[team] waiting for $runtime ($session_name) ... ${elapsed}s/${timeout_secs}s" >&2
  sleep "$poll_interval"
  elapsed=$((elapsed + poll_interval))
done

echo "[team] $runtime completed ($session_name)" >&2

# ── 3. OUTPUT ───────────────────────────────────────

if [[ ! -f "$output_file" ]]; then
  echo "错误：输出文件不存在：$output_file" >&2
  exit 1
fi

bash "$SCRIPT_DIR/clean.sh" "$output_file"
exit 0
