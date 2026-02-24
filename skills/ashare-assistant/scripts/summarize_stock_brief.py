#!/usr/bin/env python3
"""
个股 deep research 摘要生成器（可选离线工具）。

两种运行模式：

1. --compact-only（Skill 主流程使用）
   仅做规则提取，输出 compact JSON（约 600 tokens），
   不调用任何 LLM API。输出供主 LLM 读取后自行生成 brief。

2. 完整模式（离线/批处理）
   调用 litellm gateway 直接生成 brief JSON。
   若 gateway 不可达，降级为关键词规则抽取。

用法：
    # Skill 主流程（输出 compact，由主 LLM 生成 brief）
    python3 summarize_stock_brief.py \
        --code 002050 \
        --em-raw ~/.ashare-assistant/data/DATE/dr_002050_em.json \
        --tgb-raw ~/.ashare-assistant/data/DATE/dr_002050_tgb.json \
        --output ~/.ashare-assistant/data/DATE/dr_002050_compact.json \
        --compact-only

    # 离线完整模式（直接生成 brief）
    python3 summarize_stock_brief.py \
        --code 002050 \
        --em-raw ~/.ashare-assistant/data/DATE/dr_002050_em.json \
        --tgb-raw ~/.ashare-assistant/data/DATE/dr_002050_tgb.json \
        --output ~/.ashare-assistant/data/DATE/dr_002050_brief.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

def _load_litellm_config() -> tuple[str, str, str]:
    """返回 (base_url, api_key, model_id)。"""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = json.load(f)
            litellm = cfg.get("models", {}).get("providers", {}).get("litellm", {})
            base_url = litellm.get("baseUrl", "http://127.0.0.1:4000")
            api_key = litellm.get("apiKey", "")
            models = litellm.get("models", [])
            # 选第一个非 free-pool 的模型，否则取第一个
            model_id = next(
                (m["id"] for m in models if m.get("id") != "free-pool"),
                models[0]["id"] if models else "gpt-3.5-turbo",
            )
            return base_url, api_key, model_id
        except Exception:
            pass
    # 环境变量兜底
    base_url = os.environ.get("LITELLM_BASE_URL", "http://127.0.0.1:4000")
    api_key = os.environ.get("LITELLM_API_KEY", "")
    model_id = os.environ.get("LITELLM_MODEL", "gpt-3.5-turbo")
    return base_url, api_key, model_id


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _hours_ago(time_str: str, now: datetime) -> int | None:
    """将时间字符串转换为距现在的小时数（整数，向上取整）。

    支持格式：
    - "2026-02-19 15:55:50"
    - "2026-02-19 15:55"
    - "02-19 03:41"  (MM-DD HH:MM，推断年份)
    - ISO 8601 带时区
    """
    if not time_str:
        return None

    s = time_str.strip()

    # 标准格式
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(s[:19], fmt[:len(s[:19])])
            return max(0, int((now - dt).total_seconds() / 3600) + 1)
        except ValueError:
            continue

    # ISO 8601 带时区（去掉 tzinfo 再算）
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(s[:25], fmt)
            dt_naive = dt.replace(tzinfo=None)
            return max(0, int((now - dt_naive).total_seconds() / 3600) + 1)
        except ValueError:
            continue

    # "MM-DD HH:MM" 格式（推断年份）
    if len(s) >= 11 and s[2] == "-" and s[5] == " ":
        try:
            month = int(s[0:2])
            day = int(s[3:5])
            hour = int(s[6:8])
            minute = int(s[9:11])
            dt = datetime(now.year, month, day, hour, minute)
            # 若推断结果在未来，视为上一年
            if dt > now:
                dt = datetime(now.year - 1, month, day, hour, minute)
            return max(0, int((now - dt).total_seconds() / 3600) + 1)
        except (ValueError, IndexError):
            pass

    return None


def _tier_for_source(source_type: str) -> str:
    tier_map = {
        "announcement": "A",
        "stock_info": "B",
        "eastmoney_guba": "C",
        "taoguba": "C",
    }
    return tier_map.get(source_type, "C")


# ---------------------------------------------------------------------------
# 输入数据精简（控制传给 LLM 的 token 量）
# ---------------------------------------------------------------------------

def _build_compact_input(em: dict, tgb: dict, now: datetime) -> dict:
    """从原始 JSON 中提取关键字段，压缩后传给 LLM。"""
    compact: dict[str, Any] = {}

    # --- 东方财富：公告（tier A）---
    notices = em.get("stock_notices_recent", [])
    compact["announcements"] = [
        {
            "title": n.get("title", ""),
            "pub_time": n.get("pub_datetime") or n.get("pub_time", ""),
            "hours_ago": _hours_ago(n.get("pub_datetime") or n.get("pub_time", ""), now),
            "url": n.get("url", ""),
        }
        for n in notices[:10]
    ]

    # --- 东方财富：资讯（tier B）---
    infos = em.get("stock_infos", [])
    compact["news_infos"] = [
        {
            "title": n.get("title", ""),
            "pub_time": n.get("pub_time", ""),
            "hours_ago": _hours_ago(n.get("pub_time", ""), now),
            "url": n.get("url", ""),
        }
        for n in infos[:5]
    ]

    # --- 东方财富：帖子正文（tier C，截取前 300 字）---
    details = em.get("latest_post_details", [])
    compact["guba_posts"] = [
        {
            "title": d.get("post_title", ""),
            "abstract": (d.get("post_content_text") or d.get("post_abstract") or "")[:300],
            "pub_time": d.get("post_publish_time", ""),
            "hours_ago": _hours_ago(d.get("post_publish_time", ""), now),
            "url": d.get("url", ""),
        }
        for d in details[:5]
        if not d.get("error")
    ]

    # --- 淘股吧：题材标签 ---
    tags = tgb.get("stock_tags", [])
    compact["stock_tags"] = [t.get("gn_name", "") for t in tags if t.get("gn_name")]

    # --- 淘股吧：个股讨论（tier C）---
    qposts = tgb.get("quotes_posts", [])
    compact["taoguba_posts"] = [
        {
            "subject": p.get("subject", ""),
            "summary": (p.get("summary") or "")[:200],
            "post_time": p.get("post_time", ""),
            "hours_ago": _hours_ago(p.get("post_time", ""), now),
            "url": p.get("url", ""),
        }
        for p in qposts[:8]
    ]

    return compact


# ---------------------------------------------------------------------------
# LLM 调用
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是一个A股个股情报分析助手。根据给定的个股相关数据，生成一份结构化的情报摘要（brief）。

输出必须是合法的 JSON，格式如下：
{
  "positive_signals": [
    {"summary": "简洁描述（20字内）", "source_url": "...", "source_type": "announcement|stock_info|eastmoney_guba|taoguba", "evidence_tier": "A|B|C", "hours_ago": 数字或null}
  ],
  "negative_signals": [...同上格式...],
  "uncertain_claims": [...同上格式...],
  "stock_tags": ["题材1", "题材2"],
  "community_heat": "high|medium|low"
}

分类规则：
- positive_signals：明确利好（增持/回购/中标/业绩超预期/题材催化）
- negative_signals：明确利空（减持/亏损/诉讼/解禁/监管处罚）
- uncertain_claims：无一手来源的传言/推测/模糊情绪
- evidence_tier：A=公告监管（announcements），B=资讯媒体（news_infos），C=社区帖子（guba_posts/taoguba_posts）
- hours_ago：直接从输入数据中对应条目的 hours_ago 字段复制，不要自行计算；若无则填 null
- community_heat：high=帖子数量多且互动活跃，low=帖子少或无讨论，medium=一般

重要约束：
- 每类最多 5 条，优先选信息量大的
- 没有足够信息时返回空数组 []
- community_heat 根据帖子数量和互动量综合判断
- 只输出 JSON，不要其他文字
"""


def _call_llm(compact_input: dict, code: str, base_url: str, api_key: str, model_id: str) -> dict | None:
    """调用 LLM，返回解析后的 brief dict，失败返回 None。"""
    user_content = f"股票代码：{code}\n\n数据：\n{json.dumps(compact_input, ensure_ascii=False)}"

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 1200,
        "temperature": 0.1,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    try:
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        content = body["choices"][0]["message"]["content"].strip()

        # 提取 JSON（LLM 有时会用 ```json ... ``` 包裹）
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        result = json.loads(content)
        if not isinstance(result, dict):
            print(f"[warn] LLM 返回类型异常: {type(result).__name__}", file=sys.stderr)
            return None
        return result

    except (urllib.error.URLError, OSError) as e:
        print(f"[warn] LLM API 不可达: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[warn] LLM 调用失败: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# 规则降级抽取
# ---------------------------------------------------------------------------

def _fallback_brief(compact: dict, code: str, now: datetime) -> dict:
    """规则降级：取公告标题为 positive/negative，帖子主题为 uncertain_claims。"""
    positive: list[dict] = []
    negative: list[dict] = []
    uncertain: list[dict] = []

    # 负向关键词
    neg_kws = {"减持", "亏损", "诉讼", "处罚", "终止", "违规", "跌停", "解禁", "问询", "立案"}
    pos_kws = {"增持", "回购", "中标", "分红", "并购", "涨停", "业绩", "签约", "获批", "战略"}

    def _is_negative(text: str) -> bool:
        return any(kw in text for kw in neg_kws)

    def _is_positive(text: str) -> bool:
        return any(kw in text for kw in pos_kws)

    # 公告（tier A）
    for ann in compact.get("announcements", []):
        title = ann.get("title", "")
        if not title:
            continue
        ha = _hours_ago(ann.get("pub_time", ""), now)
        item = {
            "summary": title[:60],
            "source_url": ann.get("url", ""),
            "source_type": "announcement",
            "evidence_tier": "A",
            "hours_ago": ha,
        }
        if _is_negative(title):
            negative.append(item)
        else:
            positive.append(item)

    # 资讯（tier B）
    for info in compact.get("news_infos", []):
        title = info.get("title", "")
        if not title:
            continue
        ha = _hours_ago(info.get("pub_time", ""), now)
        item = {
            "summary": title[:60],
            "source_url": info.get("url", ""),
            "source_type": "stock_info",
            "evidence_tier": "B",
            "hours_ago": ha,
        }
        if _is_negative(title):
            negative.append(item)
        elif _is_positive(title):
            positive.append(item)
        else:
            uncertain.append(item)

    # 股吧帖子（tier C）→ uncertain
    for post in compact.get("guba_posts", [])[:3]:
        title = post.get("title", "")
        if not title:
            continue
        ha = _hours_ago(post.get("pub_time", ""), now)
        uncertain.append({
            "summary": title[:60],
            "source_url": post.get("url", ""),
            "source_type": "eastmoney_guba",
            "evidence_tier": "C",
            "hours_ago": ha,
        })

    # 淘股吧帖子（tier C）→ uncertain
    for post in compact.get("taoguba_posts", [])[:3]:
        subject = post.get("subject", "")
        if not subject:
            continue
        ha = _hours_ago(post.get("post_time", ""), now)
        uncertain.append({
            "summary": subject[:60],
            "source_url": post.get("url", ""),
            "source_type": "taoguba",
            "evidence_tier": "C",
            "hours_ago": ha,
        })

    # 社区热度（帖子总数粗估）
    total_posts = len(compact.get("guba_posts", [])) + len(compact.get("taoguba_posts", []))
    community_heat = "high" if total_posts >= 10 else ("medium" if total_posts >= 4 else "low")

    return {
        "positive_signals": positive[:5],
        "negative_signals": negative[:5],
        "uncertain_claims": uncertain[:5],
        "stock_tags": compact.get("stock_tags", []),
        "community_heat": community_heat,
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def extract_compact(code: str, em_raw_path: str, tgb_raw_path: str, output_path: str) -> None:
    """仅做规则提取，输出 compact JSON，供主 LLM 生成 brief 使用。"""
    now = datetime.now()
    em: dict = {}
    tgb: dict = {}

    if em_raw_path and os.path.exists(em_raw_path):
        with open(em_raw_path, encoding="utf-8") as f:
            em = json.load(f)
    else:
        print(f"[warn] 东方财富原始文件不存在: {em_raw_path}", file=sys.stderr)

    if tgb_raw_path and os.path.exists(tgb_raw_path):
        with open(tgb_raw_path, encoding="utf-8") as f:
            tgb = json.load(f)
    else:
        print(f"[warn] 淘股吧原始文件不存在: {tgb_raw_path}", file=sys.stderr)

    compact = _build_compact_input(em, tgb, now)
    compact["code"] = code
    compact["extracted_at"] = now.strftime("%Y-%m-%d %H:%M:%S")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(compact, f, ensure_ascii=False, indent=2)

    size = len(json.dumps(compact, ensure_ascii=False))
    print(json.dumps({
        "code": code,
        "mode": "compact",
        "chars": size,
        "est_tokens": size // 4,
        "announcements": len(compact.get("announcements", [])),
        "news_infos": len(compact.get("news_infos", [])),
        "guba_posts": len(compact.get("guba_posts", [])),
        "taoguba_posts": len(compact.get("taoguba_posts", [])),
        "stock_tags": len(compact.get("stock_tags", [])),
    }, ensure_ascii=False))


def summarize(code: str, em_raw_path: str, tgb_raw_path: str, output_path: str) -> None:
    """完整模式：调用 litellm 生成 brief，不可达时降级为规则抽取。"""
    now = datetime.now()
    em: dict = {}
    tgb: dict = {}

    if em_raw_path and os.path.exists(em_raw_path):
        with open(em_raw_path, encoding="utf-8") as f:
            em = json.load(f)
    else:
        print(f"[warn] 东方财富原始文件不存在: {em_raw_path}", file=sys.stderr)

    if tgb_raw_path and os.path.exists(tgb_raw_path):
        with open(tgb_raw_path, encoding="utf-8") as f:
            tgb = json.load(f)
    else:
        print(f"[warn] 淘股吧原始文件不存在: {tgb_raw_path}", file=sys.stderr)

    compact = _build_compact_input(em, tgb, now)

    base_url, api_key, model_id = _load_litellm_config()
    brief = _call_llm(compact, code, base_url, api_key, model_id)

    if brief is None:
        print("[info] 降级为规则抽取", file=sys.stderr)
        brief = _fallback_brief(compact, code, now)
        brief["_source"] = "fallback"
    else:
        brief["_source"] = "llm"
        if "stock_tags" not in brief:
            brief["stock_tags"] = compact.get("stock_tags", [])

    brief["code"] = code
    brief["summarized_at"] = now.strftime("%Y-%m-%d %H:%M:%S")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "code": code,
        "mode": "full",
        "positive": len(brief.get("positive_signals", [])),
        "negative": len(brief.get("negative_signals", [])),
        "uncertain": len(brief.get("uncertain_claims", [])),
        "tags": brief.get("stock_tags", [])[:5],
        "heat": brief.get("community_heat"),
        "source": brief.get("_source"),
    }, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="个股 deep research 摘要生成器")
    parser.add_argument("--code", required=True, help="股票代码，如 002050")
    parser.add_argument("--em-raw", default="", help="东方财富原始 JSON 路径")
    parser.add_argument("--tgb-raw", default="", help="淘股吧原始 JSON 路径")
    parser.add_argument("--output", required=True, help="输出 JSON 路径")
    parser.add_argument(
        "--compact-only",
        action="store_true",
        help="仅输出 compact JSON（规则提取，不调用 LLM），供主 LLM 生成 brief",
    )
    args = parser.parse_args()

    if args.compact_only:
        extract_compact(args.code, args.em_raw, args.tgb_raw, args.output)
    else:
        summarize(args.code, args.em_raw, args.tgb_raw, args.output)


if __name__ == "__main__":
    main()
