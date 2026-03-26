#!/usr/bin/env bash
# search.sh — search GitHub via gh CLI (repos + issues + discussions).
# Input:  <query> [limit]
# Output: JSON array of { type, title, summary, url, stars?, repo?, labels? }
#
# Searches repos, issues, and discussions in parallel via gh CLI.
# No browser/CDP needed — pure API calls.
#
# Requires: gh (authenticated), jq

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

require_cmd() { command -v "$1" &>/dev/null || { echo "error: $1 not found" >&2; exit 1; }; }
require_cmd gh
require_cmd jq

usage() {
  printf 'usage: %s <query> [limit]\n' "$(basename "$0")" >&2
  exit 1
}

QUERY="${1:-}"
LIMIT="${2:-20}"

[[ -n "$QUERY" ]] || usage
[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }
(( LIMIT > 60 )) && LIMIT=60

# allocate limits per category (repos gets fewer, issues/discussions get more)
REPO_LIMIT=$(( LIMIT / 3 ))
ISSUE_LIMIT=$(( LIMIT / 3 ))
DISC_LIMIT=$(( LIMIT - REPO_LIMIT - ISSUE_LIMIT ))
(( REPO_LIMIT < 3 )) && REPO_LIMIT=3
(( ISSUE_LIMIT < 3 )) && ISSUE_LIMIT=3
(( DISC_LIMIT < 3 )) && DISC_LIMIT=3

TMPDIR_BASE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

# --- repos -------------------------------------------------------------------
(
  gh search repos "$QUERY" \
    --json fullName,description,url,stargazersCount,updatedAt \
    --limit "$REPO_LIMIT" 2>/dev/null \
  | jq '[.[] | {
      type: "repo",
      title: .fullName,
      summary: (.description // "" | .[0:280]),
      url: .url,
      stars: .stargazersCount,
      updated_at: .updatedAt
    }]' > "${TMPDIR_BASE}/repos.json" 2>/dev/null
) &
PID_REPOS=$!

# --- issues -------------------------------------------------------------------
(
  gh search issues "$QUERY" \
    --json title,url,repository,state,labels,commentsCount,updatedAt,body \
    --limit "$ISSUE_LIMIT" 2>/dev/null \
  | jq '[.[] | {
      type: (if .isPullRequest then "pr" else "issue" end),
      title: .title,
      summary: ((.body // "")[0:280] | gsub("\n"; " ")),
      url: .url,
      repo: (.repository.nameWithOwner // .repository.name // ""),
      state: .state,
      labels: ([.labels[]?.name] | join(", ")),
      comments: .commentsCount,
      updated_at: .updatedAt
    }]' > "${TMPDIR_BASE}/issues.json" 2>/dev/null
) &
PID_ISSUES=$!

# --- discussions (via GraphQL, gh doesn't have gh search discussions) ---------
(
  # Use GitHub search API via gh api for discussions
  ENCODED_QUERY=$(printf '%s' "$QUERY type:discussions" | jq -sRr @uri)
  gh api "search/issues?q=${ENCODED_QUERY}&per_page=${DISC_LIMIT}" 2>/dev/null \
  | jq '[(.items // [])[] | {
      type: "discussion",
      title: .title,
      summary: ((.body // "")[0:280] | gsub("\n"; " ")),
      url: .html_url,
      repo: (.repository_url // "" | split("/") | .[-2:] | join("/")),
      comments: .comments,
      updated_at: .updated_at
    }]' > "${TMPDIR_BASE}/discussions.json" 2>/dev/null
) &
PID_DISC=$!

# --- wait & merge -------------------------------------------------------------
wait "$PID_REPOS" 2>/dev/null || true
wait "$PID_ISSUES" 2>/dev/null || true
wait "$PID_DISC" 2>/dev/null || true

# merge all results, default to empty array if any file missing/invalid
jq -s '
  [ .[][] ] | .[0:'"$LIMIT"']
' "${TMPDIR_BASE}/repos.json" \
  "${TMPDIR_BASE}/issues.json" \
  "${TMPDIR_BASE}/discussions.json" 2>/dev/null \
|| jq -n '[]'
