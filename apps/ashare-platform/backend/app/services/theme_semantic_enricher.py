"""OpenAI-compatible theme semantic enricher.

Purpose: Fill semantic-only theme fields from an LLM without touching
         deterministic facts.
"""

from __future__ import annotations

import json
import urllib.request
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


def _build_prompt(theme_row: dict[str, Any], stock_rows: list[dict[str, Any]]) -> str:
    payload = {
        "theme": {
            "theme_name": theme_row.get("theme_name"),
            "theme_strength": theme_row.get("theme_strength"),
            "theme_score": theme_row.get("theme_score"),
            "trend_stock_count": theme_row.get("trend_stock_count"),
            "core_trend_stock_count": theme_row.get("core_trend_stock_count"),
            "evidence_json": theme_row.get("evidence_json"),
        },
        "market_emotion": theme_row.get("market_emotion_json"),
        "theme_emotion": theme_row.get("theme_emotion_json"),
        "stocks": [
            {
                "code": row.get("code"),
                "name": row.get("name"),
                "role": row.get("role"),
                "is_core": row.get("is_core"),
                "rank_in_theme": row.get("rank_in_theme"),
                "trend_score": row.get("trend_score"),
                "star_rating": row.get("star_rating"),
                "emotion_level": row.get("emotion_level"),
            }
            for row in stock_rows
        ],
    }
    return (
        "You are enriching A-share theme semantics.\n"
        "Return JSON only. Do not include markdown.\n"
        "Allowed theme fields: market_attitude, theme_stage, summary.\n"
        "Allowed stock fields: stock_comments as a mapping from code to short comment.\n"
        "theme_stage must be one of: early, middle, late, unknown.\n"
        "market_attitude should be one short phrase in Chinese.\n"
        "summary should be concise Chinese text and include a brief reasoning summary.\n"
        "请在 summary 中简要说明判断过程，至少点出市场情绪、题材阶段证据、核心股承接或风险信号中的两项依据。\n"
        "识别末端风险优先于判断中段回调机会。\n"
        "如果高位风险、炸板率、跌停压力、题材恶性分歧明显上升，应优先判断为 late。\n"
        "如果市场转弱但题材核心承接稳定、并非恶性分歧，可保留为 middle。\n"
        "只有在核心股承接稳定、情绪分歧可修复时，才能判断为 middle。\n"
        "当 theme_cycle_hint 显示 main_rise 或 healthy_divergence，且 leader_board_max/leader_continuity_score 仍强时，不要轻易判 late。\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def create_theme_semantic_enricher(
    *,
    request_fn: JsonRequestFn | None = None,
) -> Callable[[dict[str, Any], list[dict[str, Any]]], tuple[dict[str, Any], list[dict[str, Any]]]]:
    """Create an OpenAI-compatible theme semantic enricher from settings."""
    settings = get_settings()
    if not settings.openai_base_url or not settings.openai_model:
        raise ValueError("Theme semantic enrichment requires OPENAI_BASE_URL and OPENAI_MODEL")

    effective_request = request_fn or _default_request
    api_url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if settings.openai_api_key:
        headers["Authorization"] = f"Bearer {settings.openai_api_key}"

    def enrich(theme_row: dict[str, Any], stock_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        payload = {
            "model": settings.openai_model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "Return strict JSON for theme semantic enrichment.",
                },
                {
                    "role": "user",
                    "content": _build_prompt(theme_row, stock_rows),
                },
            ],
        }
        response = effective_request(api_url, payload, headers)
        choices = response.get("choices") if isinstance(response, dict) else None
        if not isinstance(choices, list) or not choices:
            return theme_row, stock_rows
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            return theme_row, stock_rows
        try:
            parsed = json.loads(_strip_json_block(content))
        except json.JSONDecodeError:
            return theme_row, stock_rows

        if isinstance(parsed, dict):
            theme_payload = parsed.get("theme") if isinstance(parsed.get("theme"), dict) else parsed
            if isinstance(theme_payload.get("market_attitude"), str):
                theme_row["market_attitude"] = theme_payload["market_attitude"].strip() or None
            if theme_payload.get("theme_stage") in {"early", "middle", "late", "unknown"}:
                theme_row["theme_stage"] = theme_payload["theme_stage"]
            if isinstance(theme_payload.get("summary"), str):
                theme_row["summary"] = theme_payload["summary"].strip() or None
            stock_comments = parsed.get("stock_comments")
            if isinstance(stock_comments, dict):
                comment_map = {
                    str(code): str(comment).strip()
                    for code, comment in stock_comments.items()
                    if str(comment).strip()
                }
                for row in stock_rows:
                    code = str(row.get("code", ""))
                    if code in comment_map:
                        row["comment"] = comment_map[code]
        return theme_row, stock_rows

    return enrich
