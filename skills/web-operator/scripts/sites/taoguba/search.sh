#!/usr/bin/env bash
# Search authenticated Taoguba discussions with verified year and sort filters.
# Input: query, optional limit, required --year, optional --sort/--target.
# Output: one compact JSON object containing filter evidence and search results.
# Public interface:
#   search.sh <query> [limit] --year YYYY [--sort hot|latest] [--target PREFIX]
#
# The workflow fails closed when authentication, discussion type, year, or sort
# cannot be verified. It extracts only .topic_Item search cards, never sidebar
# recommendations, and follows result pagination until the requested limit.

set -euo pipefail

TAOGUBA_SEARCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${TAOGUBA_SEARCH_DIR}/common.sh"

require_cmd jq

KEYWORD="${1:-}"
[[ -n "$KEYWORD" ]] && shift || true

LIMIT="10"
if [[ $# -gt 0 && "$1" != --* ]]; then
  LIMIT="$1"
  shift
fi

YEAR=""
SORT="hot"
TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --year)
      [[ $# -ge 2 ]] || {
        jq -cn '{ok:false,site:"taoguba",error:{code:"missing_option_value",message:"--year requires a value",hint:"Pass `--year YYYY`."}}' >&2
        exit 2
      }
      YEAR="${2:-}"
      shift 2
      ;;
    --sort)
      [[ $# -ge 2 ]] || {
        jq -cn '{ok:false,site:"taoguba",error:{code:"missing_option_value",message:"--sort requires a value",hint:"Pass `--sort hot` or `--sort latest`."}}' >&2
        exit 2
      }
      SORT="${2:-}"
      shift 2
      ;;
    --target)
      [[ $# -ge 2 ]] || {
        jq -cn '{ok:false,site:"taoguba",error:{code:"missing_option_value",message:"--target requires a value",hint:"Pass a CDP target prefix after --target."}}' >&2
        exit 2
      }
      TARGET="${2:-}"
      shift 2
      ;;
    *)
      jq -cn --arg value "$1" \
        '{ok:false,site:"taoguba",error:{code:"unknown_argument",message:("unknown argument: " + $value),hint:"Run `omp web-operator search --help` for the supported interface."}}' >&2
      exit 2
      ;;
  esac
done

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

[[ -n "$KEYWORD" ]] || {
  emit_error \
    "missing_query" \
    "Taoguba search requires a non-empty query" \
    "Pass the query as the first positional argument."
  exit 2
}

if [[ ! "$LIMIT" =~ ^[0-9]+$ ]] || (( LIMIT < 1 || LIMIT > 50 )); then
  emit_error \
    "invalid_limit" \
    "limit must be a positive integer no greater than 50" \
    "Pass a result limit between 1 and 50."
  exit 2
fi

[[ "$YEAR" =~ ^[0-9]{4}$ ]] || {
  emit_error \
    "invalid_year" \
    "Taoguba search requires an explicit four-digit year" \
    "Pass --year YYYY, for example --year 2024."
  exit 2
}

[[ "$SORT" == "hot" || "$SORT" == "latest" ]] || {
  emit_error \
    "invalid_sort" \
    "Taoguba sort must be hot or latest" \
    "Pass --sort hot or --sort latest."
  exit 2
}

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

ENCODED_KEYWORD="$(url_encode "$KEYWORD")"
SEARCH_URL="https://www.tgb.cn/search/search?searchContent=${ENCODED_KEYWORD}&type=0"

if ! taoguba_nav_fast "$TARGET" "$SEARCH_URL" >/dev/null 2>&1; then
  emit_error \
    "browser_unavailable" \
    "Chrome could not navigate to Taoguba search" \
    "Confirm the CDP tab is reachable and retry."
  exit 4
fi
if ! wait_for_url_contains "$TARGET" "/search/search" 12000 2>/dev/null; then
  emit_error \
    "page_not_ready" \
    "Taoguba search did not become ready before timeout" \
    "Inspect the tab for a network or verification page."
  exit 4
fi
if ! wait_for_taoguba_text "$TARGET" "讨论" 12000 2>/dev/null; then
  emit_error \
    "page_not_ready" \
    "Taoguba search controls did not become ready before timeout" \
    "Inspect the tab for a network or verification page."
  exit 4
fi

read -r -d '' SEARCH_EXPR <<'EOF' || true
(async () => {
  const requestedYear = YEAR_VALUE;
  const requestedSort = SORT_VALUE;
  const requestedLimit = LIMIT_VALUE;
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const visible = (element) =>
    Boolean(element && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
  const normalize = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const fail = (code, message, hint) => ({
    ok: false,
    site: 'taoguba',
    error: { code, message, hint }
  });
  const waitFor = async (predicate, timeoutMs = 12000) => {
    const timeoutAt = Date.now() + timeoutMs;
    while (Date.now() < timeoutAt) {
      const value = predicate();
      if (value) return value;
      await sleep(150);
    }
    return null;
  };
  const waitForAjax = async () => {
    await sleep(150);
    if (window.jQuery) {
      const settled = await waitFor(() => window.jQuery.active === 0);
      if (!settled) return false;
    }
    await sleep(250);
    return true;
  };
  const activePage = () =>
    Number(document.querySelector('.js-page-btn.N_now_page')?.getAttribute('data-page') || 1);
  const pageSignature = () =>
    [...document.querySelectorAll('.topic_Item .js-topic-subject')]
      .map(element => element.getAttribute('href') || '')
      .join('|');
  const resultYears = () =>
    [...document.querySelectorAll('.topic_Item .Item_time')]
      .map(element => normalize(element.textContent).match(/^(\d{4})-/)?.[1])
      .filter(Boolean);
  const countFrom = (container, selector) => {
    const match = normalize(container.querySelector(selector)?.textContent).match(/\((\d+)\)/);
    return match ? Number(match[1]) : null;
  };
  const sourceTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  const normalizePublishedAt = (displayed) => {
    const match = String(displayed || '')
      .match(/(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})/);
    if (!match) return null;
    const [, year, month, day, hour, minute] = match;
    const localTime = new Date(
      Number(year),
      Number(month) - 1,
      Number(day),
      Number(hour),
      Number(minute)
    );
    const parts = Object.fromEntries(
      new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Asia/Shanghai',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hourCycle: 'h23'
      }).formatToParts(localTime).map(part => [part.type, part.value])
    );
    return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}+08:00`;
  };
  const extractPage = (pageNumber) =>
    [...document.querySelectorAll('.topic_Item')].map(container => {
      const link = container.querySelector('.js-topic-subject');
      const href = link?.getAttribute('href') || '';
      const displayedTime = normalize(container.querySelector('.Item_time')?.textContent);
      return {
        title: normalize(link?.textContent),
        url: href ? new URL(href, location.origin).href : '',
        author: normalize(container.querySelector('.topic_Item_name')?.textContent),
        displayed_time: displayedTime,
        abstract: normalize(container.querySelector('.topic_text')?.textContent),
        likes: countFrom(container, '.topic_zan'),
        views: countFrom(container, '.topic_view'),
        comments: countFrom(container, '.topic_dicuss'),
        published_at_asia_shanghai: normalizePublishedAt(displayedTime),
        page: pageNumber
      };
    }).filter(result => result.title && result.url);

  const userEntry = document.querySelector(
    '.right.header-user a[href*="/user/getSelfInfo"],.right.header-user a[href*="/blog/"]'
  );
  if (!visible(userEntry)) {
    return fail(
      'authentication_required',
      'Taoguba search requires a signed-in Chrome session',
      'Run `omp web-operator taoguba login`, then retry.'
    );
  }

  const controls = await waitFor(() => {
    const yearSelect = document.querySelector('#changetime');
    const hotSort = document.querySelector('.hot_type[data-topic-type="2"]');
    const latestSort = document.querySelector('.new_type[data-topic-type="3"]');
    const activeType = document.querySelector('.s_type_act');
    return yearSelect && visible(hotSort) && visible(latestSort) && activeType
      ? { yearSelect, hotSort, latestSort, activeType }
      : null;
  });
  if (!controls) {
    return fail(
      'page_schema_changed',
      'Taoguba search controls could not be located',
      'Inspect the search page selectors before retrying.'
    );
  }
  if (normalize(controls.activeType.textContent) !== '讨论') {
    return fail(
      'content_type_not_applied',
      'Taoguba search is not showing discussion results',
      'Ensure the search URL uses type=0 and retry.'
    );
  }

  const yearOption = [...controls.yearSelect.options]
    .find(option => option.value === requestedYear);
  if (!yearOption) {
    return fail(
      'year_unavailable',
      `Taoguba does not offer ${requestedYear} in the year selector`,
      'Choose one of the years currently shown in the search page.'
    );
  }
  if (controls.yearSelect.value !== requestedYear) {
    controls.yearSelect.value = requestedYear;
    controls.yearSelect.dispatchEvent(new Event('change', { bubbles: true }));
    const yearSelected = await waitFor(() => controls.yearSelect.value === requestedYear);
    if (!yearSelected || !(await waitForAjax())) {
      return fail(
        'year_filter_not_applied',
        `Taoguba did not apply year ${requestedYear}`,
        'Inspect the year selector and its page event handler.'
      );
    }
  }

  const requestedSortElement = requestedSort === 'hot'
    ? controls.hotSort
    : controls.latestSort;
  if (!requestedSortElement.classList.contains('topic_type_act')) {
    requestedSortElement.click();
    const sortSelected = await waitFor(
      () => requestedSortElement.classList.contains('topic_type_act')
    );
    if (!sortSelected || !(await waitForAjax())) {
      return fail(
        'sort_filter_not_applied',
        `Taoguba did not apply ${requestedSort} sorting`,
        'Inspect the sorting control and its page event handler.'
      );
    }
  }

  const currentYear = controls.yearSelect.value;
  const activeSortElement = document.querySelector('.topic_type.topic_type_act');
  const currentSort = activeSortElement?.getAttribute('data-topic-type') === '2'
    ? 'hot'
    : activeSortElement?.getAttribute('data-topic-type') === '3'
      ? 'latest'
      : '';
  if (currentYear !== requestedYear || currentSort !== requestedSort) {
    return fail(
      'filter_verification_failed',
      'Taoguba search filters do not match the requested filters',
      'Retry after inspecting the visible year and sort controls.'
    );
  }

  const firstPageReady = await waitFor(() =>
    document.querySelector('.topic_Items') ||
    document.querySelector('.pc_searchCount')
  );
  if (!firstPageReady) {
    return fail(
      'results_not_ready',
      'Taoguba search results did not become ready',
      'Inspect the visible page for an error or schema change.'
    );
  }

  const firstPageYears = resultYears();
  if (firstPageYears.some(year => year !== requestedYear)) {
    return fail(
      'year_filter_not_applied',
      'Taoguba returned result cards outside the requested year',
      'Retry after verifying the visible year selector.'
    );
  }

  const totalPages = Math.max(
    1,
    ...[...document.querySelectorAll('.js-page-btn')]
      .map(element => Number(element.getAttribute('data-total') || 0))
  );
  const availableText = normalize(document.querySelector('.pc_searchCount')?.textContent);
  const availableResults = /^\d+$/.test(availableText) ? Number(availableText) : null;
  const collected = [];
  const seen = new Set();
  const pagesVisited = [];

  const collectCurrentPage = () => {
    const pageNumber = activePage();
    pagesVisited.push(pageNumber);
    for (const result of extractPage(pageNumber)) {
      if (seen.has(result.url)) continue;
      seen.add(result.url);
      collected.push(result);
      if (collected.length >= requestedLimit) break;
    }
  };

  collectCurrentPage();
  while (collected.length < requestedLimit && activePage() < totalPages) {
    const nextPage = activePage() + 1;
    const nextButton = document.querySelector(
      `.js-page-btn[data-page="${nextPage}"]`
    );
    if (!nextButton) {
      return fail(
        'pagination_control_missing',
        `Taoguba page ${nextPage} control is missing`,
        'Inspect the search pagination schema before retrying.'
      );
    }
    const previousSignature = pageSignature();
    nextButton.click();
    const pageChanged = await waitFor(() =>
      activePage() === nextPage && pageSignature() !== previousSignature
    );
    if (!pageChanged || !(await waitForAjax())) {
      return fail(
        'pagination_failed',
        `Taoguba did not load result page ${nextPage}`,
        'Retry after inspecting the visible pagination controls.'
      );
    }
    if (
      controls.yearSelect.value !== requestedYear ||
      !requestedSortElement.classList.contains('topic_type_act') ||
      resultYears().some(year => year !== requestedYear)
    ) {
      return fail(
        'filter_verification_failed',
        `Taoguba filters changed while loading page ${nextPage}`,
        'Retry after inspecting the visible year and sort controls.'
      );
    }
    collectCurrentPage();
  }

  const results = collected.slice(0, requestedLimit)
    .map((result, index) => ({ rank: index + 1, ...result }));
  return {
    schema_version: 1,
    ok: true,
    site: 'taoguba',
    generated_at: new Date().toISOString(),
    query: QUERY_VALUE,
    year: Number(requestedYear),
    sort: requestedSort,
    requested_filters: {
      content_type: 'discussion',
      year: requestedYear,
      sort: requestedSort
    },
    applied_filters: {
      content_type: 'discussion',
      content_type_label: normalize(controls.activeType.textContent),
      year: controls.yearSelect.value,
      year_label: normalize(controls.yearSelect.selectedOptions[0]?.textContent),
      sort: currentSort,
      sort_label: normalize(activeSortElement?.textContent)
    },
    pagination: {
      pages_visited: [...new Set(pagesVisited)],
      pages_available: totalPages,
      results_available: availableResults
    },
    source: {
      site: '淘股吧',
      search_url: location.href,
      access: 'logged-in local Chrome via loopback CDP',
      cookies_persisted: false,
      page_meta: {
        url: location.href,
        title: document.title,
        logged_in: true,
        selected_year: controls.yearSelect.value,
        selected_sort: normalize(activeSortElement?.textContent)
      }
    },
    time_normalization: {
      display_timezone: sourceTimezone,
      target_timezone: 'Asia/Shanghai',
      reason: '账户交割日期按中国交易日解释'
    },
    result_count: results.length,
    results
  };
})()
EOF

SEARCH_EXPR="${SEARCH_EXPR/YEAR_VALUE/$(jq -Rn --arg value "$YEAR" '$value')}"
SEARCH_EXPR="${SEARCH_EXPR/SORT_VALUE/$(jq -Rn --arg value "$SORT" '$value')}"
SEARCH_EXPR="${SEARCH_EXPR/LIMIT_VALUE/${LIMIT}}"
SEARCH_EXPR="${SEARCH_EXPR/QUERY_VALUE/$(jq -Rn --arg value "$KEYWORD" '$value')}"

if ! SEARCH_RESULT="$(cdp_eval "$TARGET" "$SEARCH_EXPR" 2>/dev/null)"; then
  emit_error \
    "browser_workflow_failed" \
    "Chrome could not complete the Taoguba search workflow" \
    "Confirm the CDP tab is reachable and inspect the visible search page."
  exit 4
fi
if ! jq -e 'type == "object" and has("ok")' >/dev/null 2>&1 <<<"$SEARCH_RESULT"; then
  emit_error \
    "invalid_browser_response" \
    "Taoguba search returned an invalid browser response" \
    "Inspect the current search page DOM and CDP connection."
  exit 1
fi
if [[ "$(jq -r '.ok' <<<"$SEARCH_RESULT")" != "true" ]]; then
  jq -c . <<<"$SEARCH_RESULT" >&2
  case "$(jq -r '.error.code // empty' <<<"$SEARCH_RESULT")" in
    authentication_required) exit 4 ;;
    *) exit 1 ;;
  esac
fi

jq -c . <<<"$SEARCH_RESULT"
