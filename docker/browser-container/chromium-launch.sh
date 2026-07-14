#!/usr/bin/env bash
# Chromium launcher. Wraps the static supervisord command so proxy flags can be
# added conditionally: --proxy-server is only valid when a proxy is configured,
# and Chromium (GUI) does not honour http_proxy env vars, so the flag is the
# only reliable path.
set -euo pipefail

args=(
  --no-sandbox --no-first-run --no-default-browser-check --disable-gpu
  --disable-dev-shm-usage --window-size=1280,800 --disable-infobars
  --user-data-dir=/data/profile
  --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1
)

if [ -n "${OMP_BROWSER_PROXY:-}" ]; then
  args+=(--proxy-server="${OMP_BROWSER_PROXY}")
  [ -n "${OMP_BROWSER_NO_PROXY:-}" ] && args+=(--proxy-bypass-list="${OMP_BROWSER_NO_PROXY}")
fi

exec /usr/bin/chromium "${args[@]}" about:blank
