#!/usr/bin/env bash
# Ask WPS Docs Chat a question and return the AI answer plus references.
# Input: a natural-language question and optional main target prefix.
# Output: a JSON object with question, scope, answer, references, and main_target.
# Public interface: kdocs-ask-ai.sh <question> [main_target_prefix].
#
# The script reuses the 365.kdocs.cn/latest tab but does not depend on the UI
# send path. Instead, it calls the reverse-engineered Docs Chat SSE endpoint
# directly from page JS, lets the server create a fresh session, and polls a
# window-scoped result object until the answer and file references are ready.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

usage() {
  printf 'usage: %s <question> [main_target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

QUESTION="${1:-}"
MAIN_TARGET="${2:-}"

[[ -n "$QUESTION" ]] || usage

MAIN_TARGET="$(kdocs_find_main_tab "$MAIN_TARGET")"
[[ -n "$MAIN_TARGET" ]] || { printf 'no usable 365.kdocs.cn/latest tab found\n' >&2; exit 1; }

QUESTION_JSON="$(json_string "$QUESTION")"
TARGET_JSON="$(json_string "$MAIN_TARGET")"

RUN_EXPR=$(cat <<'EOF'
(() => {
  const question = __QUESTION_JSON__;
  const target = __TARGET_JSON__;
  const csrf = document.cookie.match(/(?:^|; )csrf=([^;]+)/)?.[1] || '';
  if (!csrf) throw new Error('Missing csrf cookie for Docs Chat request');

  delete window.__CODEx_QA_RESULT__;
  window.__CODEx_QA_RESULT__ = {
    status: 'running',
    question,
    scope: 'all_parsed_files',
    answer: '',
    references: [],
    session_id: '',
    main_target: target,
    last_citation_text: '',
    last_answer_len: 0,
    last_growth_ts: Date.now(),
    references_first_seen_ts: 0,
    event_codes: []
  };

  (async () => {
    try {
      const body = {
        action: 'qa',
        disable_reference: false,
        intention_code: 'saas_knowledgebase_session',
        no_cache: false,
        product_name: 'saas_knowledgebase_web',
        qa_drive_ids: [],
        qa_group_names: [],
        query_source: 'user_input',
        request_id: `codex_${Date.now()}`,
        scene: 'general',
        scope: 'all',
        searchname: question,
        session_id: '',
        switch_markdown: true,
        switch_thinking: false,
        task_id: '',
        trigger_scene: 'all',
        use_web_search: false,
        csrfmiddlewaretoken: csrf
      };

      const resp = await fetch('https://365.kdocs.cn/insight/api/app/v1/search/gpt', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!resp.ok) {
        throw new Error(`Docs Chat API returned ${resp.status}`);
      }

      const reader = resp.body?.getReader();
      if (!reader) throw new Error('Docs Chat response body is not readable');

      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        let chunk;
        try {
          chunk = await Promise.race([
            reader.read(),
            new Promise((_, reject) => setTimeout(() => reject(new Error('read timeout')), 15000))
          ]);
        } catch (e) {
          if (window.__CODEx_QA_RESULT__.answer) break;
          throw e;
        }
        if (chunk.done) break;

        buffer += decoder.decode(chunk.value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const dataLine = part.split('\n').find(line => line.startsWith('data:'));
          if (!dataLine) continue;

          let payload;
          try {
            payload = JSON.parse(dataLine.slice(5));
          } catch {
            continue;
          }

          const data = payload.data || {};
          if (typeof data.code === 'number') {
            window.__CODEx_QA_RESULT__.event_codes.push(data.code);
          }
          if (typeof data.session_id === 'string' && data.session_id) {
            window.__CODEx_QA_RESULT__.session_id = data.session_id;
          }
          if (typeof data.answer === 'string' && data.answer.trim()) {
            window.__CODEx_QA_RESULT__.answer = data.answer.trim();
          }
          const citationText = Array.isArray(data.dynamic?.answer_citations)
            ? data.dynamic.answer_citations
                .map(item => typeof item?.text === 'string' ? item.text : '')
                .join('')
                .trim()
            : '';
          if (citationText) {
            if (citationText.startsWith(window.__CODEx_QA_RESULT__.answer)) {
              window.__CODEx_QA_RESULT__.answer = citationText;
            } else if (
              citationText !== window.__CODEx_QA_RESULT__.last_citation_text
              && !window.__CODEx_QA_RESULT__.answer.endsWith(citationText)
            ) {
              window.__CODEx_QA_RESULT__.answer += citationText;
            }
            window.__CODEx_QA_RESULT__.last_citation_text = citationText;
          }
          if (Array.isArray(data.result?.files) && data.result.files.length > 0) {
            window.__CODEx_QA_RESULT__.references = data.result.files;
            if (!window.__CODEx_QA_RESULT__.references_first_seen_ts) {
              window.__CODEx_QA_RESULT__.references_first_seen_ts = Date.now();
            }
          }
          if (Array.isArray(data.qa_resources_meta) && data.qa_resources_meta.length > 0) {
            window.__CODEx_QA_RESULT__.references = data.qa_resources_meta;
            if (!window.__CODEx_QA_RESULT__.references_first_seen_ts) {
              window.__CODEx_QA_RESULT__.references_first_seen_ts = Date.now();
            }
          }
          if (Array.isArray(data.dynamic?.answer_citations)) {
            const citationRefs = data.dynamic.answer_citations
              .flatMap(item => [item?.reply_sources, item?.reply_faq_sources])
              .filter(Array.isArray)
              .flat();
            if (citationRefs.length > 0) {
              window.__CODEx_QA_RESULT__.references = citationRefs;
              if (!window.__CODEx_QA_RESULT__.references_first_seen_ts) {
                window.__CODEx_QA_RESULT__.references_first_seen_ts = Date.now();
              }
            }
          }

          const answerLen = window.__CODEx_QA_RESULT__.answer.length;
          if (answerLen > window.__CODEx_QA_RESULT__.last_answer_len) {
            window.__CODEx_QA_RESULT__.last_answer_len = answerLen;
            window.__CODEx_QA_RESULT__.last_growth_ts = Date.now();
          }
        }
      }

      if (window.__CODEx_QA_RESULT__.answer) {
        window.__CODEx_QA_RESULT__.status = 'done';
      } else {
        window.__CODEx_QA_RESULT__.status = 'error';
        window.__CODEx_QA_RESULT__.error = 'Docs Chat SSE finished without a non-empty answer';
      }
    } catch (error) {
      window.__CODEx_QA_RESULT__.status = 'error';
      window.__CODEx_QA_RESULT__.error = String(error?.message || error);
    }
  })();

  return 'STARTED';
})()
EOF
)
RUN_EXPR="${RUN_EXPR//__QUESTION_JSON__/${QUESTION_JSON}}"
RUN_EXPR="${RUN_EXPR//__TARGET_JSON__/${TARGET_JSON}}"
cdp_eval "$MAIN_TARGET" "$RUN_EXPR" >/dev/null

RESULT_STATE=""
MIN_ANSWER_LEN=200
STABLE_MS=3000
REFERENCE_GRACE_MS=5000
for _ in $(seq 1 90); do
  RESULT_STATE="$(cdp_eval "$MAIN_TARGET" '(() => JSON.stringify(window.__CODEx_QA_RESULT__ || null))()' 2>/dev/null || true)"
  if [[ -n "$RESULT_STATE" && "$RESULT_STATE" != "null" ]]; then
    STATUS="$(jq -r '.status // ""' <<<"$RESULT_STATE" 2>/dev/null || true)"
    ANSWER_LEN="$(jq -r '(.answer // "") | length' <<<"$RESULT_STATE" 2>/dev/null || true)"
    REF_LEN="$(jq -r '(.references // []) | length' <<<"$RESULT_STATE" 2>/dev/null || true)"
    LAST_GROWTH_TS="$(jq -r '.last_growth_ts // 0' <<<"$RESULT_STATE" 2>/dev/null || true)"
    NOW_TS="$(date +%s%3N)"
    STABLE_FOR=0
    if [[ "$LAST_GROWTH_TS" =~ ^[0-9]+$ ]]; then
      STABLE_FOR=$(( NOW_TS - LAST_GROWTH_TS ))
    fi
    if [[ "$STATUS" == "done" || "$STATUS" == "error" ]]; then
      break
    fi
    if [[ "$ANSWER_LEN" =~ ^[0-9]+$ ]] && [[ "$REF_LEN" =~ ^[0-9]+$ ]] && (( ANSWER_LEN >= MIN_ANSWER_LEN )) && (( STABLE_FOR >= STABLE_MS )); then
      break
    fi
  fi
  sleep 1
done

[[ -n "$RESULT_STATE" && "$RESULT_STATE" != "null" ]] || {
  printf 'Docs Chat result was not produced in time\n' >&2
  exit 1
}

STATUS="$(jq -r '.status // ""' <<<"$RESULT_STATE")"
ANSWER_LEN="$(jq -r '(.answer // "") | length' <<<"$RESULT_STATE")"
if [[ "$STATUS" == "error" && "$ANSWER_LEN" -eq 0 ]]; then
  jq -r '.error // "Docs Chat request failed"' <<<"$RESULT_STATE" >&2
  exit 1
fi

RESULT_EXPR=$(cat <<'EOF'
(() => {
  const result = window.__CODEx_QA_RESULT__ || {};
  const references = Array.isArray(result.references) ? result.references.map((file, idx) => ({
    index: Number(file.seq || file.index || idx + 1),
    title: file.title || file.name || file.file_name || file.fileName || file.doc_name || file.docName || ''
  })).filter(ref => ref.title) : [];
  const now = Date.now();
  const stableFor = Math.max(0, now - (result.last_growth_ts || now));
  const referencesPending = references.length === 0 && (result.answer || '').length > 0 && stableFor < __REFERENCE_GRACE_MS__;

  return JSON.stringify({
    question: result.question || __QUESTION_JSON__,
    scope: result.scope || 'all_parsed_files',
    answer: result.answer || '',
    references,
    main_target: result.main_target || result.target || __TARGET_JSON__,
    is_partial: referencesPending,
    references_pending: referencesPending
  });
})()
EOF
)
RESULT_EXPR="${RESULT_EXPR//__QUESTION_JSON__/${QUESTION_JSON}}"
RESULT_EXPR="${RESULT_EXPR//__TARGET_JSON__/${TARGET_JSON}}"
RESULT_EXPR="${RESULT_EXPR//__REFERENCE_GRACE_MS__/${REFERENCE_GRACE_MS}}"
cdp_eval "$MAIN_TARGET" "$RESULT_EXPR"
