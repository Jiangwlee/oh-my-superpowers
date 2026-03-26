#!/usr/bin/env bash
# This script searches Taoguba discussions by keyword and returns results sorted by popularity.
# Input: search keyword, optional result limit, and optional target prefix.
# Output: a JSON array of discussion posts with title, author, time, stats, and url.
# Public interface: taoguba-search.sh <keyword> [limit] [target_prefix].
#
# The script navigates to the search page with the keyword, switches to "讨论" (discussions) tab,
# sorts by "最热" (hottest), and extracts the post list.
# The default limit is 10 results.
# The script depends on jq and the sibling common.sh helpers.
# Errors are printed to stderr and the script exits non-zero.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

KEYWORD="${1:-}"
LIMIT="${2:-10}"
TARGET="${3:-}"

[[ -n "$KEYWORD" ]] || {
  printf 'usage: %s <keyword> [limit] [target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }

TARGET="$(taoguba_find_target "$TARGET" "tgb\.cn/(search/|a/|jinghua/)")"
[[ -n "$TARGET" ]] || { printf 'no usable Taoguba tab found\n' >&2; exit 1; }

# URL encode the keyword
ENCODED_KEYWORD=$(jq -nr --arg k "$KEYWORD" '$k | @uri')
SEARCH_URL="https://www.tgb.cn/search/search?searchContent=${ENCODED_KEYWORD}&type=0"

taoguba_nav_fast "$TARGET" "$SEARCH_URL"
wait_for_url_contains "$TARGET" "/search/search"

# Wait for search results to load - look for common search result indicators
wait_for_taoguba_text "$TARGET" "讨论" || wait_for_taoguba_text "$TARGET" "搜索"

# Click on "讨论" tab if not already active, then sort by "最热"
read -r -d '' SETUP_EXPR <<'EOF' || true
(async () => {
  // Wait a bit for the page to settle
  await new Promise(resolve => setTimeout(resolve, 800));
  
  // Find and click "讨论" tab if exists and not active
  const tabs = Array.from(document.querySelectorAll('a, button, span, div'));
  const discussTab = tabs.find(el => el.textContent.trim() === '讨论' && el.getAttribute('role') !== 'tab');
  if (discussTab) {
    discussTab.click();
    await new Promise(resolve => setTimeout(resolve, 600));
  }
  
  // Find and click "最热" sort option
  const sortOptions = Array.from(document.querySelectorAll('a, button, span'));
  const hotSort = sortOptions.find(el => el.textContent.trim() === '最热');
  if (hotSort) {
    hotSort.click();
    await new Promise(resolve => setTimeout(resolve, 800));
  }
  
  return 'SETUP_DONE';
})()
EOF

# Try to setup the page (switch to discussions and sort by hot), but don't fail if elements aren't found
cdp_eval "$TARGET" "$SETUP_EXPR" >/dev/null 2>&1 || true

# Wait for results to load after sorting
sleep 1

# Extract search results - directly scan all links like manual extraction in logs
read -r -d '' EXPR <<'EOF' || true
(() => {
  const limit = LIMIT_VALUE;
  const normalizeUrl = (href) => {
    if (!href) return '';
    if (href.startsWith('http')) return href;
    return new URL(href.replace(/^\//, ''), 'https://www.tgb.cn/').href;
  };
  
  const results = [];
  const seen = new Set();
  
  // Directly scan all <a> tags - this matches the working approach in logs
  const allLinks = Array.from(document.querySelectorAll('a'));
  
  for (const link of allLinks) {
    if (results.length >= limit) break;
    
    const href = link.getAttribute('href') || link.href || '';
    
    // Filter: must contain /a/ (post path), exclude fragments
    if (!href.includes('/a/') || href.includes('#')) continue;
    
    const title = (link.innerText || link.textContent || '').trim();
    
    // Filter: reasonable title length, exclude navigation links
    if (title.length < 10 || title.length > 200) continue;
    if (title.includes('发帖') || title.includes('首页') || 
        title.includes('淘股吧') || title === '查看原文') continue;
    
    let url = normalizeUrl(href);
    // Fix malformed URLs like https://www.tgb.cna/xxx
    url = url.replace(/^https:\/\/www\.tgb\.cna\//, 'https://www.tgb.cn/a/');
    
    if (seen.has(url)) continue;
    seen.add(url);
    
    // Try to extract additional info from parent container
    let container = link.parentElement;
    let containerText = '';
    for (let i = 0; i < 4 && container; i++) {
      containerText = (container.innerText || container.textContent || '').trim();
      if (containerText.length > title.length + 20) break;
      container = container.parentElement;
    }
    
    // Try to find author - look for .hot_item_name element or blog link
    let author = '';
    
    // Pattern 1: Look for .hot_item_name in ancestor container (search result page structure)
    if (container) {
      const itemContainer = container.closest('.hot_item') || container;
      const nameEl = itemContainer.querySelector('.hot_item_name');
      if (nameEl) {
        author = (nameEl.innerText || nameEl.textContent || '').trim();
      }
    }
    
    // Pattern 2: Look for blog link in container
    if (!author && container) {
      const blogLink = container.querySelector('a[href*="/blog/"]');
      if (blogLink) {
        const authorText = (blogLink.innerText || blogLink.textContent || '').trim();
        if (authorText && authorText.length < 20 && !authorText.includes('评论')) {
          author = authorText;
        }
      }
    }
    
    // Pattern 3: "username吧" fallback
    if (!author) {
      const textWithoutTitle = containerText.replace(title, '').trim();
      const barMatch = textWithoutTitle.match(/([^\s\n(]{2,15})吧/);
      if (barMatch && !barMatch[1].includes('评论') && !barMatch[1].includes('浏览')) {
        author = barMatch[1];
      }
    }
    
    // Try to find time
    let postTime = '';
    const timeMatch = containerText.match(/(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})/) ||
                      containerText.match(/(\d{2}-\d{2}\s+\d{2}:\d{2})/);
    if (timeMatch) postTime = timeMatch[1];
    
    // Try to find stats
    let stats = '';
    const browseMatch = containerText.match(/浏览[：:]?\s*(\d+)/);
    const commentMatch = containerText.match(/评论[：:]?\s*(\d+)/);
    if (browseMatch && commentMatch) {
      stats = `${browseMatch[1]} / ${commentMatch[1]}`;
    } else if (browseMatch) {
      stats = `${browseMatch[1]} / 0`;
    } else if (commentMatch) {
      stats = `0 / ${commentMatch[1]}`;
    }
    
    results.push({
      title,
      author,
      post_time: postTime,
      stats,
      url
    });
  }
  
  return results;
})()
EOF
EXPR="${EXPR/LIMIT_VALUE/${LIMIT}}"

cdp_eval "$TARGET" "$EXPR"
