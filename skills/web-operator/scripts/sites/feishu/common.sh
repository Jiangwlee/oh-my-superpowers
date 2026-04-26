#!/usr/bin/env bash
# Shared helpers for the web-operator feishu admin workflows.
# Public interface: feishu_find_target.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=../../core/common.sh
source "${SCRIPT_DIR}/../../core/common.sh"

require_cmd jq

FEISHU_ADMIN_HOME="https://www.feishu.cn/approval/admin"

feishu_find_target() {
  local preferred="${1:-}"
  if [[ -n "$preferred" ]]; then
    printf '%s\n' "$preferred"
    return 0
  fi
  find_or_create_tab "$FEISHU_ADMIN_HOME" "feishu.cn"
}
