"""OpenAI-compatible market review semantic enricher.

Purpose: Fill market review summary and markdown narrative from deterministic
         review facts.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime
from typing import Any, Callable

from app.core.config import get_settings

JsonRequestFn = Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]]


def _default_request(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _strip_json_block(text: str) -> str:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    return candidate


def _json_safe(value: Any) -> Any:
    """Convert prompt payload values to JSON-safe primitives."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _build_prompt(review_row: dict[str, Any]) -> str:
    payload = {
        "trade_date": _json_safe(review_row.get("trade_date")),
        "regime": _json_safe(review_row.get("regime")),
        "position_guidance": _json_safe(review_row.get("position_guidance")),
        "main_themes": _json_safe(review_row.get("main_themes_json")),
        "emerging_themes": _json_safe(review_row.get("emerging_themes_json")),
        "fading_themes": _json_safe(review_row.get("fading_themes_json")),
        "market_emotion": _json_safe(review_row.get("market_emotion_json")),
        "themes": _json_safe(review_row.get("themes_json")),
        "trend_codes": _json_safe(review_row.get("trend_codes_json")),
        "report_markdown": _json_safe(review_row.get("report_markdown")),
    }
    return (
        "You are enriching an A-share daily market review.\n"
        "Return JSON only. Do not include markdown fences.\n"
        "Allowed fields: summary, report_markdown.\n"
        "summary should be concise Chinese text.\n"
        "report_markdown should be a polished Chinese markdown review.\n"
        "The markdown must include these sections in order:\n"
        "1. 市场情绪定位\n"
        "2. 主线与非主线\n"
        "3. 推演过程\n"
        "4. 题材逐项判断\n"
        "5. 核心股观察\n"
        "6. 交易结论\n"
        "推演过程必须写出简要思考过程，明确说明你是如何从市场情绪、题材阶段、核心股承接、风险信号推导出结论的。\n"
        "不要省略推演过程，不要只给最终结论。\n"
        "The review must reflect market emotion, theme stage, risk signals, and actionable trading judgment.\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def create_market_review_semantic_enricher(
    *,
    request_fn: JsonRequestFn | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an OpenAI-compatible market review enricher from settings."""
    settings = get_settings()
    if not settings.openai_base_url or not settings.openai_model:
        raise ValueError("Market review enrichment requires OPENAI_BASE_URL and OPENAI_MODEL")

    effective_request = request_fn or _default_request
    api_url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if settings.openai_api_key:
        headers["Authorization"] = f"Bearer {settings.openai_api_key}"

    def enrich(review_row: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": settings.openai_model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "Return strict JSON for market review semantic enrichment.",
                },
                {
                    "role": "user",
                    "content": _build_prompt(review_row),
                },
            ],
        }
        response = effective_request(api_url, payload, headers)
        choices = response.get("choices") if isinstance(response, dict) else None
        if not isinstance(choices, list) or not choices:
            return review_row
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            return review_row
        try:
            parsed = json.loads(_strip_json_block(content))
        except json.JSONDecodeError:
            return review_row
        if isinstance(parsed, dict):
            if isinstance(parsed.get("summary"), str):
                review_row["summary"] = parsed["summary"].strip() or None
            if isinstance(parsed.get("report_markdown"), str):
                review_row["report_markdown"] = parsed["report_markdown"].strip() or review_row.get("report_markdown", "")
        return review_row

    return enrich
