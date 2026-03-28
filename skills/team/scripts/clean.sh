#!/usr/bin/env bash
# clean.sh — ANSI 转义清洗工具
#
# 从 stdin 或文件参数读取，strip 所有 ANSI escape sequences（颜色、光标移动等），
# 输出纯文本到 stdout。
#
# Usage:
#   clean.sh <file>        从文件读取
#   cat file | clean.sh    从 stdin 读取

set -euo pipefail

if [[ $# -ge 1 ]]; then
  cat "$1"
else
  cat
fi | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g; s/\x1b\][^\x07]*\x07//g; s/\x1b\[[0-9;]*[mGKHJ]//g; s/\x1b(B//g; s/\x1b\[?[0-9;]*[hl]//g; s/\r//g'
