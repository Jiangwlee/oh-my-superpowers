#!/usr/bin/env bash
# Generate an image on chatgpt.com/images and save it locally.
# Input: prompt plus options; see generate-image.mjs --help.
# Output: saved path or JSON, depending on --json.

set -euo pipefail

CHATGPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
node "$CHATGPT_DIR/generate-image.mjs" "$@"
