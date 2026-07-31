#!/usr/bin/env bash
# Read one authenticated Taoguba main post and its metadata.
# Input: a Taoguba post URL and an optional CDP target prefix.
# Output: one compact JSON object with the main post, metadata, and source facts.
# Public interface: open-post.sh <post_url> [target_prefix].
#
# This is the single Taoguba post-reading implementation used by:
# - omp web-operator taoguba read
# - omp web-operator open-post taoguba
# - omp web-operator read-url for tgb.cn URLs
#
# It reads only the main post and stops before reply floors. Authentication,
# navigation, schema, and extraction failures are emitted as compact JSON on
# stderr. Credentials, cookies, and browser storage are never read or returned.

set -euo pipefail

TAOGUBA_READ_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${TAOGUBA_READ_DIR}/common.sh"

require_cmd jq

POST_URL="${1:-}"
TARGET="${2:-}"

emit_error() {
  local code="$1"
  local message="$2"
  local hint="$3"
  jq -cn \
    --arg code "$code" \
    --arg message "$message" \
    --arg hint "$hint" \
    '{ok:false,site:"taoguba",error:{code:$code,message:$message,hint:$hint}}' >&2
}

[[ -n "$POST_URL" ]] || {
  emit_error \
    "missing_url" \
    "Taoguba read requires a post URL" \
    "Pass https://www.tgb.cn/a/<post-id> as the URL."
  exit 2
}
[[ "$POST_URL" =~ ^https://www\.tgb\.cn/a/[A-Za-z0-9]+([/?#].*)?$ ]] || {
  emit_error \
    "invalid_url" \
    "URL is not a supported Taoguba main-post URL" \
    "Pass a URL shaped like https://www.tgb.cn/a/<post-id>."
  exit 2
}

POST_ID_PART="${POST_URL#https://www.tgb.cn/a/}"
POST_ID="${POST_ID_PART%%[/?#]*}"

if ! TARGET="$(taoguba_find_target "$TARGET" 2>/dev/null)"; then
  emit_error \
    "browser_unavailable" \
    "Chrome could not resolve a Taoguba tab" \
    "Enable Chrome remote debugging and retry."
  exit 4
fi
[[ -n "$TARGET" ]] || {
  emit_error \
    "browser_unavailable" \
    "no usable Taoguba tab was found" \
    "Enable Chrome remote debugging and retry."
  exit 4
}

if ! taoguba_nav_fast "$TARGET" "$POST_URL" >/dev/null 2>&1; then
  emit_error \
    "browser_unavailable" \
    "Chrome could not navigate to the Taoguba post" \
    "Confirm the CDP tab is reachable and retry."
  exit 4
fi
if ! wait_for_url_contains "$TARGET" "/a/" 12000 2>/dev/null; then
  emit_error \
    "page_not_ready" \
    "Taoguba did not reach the requested post before timeout" \
    "Inspect the tab for a network or verification page."
  exit 4
fi

read -r -d '' READ_EXPR <<'EOF' || true
(async () => {
  const requestedPostId = POST_ID_VALUE;
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const visible = (element) =>
    Boolean(element && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
  const normalize = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const fail = (code, message, hint) => ({
    ok: false,
    site: 'taoguba',
    error: { code, message, hint }
  });
  const deadline = Date.now() + 12000;

  while (Date.now() < deadline) {
    const text = document.body?.innerText || '';
    const loginEntry = [...document.querySelectorAll('a')]
      .find(element => visible(element) && normalize(element.textContent) === '登录/注册');
    if (text.includes('淘股吧原创') || loginEntry) break;
    await sleep(200);
  }

  const userEntry = document.querySelector(
    '.right.header-user a[href*="/user/getSelfInfo"],.right.header-user a[href*="/blog/"]'
  );
  if (!visible(userEntry)) {
    return fail(
      'authentication_required',
      'Taoguba post reading requires a signed-in Chrome session',
      'Run `omp web-operator taoguba login`, then retry.'
    );
  }

  const bodyText = document.body?.innerText || '';
  if (!bodyText.includes('淘股吧原创')) {
    return fail(
      'page_schema_changed',
      'Taoguba main-post marker was not found',
      'Inspect the visible post page before retrying.'
    );
  }

  const lines = bodyText
    .split(/\n+/)
    .map(line => line.trim())
    .filter(Boolean);
  const titleParts = (document.title || '')
    .split('_')
    .map(part => normalize(part))
    .filter(Boolean);
  const pageTitle = titleParts[0] || '';
  const title = lines.find(line => line === pageTitle) || pageTitle;
  const titleIndex = title ? lines.indexOf(title) : -1;
  const metaLine = lines.find(line => /淘股吧原创/.test(line)) || '';
  const authorSpace = lines.find(line => /的空间$/.test(line)) || '';
  const titleAuthor = titleParts.find(
    (part, index) =>
      index > 0 &&
      part !== '淘股吧' &&
      part !== '淘股吧原创' &&
      part !== title
  ) || '';
  const author = normalize(authorSpace.replace(/的空间$/, '') || titleAuthor);
  const displayedTime = metaLine.match(/\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}/)?.[0] || '';
  const publishedAtShanghai = displayedTime
    ? `${displayedTime.replace(/\s+/, 'T')}:00+08:00`
    : null;
  const viewsMatch = metaLine.match(/浏览\s+(\d+)/);
  const commentsMatch = metaLine.match(/评论\s+(\d+)/);
  const likesLine = lines.find(line => /^赞\s*[（(]?\s*\d+/.test(line)) || '';
  const likesMatch = likesLine.match(/^赞\s*[（(]?\s*(\d+)/);

  const start = titleIndex >= 0 ? titleIndex + 1 : 0;
  let end = lines.length;
  for (let index = start; index < lines.length; index += 1) {
    if (
      /^第\d+楼/.test(lines[index]) ||
      /^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$/.test(lines[index]) ||
      lines[index] === '举报' ||
      lines[index] === '话题与分类：' ||
      lines[index] === '最早' ||
      lines[index] === '最新评论' ||
      lines[index] === '点赞榜' ||
      lines[index] === '打赏榜' ||
      lines[index] === '查看选项' ||
      lines[index] === '发布回帖'
    ) {
      end = index;
      break;
    }
  }

  const content = lines
    .slice(start, end)
    .filter(line =>
      line &&
      line !== metaLine &&
      !/空间$/.test(line) &&
      line !== '淘股吧原创' &&
      !/^浏览\s+\d+/.test(line) &&
      !/^评论\s+\d+/.test(line) &&
      !/^\d+\s+9\/9/.test(line) &&
      line !== '举报' &&
      line !== '评论 打赏Ta' &&
      line !== '打赏Ta' &&
      !/^分享文章/.test(line) &&
      !/^加油/.test(line) &&
      line !== '只看楼主' &&
      line !== '数据加载中，请等待...'
    )
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (!title || !content) {
    return fail(
      'content_not_found',
      'Taoguba main-post title or content could not be extracted',
      'Inspect the current post DOM before using this result.'
    );
  }

  return {
    schema_version: 1,
    ok: true,
    site: 'taoguba',
    post: {
      post_id: requestedPostId,
      url: location.href,
      title,
      author: author || null,
      displayed_time: displayedTime || null,
      published_at_asia_shanghai: publishedAtShanghai,
      content,
      stats: {
        likes: likesMatch ? Number(likesMatch[1]) : null,
        views: viewsMatch ? Number(viewsMatch[1]) : null,
        comments: commentsMatch ? Number(commentsMatch[1]) : null
      }
    },
    source: {
      access: 'logged-in local Chrome via loopback CDP',
      collected_at: new Date().toISOString(),
      published_time_semantics: 'Asia/Shanghai',
      cookies_persisted: false
    }
  };
})()
EOF
READ_EXPR="${READ_EXPR/POST_ID_VALUE/$(jq -Rn --arg value "$POST_ID" '$value')}"

if ! READ_RESULT="$(cdp_eval "$TARGET" "$READ_EXPR" 2>/dev/null)"; then
  emit_error \
    "browser_workflow_failed" \
    "Chrome could not complete the Taoguba post read" \
    "Confirm the CDP tab is reachable and inspect the visible post."
  exit 4
fi
if ! jq -e 'type == "object" and has("ok")' >/dev/null 2>&1 <<<"$READ_RESULT"; then
  emit_error \
    "invalid_browser_response" \
    "Taoguba post reading returned an invalid browser response" \
    "Inspect the current post DOM and CDP connection."
  exit 1
fi
if [[ "$(jq -r '.ok' <<<"$READ_RESULT")" != "true" ]]; then
  jq -c . <<<"$READ_RESULT" >&2
  case "$(jq -r '.error.code // empty' <<<"$READ_RESULT")" in
    authentication_required) exit 4 ;;
    *) exit 1 ;;
  esac
fi

jq -c . <<<"$READ_RESULT"
