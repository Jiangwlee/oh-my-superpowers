#!/usr/bin/env bash
# T2 (real container): drive the full loop against a running browser-container.
#
#   omp container up browser
#   bash e2e_curl_sequence.sh
#
# Isolates nothing on the host: talks only to the container's REST port.
set -euo pipefail

BASE="${BASE:-http://localhost:8080}"
AUTH=()
[ -n "${OMP_BROWSER_TOKEN:-}" ] && AUTH=(-H "Authorization: Bearer ${OMP_BROWSER_TOKEN}")

jqget() { python3 -c "import sys,json;print(json.load(sys.stdin)$1)"; }

echo "== 0. health =="
curl -sf "${AUTH[@]}" "$BASE/health"; echo

echo "== 1. create session =="
SID=$(curl -sf "${AUTH[@]}" -X POST "$BASE/session" | jqget "['sessionId']")
echo "sessionId=$SID"

echo "== 2. navigate =="
curl -sf "${AUTH[@]}" -X POST "$BASE/session/$SID/act" \
  -H 'content-type: application/json' \
  -d '{"action":"navigate","args":{"url":"https://example.com"}}'; echo

echo "== 3. dom =="
DOM=$(curl -sf "${AUTH[@]}" "$BASE/session/$SID/dom")
echo "$DOM"
COUNT=$(echo "$DOM" | jqget "['count']")

echo "== 4. click index 0 (if any interactive element) =="
if [ "$COUNT" -gt 0 ]; then
  curl -sf "${AUTH[@]}" -X POST "$BASE/session/$SID/act" \
    -H 'content-type: application/json' \
    -d '{"action":"click","args":{"index":0}}'; echo
else
  echo "no interactive elements; skipping click"
fi

echo "== 5. stale contract: click a bogus index must return not-found =="
CODE=$(curl -s -o /dev/null -w '%{http_code}' "${AUTH[@]}" -X POST "$BASE/session/$SID/act" \
  -H 'content-type: application/json' \
  -d '{"action":"click","args":{"index":99999}}')
[ "$CODE" = "409" ] && echo "OK (409 not-found)" || { echo "FAIL: expected 409, got $CODE"; exit 1; }

echo "== done. VNC: http://localhost:6080/vnc.html (viewonly) / :6081 (interactive) =="
