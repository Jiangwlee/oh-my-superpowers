#!/usr/bin/env bash
# session.sh — Round Table 圆桌讨论的 session 管理脚本
#
# 职责：管理讨论 session 的生命周期（创建、读写消息、结束）
# 用法：session.sh <command> [args]
# 命令：init | get-context | get-messages | post-message | end | status
# 依赖：jq（JSON 处理）
# 数据目录：$RT_DATA_DIR（默认 ~/.local/share/oh-my-superpowers/round-table）
#
# Session 定位：
#   - 环境变量 ROUND_TABLE_SESSION 指定 session-id
#   - 未设置时自动使用最新的（按目录名排序）

set -euo pipefail

# --- 常量与路径 ---
RT_DATA_DIR="${RT_DATA_DIR:-$HOME/.local/share/oh-my-superpowers/round-table}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 检查 jq 依赖
if ! command -v jq &>/dev/null; then
  echo "错误：需要 jq 但未安装。请运行: sudo apt install jq" >&2
  exit 1
fi

# --- 辅助函数 ---

# 获取当前 session 目录
_session_dir() {
  local sid="${ROUND_TABLE_SESSION:-}"
  if [[ -z "$sid" ]]; then
    # 自动选最新的 session
    sid=$(ls -1 "$RT_DATA_DIR" 2>/dev/null | sort -r | head -1)
    if [[ -z "$sid" ]]; then
      echo "错误：没有找到任何 session。请先运行: omp-round-table start <topic>" >&2
      exit 1
    fi
  fi
  echo "$RT_DATA_DIR/$sid"
}

# 生成下一个 msg-id（基于当前行数）
_next_msg_id() {
  local jsonl="$1"
  local count=0
  if [[ -f "$jsonl" ]]; then
    count=$(wc -l < "$jsonl")
  fi
  printf "msg-%03d" $((count + 1))
}

# --- 命令实现 ---

cmd_init() {
  local topic="${1:-}"
  if [[ -z "$topic" ]]; then
    echo "用法：session.sh init <topic> [--roles <id1,id2,...>] [--participants <json>] [--context <text|file>]" >&2
    echo "示例：session.sh init '是否需要独立 Agent 框架' --roles linus-torvalds,alan-kay,elon-musk" >&2
    exit 1
  fi

  # 解析可选参数
  local participants='[]'
  local roles=""
  local context_input=""
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --participants) participants="$2"; shift 2 ;;
      --roles)        roles="$2"; shift 2 ;;
      --context)      context_input="$2"; shift 2 ;;
      *) echo "未知参数: $1" >&2; exit 1 ;;
    esac
  done

  # 生成 session-id
  local session_id
  session_id=$(date +%Y%m%dT%H%M%S)

  local session_dir="$RT_DATA_DIR/$session_id"
  mkdir -p "$session_dir"/{participants,responses}

  # --- 内置角色查找表 ---
  if [[ -n "$roles" ]]; then
    declare -A _ROLE_NAME=(
      [steve-jobs]="Steve Jobs"
      [elon-musk]="Elon Musk"
      [linus-torvalds]="Linus Torvalds"
      [alan-kay]="Alan Kay"
      [andrej-karpathy]="Andrej Karpathy"
      [richard-stallman]="Richard Stallman"
      [dhh]="DHH"
      [yann-lecun]="Yann LeCun"
      [grace-hopper]="Grace Hopper"
      [nassim-taleb]="Nassim Taleb"
      [leslie-lamport]="Leslie Lamport"
      [dario-amodei]="Dario Amodei"
    )
    declare -A _ROLE_LABEL=(
      [steve-jobs]="产品视觉家"
      [elon-musk]="第一性原理工程"
      [linus-torvalds]="务实开发者"
      [alan-kay]="系统思想家"
      [andrej-karpathy]="AI 架构师"
      [richard-stallman]="魔鬼代言人"
      [dhh]="独立开发倡导者"
      [yann-lecun]="AI 科学务实派"
      [grace-hopper]="工程先驱"
      [nassim-taleb]="反脆弱思想家"
      [leslie-lamport]="形式化验证者"
      [dario-amodei]="AI 安全缩放者"
    )
    declare -A _ROLE_RUNTIME=(
      [steve-jobs]="claude"
      [elon-musk]="codex"
      [linus-torvalds]="pi"
      [alan-kay]="claude"
      [andrej-karpathy]="claude"
      [richard-stallman]="codex"
      [dhh]="codex"
      [yann-lecun]="claude"
      [grace-hopper]="pi"
      [nassim-taleb]="codex"
      [leslie-lamport]="claude"
      [dario-amodei]="claude"
    )
    declare -A _ROLE_MODEL=(
      [steve-jobs]="opus"
      [elon-musk]="gpt-5.4"
      [linus-torvalds]="github-copilot/gpt-4.1"
      [alan-kay]="sonnet"
      [andrej-karpathy]="sonnet"
      [richard-stallman]="gpt-5.4"
      [dhh]="gpt-5.4"
      [yann-lecun]="sonnet"
      [grace-hopper]="qwen3.5-27b"
      [nassim-taleb]="gpt-5.4"
      [leslie-lamport]="sonnet"
      [dario-amodei]="opus"
    )

    participants='[]'
    IFS=',' read -ra role_list <<< "$roles"
    for role_id in "${role_list[@]}"; do
      role_id=$(echo "$role_id" | xargs)  # trim whitespace
      local name="${_ROLE_NAME[$role_id]:-}"
      if [[ -z "$name" ]]; then
        echo "警告：未知内置角色 '$role_id'，跳过。可用角色: ${!_ROLE_NAME[*]}" >&2
        continue
      fi

      # 构建 participant JSON
      participants=$(echo "$participants" | jq \
        --arg id "$role_id" \
        --arg name "$name" \
        --arg role "${_ROLE_LABEL[$role_id]}" \
        --arg runtime "${_ROLE_RUNTIME[$role_id]}" \
        --arg model "${_ROLE_MODEL[$role_id]}" \
        '. + [{id: $id, name: $name, role: $role, runtime: $runtime, model: $model}]')

      # 拷贝预置 prompt 文件
      local prompt_src="$SKILL_DIR/references/prompts/${role_id}.md"
      if [[ -f "$prompt_src" ]]; then
        cp "$prompt_src" "$session_dir/participants/${role_id}.md"
      else
        echo "警告：预置 prompt 不存在: $prompt_src（需要手动创建 participants/${role_id}.md）" >&2
      fi
    done
  fi

  # 写入 meta.json
  jq -n \
    --arg sid "$session_id" \
    --arg topic "$topic" \
    --arg created "$(date -Iseconds)" \
    --argjson participants "$participants" \
    '{
      session_id: $sid,
      topic: $topic,
      created_at: $created,
      status: "active",
      current_round: 0,
      participants: $participants
    }' > "$session_dir/meta.json"

  # 创建空文件
  touch "$session_dir/messages.jsonl"
  echo "# 讨论背景" > "$session_dir/context.md"
  echo "" >> "$session_dir/context.md"
  echo "**议题**：$topic" >> "$session_dir/context.md"

  # 写入额外 context
  if [[ -n "$context_input" ]]; then
    echo "" >> "$session_dir/context.md"
    if [[ -f "$context_input" ]]; then
      cat "$context_input" >> "$session_dir/context.md"
    else
      echo "$context_input" >> "$session_dir/context.md"
    fi
  fi

  echo "# 讨论计划" > "$session_dir/plan.md"

  # 输出 session-id（供 orchestrator 捕获）
  echo "$session_id"
}

cmd_get_context() {
  local mode="${1:-brief}"
  local session_dir
  session_dir=$(_session_dir)

  local context_file="$session_dir/context.md"
  if [[ ! -f "$context_file" ]]; then
    echo "错误：context.md 不存在。请先初始化 session。" >&2
    exit 1
  fi

  case "$mode" in
    brief)
      # 输出前 10 行作为摘要
      head -10 "$context_file"
      ;;
    detail)
      cat "$context_file"
      ;;
    *)
      echo "用法：session.sh get-context <brief|detail>" >&2
      exit 1
      ;;
  esac
}

cmd_get_messages() {
  local session_dir
  session_dir=$(_session_dir)
  local jsonl="$session_dir/messages.jsonl"

  if [[ ! -f "$jsonl" ]] || [[ ! -s "$jsonl" ]]; then
    echo "（暂无消息）"
    return 0
  fi

  # 如果指定了 msg-id，输出该消息详情
  local msg_id="${1:-}"
  if [[ -n "$msg_id" ]]; then
    local msg
    msg=$(jq -r "select(.msg_id == \"$msg_id\")" "$jsonl")
    if [[ -z "$msg" ]]; then
      echo "错误：消息 $msg_id 不存在。运行 omp-round-table get-messages 查看所有消息。" >&2
      exit 1
    fi
    local round name action content
    round=$(echo "$msg" | jq -r '.round')
    name=$(echo "$msg" | jq -r '.name')
    action=$(echo "$msg" | jq -r '.action')
    content=$(echo "$msg" | jq -r '.content')
    echo "[$msg_id] Round $round | $name | $action"
    echo "---"
    echo "$content"
    return 0
  fi

  # 默认模式：历史摘要 + 最近一轮完整消息
  local max_round
  max_round=$(jq -r '.round' "$jsonl" | sort -n | tail -1)

  # 历史摘要：从 moderator 综合消息中提取 summary
  local has_history=false
  local history_rounds
  history_rounds=$(jq -r 'select(.role == "moderator" and .action == "综合") | .round' "$jsonl" | sort -nu)

  if [[ -n "$history_rounds" ]]; then
    echo "=== 历史摘要 ==="
    while IFS= read -r round; do
      local summary
      summary=$(jq -r "select(.role == \"moderator\" and .action == \"综合\" and .round == $round) | .summary" "$jsonl")
      if [[ -n "$summary" ]]; then
        echo "[Round $round] $summary"
        has_history=true
      fi
    done <<< "$history_rounds"
    echo ""
  fi

  # 最近一轮完整消息
  echo "=== Round ${max_round}（最近一轮）==="
  jq -r "select(.round == $max_round) | \"[\\(.msg_id)] 【\\(.name)】【\\(.action)】：\\(.summary)\"" "$jsonl"
}

cmd_post_message() {
  local role="${1:-}"
  local content_file="${2:-}"

  if [[ -z "$role" ]] || [[ -z "$content_file" ]]; then
    echo "用法：session.sh post-message <role> <content-file> --round N --name '名字' --action '标签' --summary '摘要'" >&2
    exit 1
  fi
  shift 2

  # 解析命名参数
  local round="" name="" action="" summary=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --round)   round="$2"; shift 2 ;;
      --name)    name="$2"; shift 2 ;;
      --action)  action="$2"; shift 2 ;;
      --summary) summary="$2"; shift 2 ;;
      *) echo "未知参数: $1" >&2; exit 1 ;;
    esac
  done

  if [[ -z "$round" ]] || [[ -z "$name" ]] || [[ -z "$action" ]]; then
    echo "错误：--round、--name、--action 为必填参数。" >&2
    exit 1
  fi

  local session_dir
  session_dir=$(_session_dir)
  local jsonl="$session_dir/messages.jsonl"

  # 读取 content
  local content=""
  if [[ "$content_file" == "-" ]]; then
    content=$(cat)
  elif [[ -f "$content_file" ]]; then
    content=$(cat "$content_file")
  else
    echo "错误：文件不存在: $content_file" >&2
    exit 1
  fi

  # 生成 msg-id 和时间戳
  local msg_id
  msg_id=$(_next_msg_id "$jsonl")
  local timestamp
  timestamp=$(date -Iseconds)

  # 如果没有 summary，取 content 前 80 字符
  if [[ -z "$summary" ]]; then
    summary=$(echo "$content" | head -1 | cut -c1-80)
  fi

  # 追加到 jsonl
  jq -nc \
    --arg msg_id "$msg_id" \
    --argjson round "$round" \
    --arg role "$role" \
    --arg name "$name" \
    --arg action "$action" \
    --arg summary "$summary" \
    --arg content "$content" \
    --arg timestamp "$timestamp" \
    '{
      msg_id: $msg_id,
      round: $round,
      role: $role,
      name: $name,
      action: $action,
      summary: $summary,
      content: $content,
      timestamp: $timestamp
    }' >> "$jsonl"

  # 更新 current_round
  local meta="$session_dir/meta.json"
  if [[ -f "$meta" ]]; then
    local current
    current=$(jq -r '.current_round' "$meta")
    if [[ "$round" -gt "$current" ]]; then
      jq --argjson r "$round" '.current_round = $r' "$meta" > "$meta.tmp" && mv "$meta.tmp" "$meta"
    fi
  fi

  echo "$msg_id"
}

cmd_end() {
  local session_dir
  session_dir=$(_session_dir)
  local meta="$session_dir/meta.json"
  local jsonl="$session_dir/messages.jsonl"

  # 解析参数
  local output_dir=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --output-dir) output_dir="$2"; shift 2 ;;
      *) echo "未知参数: $1" >&2; exit 1 ;;
    esac
  done

  if [[ -z "$output_dir" ]]; then
    echo "用法：session.sh end --output-dir <path>" >&2
    echo "示例：session.sh end --output-dir ./docs/round-table" >&2
    exit 1
  fi

  mkdir -p "$output_dir"

  local topic
  topic=$(jq -r '.topic' "$meta")
  local created
  created=$(jq -r '.created_at' "$meta" | cut -dT -f1)

  # 生成 topic slug（简化处理：取前 30 字符，空格转连字符）
  local slug
  slug=$(echo "$topic" | tr ' ' '-' | tr -cd '[:alnum:]-_' | cut -c1-30 | tr '[:upper:]' '[:lower:]')
  local output_file="$output_dir/${created}-${slug}.md"

  # 生成文档
  {
    echo "# 圆桌讨论：$topic"
    echo ""
    echo "- **日期**：$created"

    # 参与者列表
    local participants
    participants=$(jq -r '.participants[] | "\(.name) (\(.runtime)/\(.model))"' "$meta" | paste -sd ", " -)
    echo "- **参与者**：$participants"

    local max_round
    max_round=$(jq -r '.current_round' "$meta")
    echo "- **轮次**：$max_round"
    echo ""

    # 背景
    echo "## 背景"
    echo ""
    if [[ -f "$session_dir/context.md" ]]; then
      cat "$session_dir/context.md"
    fi
    echo ""

    # 讨论记录
    echo "## 讨论记录"
    echo ""

    if [[ -f "$jsonl" ]] && [[ -s "$jsonl" ]]; then
      for r in $(seq 1 "$max_round"); do
        # 获取本轮引导问题（来自 moderator 的第一条消息或上一轮综合）
        echo "### Round $r"
        echo ""

        # 输出本轮所有消息
        jq -r "select(.round == $r) |
          if .role == \"moderator\" then
            \"- **【\\(.name)】【\\(.action)】**：\\(.summary)\"
          elif .role == \"user\" then
            \"- **【用户】**：\\(.content)\"
          else
            \"- 【\\(.name)】【\\(.action)】：\\(.summary)\"
          end" "$jsonl" 2>/dev/null || true

        echo ""
      done
    fi

    # 最终结论（从最后一轮 moderator 综合中提取）
    echo "## 最终结论"
    echo ""
    if [[ -f "$jsonl" ]] && [[ -s "$jsonl" ]]; then
      jq -r "select(.role == \"moderator\" and .action == \"综合\") | .content" "$jsonl" | tail -1
    fi
    echo ""

    echo "## 未解决的开放问题"
    echo ""
    echo "（待 orchestrator 填充）"
    echo ""

    echo "## 行动建议"
    echo ""
    echo "（待 orchestrator 填充）"

  } > "$output_file"

  # 更新 meta.json
  jq '.status = "completed"' "$meta" > "$meta.tmp" && mv "$meta.tmp" "$meta"

  echo "文档已生成：$output_file"
}

cmd_status() {
  local session_dir
  session_dir=$(_session_dir)
  local meta="$session_dir/meta.json"

  if [[ ! -f "$meta" ]]; then
    echo "错误：meta.json 不存在。" >&2
    exit 1
  fi

  jq -r '"Session:      \(.session_id)\nTopic:        \(.topic)\nStatus:       \(.status)\nRound:        \(.current_round)\nParticipants: \(.participants | length)\nCreated:      \(.created_at)"' "$meta"
}

cmd_watch() {
  local session_dir
  session_dir=$(_session_dir)
  local meta="$session_dir/meta.json"
  local responses_dir="$session_dir/responses"

  local sid
  sid=$(jq -r '.session_id' "$meta")
  local current_round
  current_round=$(jq -r '.current_round' "$meta")
  local topic
  topic=$(jq -r '.topic' "$meta")
  local tmux_session="rt-${sid}"

  # 解析参数
  local round="$current_round"
  local follow=false
  local tail_lines=20
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f|--follow) follow=true; shift ;;
      -n)          tail_lines="$2"; shift 2 ;;
      [0-9]*)      round="$1"; shift ;;
      *)           shift ;;
    esac
  done

  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║  🎙️  Round Table Watch — Round ${round}"
  echo "║  📋 ${topic}"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""

  # 显示每个参与者的当前输出
  local participant_count
  participant_count=$(jq '.participants | length' "$meta")

  local has_output=false
  local active_files=()

  for i in $(seq 0 $((participant_count - 1))); do
    local role_id name runtime model
    role_id=$(jq -r ".participants[$i].id" "$meta")
    name=$(jq -r ".participants[$i].name" "$meta")
    runtime=$(jq -r ".participants[$i].runtime" "$meta")
    model=$(jq -r ".participants[$i].model" "$meta")
    local ofile="$responses_dir/round-${round}-${role_id}.md"

    # 检查 tmux window 是否活跃
    local status_icon="❌"
    if tmux has-session -t "$tmux_session" 2>/dev/null; then
      if tmux list-windows -t "$tmux_session" -F '#{window_name}' 2>/dev/null | grep -qx "$role_id"; then
        status_icon="✍️"
      elif [[ -f "$ofile" ]] && [[ -s "$ofile" ]]; then
        status_icon="✅"
      fi
    elif [[ -f "$ofile" ]] && [[ -s "$ofile" ]]; then
      status_icon="✅"
    fi

    echo "┌─ ${status_icon} ${name} (${runtime}/${model})"
    echo "│"

    if [[ -f "$ofile" ]] && [[ -s "$ofile" ]]; then
      has_output=true
      # 显示尾部内容，带缩进
      tail -n "$tail_lines" "$ofile" | sed 's/^/│  /'
      local wc_chars
      wc_chars=$(wc -c < "$ofile")
      echo "│"
      echo "│  [${wc_chars} 字节]"
      active_files+=("$ofile")
    else
      echo "│  （尚无输出）"
    fi

    echo "└──────────────────────────────────────"
    echo ""
  done

  # follow 模式：持续监听输出变化
  if $follow && [[ ${#active_files[@]} -gt 0 ]]; then
    echo "━━━ 实时流（Ctrl+C 退出）━━━"
    echo ""
    # 用 tail -f 追踪所有输出文件
    tail -f "${active_files[@]}" 2>/dev/null
  elif $follow; then
    echo "暂无输出文件可追踪。参与者可能尚未启动。"
  fi
}

cmd_attach() {
  local session_dir
  session_dir=$(_session_dir)
  local meta="$session_dir/meta.json"
  local sid
  sid=$(jq -r '.session_id' "$meta")
  local tmux_session="rt-${sid}"

  if ! tmux has-session -t "$tmux_session" 2>/dev/null; then
    echo "错误：tmux session '$tmux_session' 不存在（参与者可能已全部完成）。" >&2
    echo "提示：使用 omp-round-table watch 查看已完成的输出。" >&2
    exit 1
  fi

  echo "正在连接 tmux session: $tmux_session"
  echo "提示：Ctrl+B D 退出（不终止参与者）"
  exec tmux attach -t "$tmux_session"
}

# --- 主入口 ---

cmd="${1:-}"
shift || true

case "$cmd" in
  init)         cmd_init "$@" ;;
  get-context)  cmd_get_context "$@" ;;
  get-messages) cmd_get_messages "$@" ;;
  post-message) cmd_post_message "$@" ;;
  end)          cmd_end "$@" ;;
  status)       cmd_status "$@" ;;
  watch)        cmd_watch "$@" ;;
  attach)       cmd_attach "$@" ;;
  *)
    echo "用法：session.sh <init|get-context|get-messages|post-message|end|status|watch|attach> [args]" >&2
    exit 1
    ;;
esac
