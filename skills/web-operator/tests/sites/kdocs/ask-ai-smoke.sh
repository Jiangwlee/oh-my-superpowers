#!/usr/bin/env bash
# Smoke test: run kdocs ask-ai.sh and validate the output structure.
# Requires a 365.kdocs.cn/latest tab with Docs Chat available in Chrome.
# Exits 0 on success, non-zero on failure.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASK_AI="${SCRIPT_DIR}/../../../scripts/sites/kdocs/ask-ai.sh"
QUERY="${CDP_TEST_KDOCS_AI_QUERY:-天基遥感 经费}"
OUTPUT=$("$ASK_AI" "$QUERY" 2>&1)
echo "$OUTPUT" | jq -e '
  type == "object"
  and .question != null
  and (.question | length > 0)
  and .scope == "all_parsed_files"
  and .answer != null
  and (.answer | length > 0)
  and (.references | type == "array")
  and (.main_target | type == "string")
  and (.main_target | length > 0)
' >/dev/null
echo "$OUTPUT"
