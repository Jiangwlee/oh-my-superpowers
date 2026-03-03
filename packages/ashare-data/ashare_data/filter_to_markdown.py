#!/usr/bin/env python3
"""将 raw/ 下的 JSON 数据转换为 filtered/ 下的 Markdown 文件。

纯规则转换，不调用 LLM。转换原则：
  - 去除 JSON 结构开销（{}, [], 引号, 键名等）
  - 保留完整正文，不截断
  - 丢弃空值字段（emotion=null, summary=""）
  - 输出合法的 Markdown 语法

用法:
    python3 scripts/filter_to_markdown.py \
        --input-dir ~/.ashare-assistant/data/2026-02-24/raw \
        --output-dir ~/.ashare-assistant/data/2026-02-24/filtered
"""

import argparse
import json
import logging
import os
import sys
from collections.abc import Callable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── 通用工具 ──────────────────────────────────────────


def _load_json(filepath: str) -> list | dict | None:
    """加载 JSON 文件，失败返回 None。"""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("加载 %s 失败: %s", filepath, e)
        return None


def _file_size_kb(filepath: str) -> float:
    """返回文件大小（KB），不存在返回 0。"""
    try:
        return os.path.getsize(filepath) / 1024
    except OSError:
        return 0.0


def _escape_md(text: str) -> str:
    """对 Markdown 表格单元格中的特殊字符转义。"""
    return text.replace("|", "\\|").replace("\n", " ")


def _yuan_to_yi(value: float | int) -> str:
    """将元转换为亿元，保留2位小数。"""
    return f"{value / 1e8:.2f}"


def _filter_recent_24h(data: list, hours: int = 24) -> list:
    """过滤新闻列表，只保留最近 N 小时内的条目。

    使用 makeDate 字段（格式: 'YYYY-MM-DD HH:MM:SS'）做比对。
    解析失败的条目视为有效（宽容策略，防止数据格式变化导致全量丢弃）。
    全部过期时返回列表中的第一条（最新一条）作为兜底。

    Args:
        data: 新闻条目列表，每项含 makeDate 字段。
        hours: 时间窗口（小时），默认 24。

    Returns:
        过滤后的列表，至少包含 1 条（若原列表非空）。
    """
    if not data:
        return []
    cutoff = datetime.now() - timedelta(hours=hours)
    result = []
    for item in data:
        raw_date = str(item.get("makeDate") or "").strip()
        if not raw_date:
            result.append(item)
            continue
        try:
            item_time = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            result.append(item)  # 格式异常，宽容保留
            continue
        if item_time >= cutoff:
            result.append(item)
    # 兜底：全部过滤掉时返回第一条（最新一条）
    return result if result else [data[0]]


# ── 新闻类转换 ────────────────────────────────────────


def _convert_news(data: list, category: str) -> str:
    """将新闻 JSON 数组转为 Markdown。

    每条新闻保留 title、makeDate、detail（完整正文）。
    丢弃 emotion（始终为 null）和 summary（始终为空）。
    数据在渲染前会经过 _filter_recent_24h() 过滤，只保留最近 24 小时内的条目。

    Args:
        data: 新闻条目列表。
        category: 新闻类别名（如"A股头条"）。

    Returns:
        Markdown 格式文本。
    """
    lines = [f"# {category}", ""]
    data = _filter_recent_24h(data)

    for i, item in enumerate(data, 1):
        title = item.get("title", "").strip()
        date = item.get("makeDate", "").strip()
        detail = item.get("detail", "").strip()

        # 跳过无内容条目
        if not title and not detail:
            continue

        if title:
            lines.append(f"## {i}. {title}")
        else:
            # news_flash 可能没有 title
            lines.append(f"## {i}. （快讯）")

        if date:
            lines.append(f"\n**时间**: {date}")

        if detail:
            lines.append(f"\n{detail}")

        lines.append("")  # 条目间空行

    return "\n".join(lines)


def convert_news_headline(raw_dir: str) -> tuple[str, str]:
    """转换 A股头条。"""
    data = _load_json(os.path.join(raw_dir, "news_headline.json"))
    if not data or not isinstance(data, list):
        return "", "news_headline.md"
    return _convert_news(data, "A股头条"), "news_headline.md"


def convert_news_daily(raw_dir: str) -> tuple[str, str]:
    """转换每日财经。"""
    data = _load_json(os.path.join(raw_dir, "news_daily.json"))
    if not data or not isinstance(data, list):
        return "", "news_daily.md"
    return _convert_news(data, "每日财经"), "news_daily.md"


def convert_news_opportunity(raw_dir: str) -> tuple[str, str]:
    """转换机会情报。"""
    data = _load_json(os.path.join(raw_dir, "news_opportunity.json"))
    if not data or not isinstance(data, list):
        return "", "news_opportunity.md"
    return _convert_news(data, "机会情报"), "news_opportunity.md"


def convert_news_realtime(raw_dir: str) -> tuple[str, str]:
    """转换市况直击。"""
    data = _load_json(os.path.join(raw_dir, "news_realtime.json"))
    if not data or not isinstance(data, list):
        return "", "news_realtime.md"
    return _convert_news(data, "市况直击"), "news_realtime.md"


def convert_news_flash(raw_dir: str) -> tuple[str, str]:
    """转换 7x24 快讯。

    快讯通常较短，使用紧凑的列表格式。
    """
    data = _load_json(os.path.join(raw_dir, "news_flash.json"))
    if not data or not isinstance(data, list):
        return "", "news_flash.md"

    lines = ["# 7x24 快讯", ""]
    data = _filter_recent_24h(data)

    for item in data:
        title = item.get("title", "").strip()
        date = item.get("makeDate", "").strip()
        detail = item.get("detail", "").strip()

        # 提取时间部分（HH:mm）
        time_str = ""
        if date:
            parts = date.split(" ")
            time_str = parts[-1][:5] if len(parts) > 1 else date

        content = title if title else detail
        if not content:
            continue

        if time_str:
            lines.append(f"- **{time_str}** {content}")
        else:
            lines.append(f"- {content}")

        # 如果 title 和 detail 都有且不同，补充 detail
        if title and detail and detail != title:
            lines.append(f"  {detail}")

    lines.append("")
    return "\n".join(lines), "news_flash.md"


# ── 淘股吧类转换 ──────────────────────────────────────


def convert_taoguba_recommend(raw_dir: str) -> tuple[str, str]:
    """转换淘股吧今日推荐。

    保留：subject, content（完整正文）, author, date, view_count, reply_count
    丢弃：subinfo（正文截断预览，冗余）, url, stock_codes（始终为空）
    """
    data = _load_json(os.path.join(raw_dir, "taoguba_recommend.json"))
    if not data or not isinstance(data, list):
        return "", "taoguba_recommend.md"

    lines = ["# 淘股吧今日推荐", ""]

    for i, item in enumerate(data, 1):
        subject = item.get("subject", "").strip()
        content = item.get("content", "").strip()
        author = item.get("author", "").strip()
        date = item.get("date", "").strip()
        view_count = item.get("view_count", 0)
        reply_count = item.get("reply_count", 0)

        if not subject and not content:
            continue

        lines.append(f"## {i}. {subject or '（无标题）'}")

        meta_parts = []
        if author:
            meta_parts.append(f"作者: {author}")
        if date:
            meta_parts.append(f"时间: {date}")
        if view_count:
            meta_parts.append(f"浏览: {view_count}")
        if reply_count:
            meta_parts.append(f"回复: {reply_count}")
        if meta_parts:
            lines.append(f"\n*{' | '.join(meta_parts)}*")

        if content:
            lines.append(f"\n{content}")

        lines.append("")

    return "\n".join(lines), "taoguba_recommend.md"


def convert_taoguba_hot_discussion(raw_dir: str) -> tuple[str, str]:
    """转换淘股吧热门讨论。

    保留：subject, body（完整正文）, quotecontent（引用内容）, author
    丢弃：date（始终为空）, view_count/reply_count（始终为0）, url, stock_codes
    """
    data = _load_json(os.path.join(raw_dir, "taoguba_hot_discussion.json"))
    if not data or not isinstance(data, list):
        return "", "taoguba_hot_discussion.md"

    lines = ["# 淘股吧热门讨论", ""]

    for i, item in enumerate(data, 1):
        subject = item.get("subject", "").strip()
        body = item.get("body", "").strip()
        quotecontent = item.get("quotecontent", "").strip()
        author = item.get("author", "").strip()

        if not subject and not body:
            continue

        lines.append(f"## {i}. {subject or '（无标题）'}")

        if author:
            lines.append(f"\n*作者: {author}*")

        if quotecontent:
            # 引用内容用 Markdown 引用块
            quoted_lines = quotecontent.split("\n")
            lines.append("")
            for ql in quoted_lines:
                lines.append(f"> {ql}")
            lines.append("")

        if body:
            lines.append(f"\n{body}")

        lines.append("")

    return "\n".join(lines), "taoguba_hot_discussion.md"


def convert_taoguba_hot(raw_dir: str) -> tuple[str, str]:
    """转换淘股吧精华帖。

    保留：title, content（完整正文）, author, date, view_count, reply_count
    丢弃：url
    """
    data = _load_json(os.path.join(raw_dir, "taoguba_hot.json"))
    if not data or not isinstance(data, list):
        return "", "taoguba_hot.md"

    lines = ["# 淘股吧精华帖", ""]

    for i, item in enumerate(data, 1):
        title = item.get("title", "").strip()
        content = item.get("content", "").strip()
        author = item.get("author", "").strip()
        date = item.get("date", "").strip()
        view_count = item.get("view_count", 0)
        reply_count = item.get("reply_count", 0)

        if not title and not content:
            continue

        lines.append(f"## {i}. {title or '（无标题）'}")

        meta_parts = []
        if author:
            meta_parts.append(f"作者: {author}")
        if date:
            meta_parts.append(f"时间: {date}")
        if view_count:
            meta_parts.append(f"浏览: {view_count}")
        if reply_count:
            meta_parts.append(f"回复: {reply_count}")
        if meta_parts:
            lines.append(f"\n*{' | '.join(meta_parts)}*")

        if content:
            lines.append(f"\n{content}")

        lines.append("")

    return "\n".join(lines), "taoguba_hot.md"


# ── 结构化市场数据转换 ────────────────────────────────


def convert_market_sectors(raw_dir: str) -> tuple[str, str]:
    """转换板块资金流向。"""
    data = _load_json(os.path.join(raw_dir, "market_sectors.json"))
    if not data or not isinstance(data, dict):
        return "", "market_sectors.md"

    trade_date = data.get("trade_date", "")
    sector_count = data.get("sector_count", "")

    lines = [f"# 板块资金流向", ""]
    if trade_date:
        lines.append(f"**交易日**: {trade_date}  **板块总数**: {sector_count}")
        lines.append("")

    for direction, label in [("top_inflow", "净流入"), ("top_outflow", "净流出")]:
        sectors = data.get(direction, [])
        if not sectors:
            continue

        lines.append(f"## {label} TOP{len(sectors)} 板块")
        lines.append("")
        lines.append("| 排名 | 板块 | 净流入(亿) | 个股数 |")
        lines.append("|------|------|-----------|--------|")

        for idx, sector in enumerate(sectors, 1):
            name = sector.get("name", "")
            netin = _yuan_to_yi(sector.get("total_netin", 0))
            count = sector.get("stock_count", "")
            lines.append(f"| {idx} | {name} | {netin} | {count} |")

        lines.append("")

        # 每个板块的个股明细
        for sector in sectors:
            name = sector.get("name", "")
            inflow_stocks = sector.get("top_inflow_stocks", [])
            outflow_stocks = sector.get("top_outflow_stocks", [])

            if inflow_stocks or outflow_stocks:
                lines.append(f"**{name}**:")
                if inflow_stocks:
                    inflow_items = [
                        f"{s['name']}({_yuan_to_yi(s['netin'])}亿)"
                        for s in inflow_stocks
                    ]
                    lines.append(f"  流入: {', '.join(inflow_items)}")
                if outflow_stocks:
                    outflow_items = [
                        f"{s['name']}({_yuan_to_yi(s['netin'])}亿)"
                        for s in outflow_stocks
                    ]
                    lines.append(f"  流出: {', '.join(outflow_items)}")
                lines.append("")

    return "\n".join(lines), "market_sectors.md"


def convert_funding(raw_dir: str) -> tuple[str, str]:
    """转换资金面数据。"""
    data = _load_json(os.path.join(raw_dir, "funding.json"))
    if not data or not isinstance(data, dict):
        return "", "funding.md"

    lines = ["# 资金面", ""]

    # 北向资金
    nb = data.get("northbound_net")
    indicator = data.get("funding_indicator", "")
    if nb is not None:
        lines.append(f"**北向资金净流入**: {nb}亿元")
        if indicator:
            lines.append(f"**统计周期**: {indicator}")
        lines.append("")

    # 主力净流入 Top20（3日累计）
    top20 = data.get("main_force_top20", [])
    if top20:
        lines.append("## 主力净流入 TOP20（3日累计）")
        lines.append("")
        lines.append("| 排名 | 股票 | 代码 | 净流入(亿) |")
        lines.append("|------|------|------|-----------|")
        for idx, item in enumerate(top20, 1):
            name = item.get("name", "")
            code = item.get("code", "")
            net = item.get("net_inflow", 0)
            lines.append(f"| {idx} | {name} | {code} | {net:.2f} |")
        lines.append("")

    # 今日 Top10
    today = data.get("today_top10", [])
    if today:
        lines.append("## 今日主力净流入 TOP10")
        lines.append("")
        lines.append("| 排名 | 股票 | 代码 | 净流入(亿) |")
        lines.append("|------|------|------|-----------|")
        for idx, item in enumerate(today, 1):
            name = item.get("name", "")
            code = item.get("code", "")
            net = item.get("net_inflow", 0)
            lines.append(f"| {idx} | {name} | {code} | {net:.2f} |")
        lines.append("")

    # 趋势候选股资金
    trend = data.get("trend_candidates_funding", [])
    if trend:
        lines.append("## 趋势候选股主力资金")
        lines.append("")
        lines.append("| 排名 | 股票 | 代码 | 净流入(亿) |")
        lines.append("|------|------|------|-----------|")
        for idx, item in enumerate(trend, 1):
            name = item.get("name", "")
            code = item.get("code", "")
            net = item.get("net_inflow", 0)
            lines.append(f"| {idx} | {name} | {code} | {net:.2f} |")
        lines.append("")

    return "\n".join(lines), "funding.md"


def convert_us_market(raw_dir: str) -> tuple[str, str]:
    """转换美股行情。"""
    data = _load_json(os.path.join(raw_dir, "us_market.json"))
    if not data or not isinstance(data, dict):
        return "", "us_market.md"

    status = data.get("market_status", "")
    if status == "unavailable":
        return "# 美股行情\n\n*数据不可用*\n", "us_market.md"

    fetched_at = data.get("fetched_at", "")
    lines = ["# 美股行情", ""]
    if fetched_at:
        lines.append(f"**采集时间**: {fetched_at}  **状态**: {status}")
        lines.append("")

    # 主要指数
    indices = data.get("indices", [])
    if indices:
        lines.append("## 主要指数")
        lines.append("")
        lines.append("| 指数 | 收盘价 | 涨跌幅 |")
        lines.append("|------|--------|--------|")
        for idx in indices:
            name = idx.get("name_cn", idx.get("ticker", ""))
            close = idx.get("close", "")
            pct = idx.get("change_pct", "")
            pct_str = f"{pct:+.2f}%" if isinstance(pct, (int, float)) else str(pct)
            lines.append(f"| {name} | {close} | {pct_str} |")
        lines.append("")

    # 科技股
    techs = data.get("tech_stocks", [])
    if techs:
        lines.append("## 科技股")
        lines.append("")
        lines.append("| 股票 | 收盘价 | 涨跌幅 | 关联A股板块 |")
        lines.append("|------|--------|--------|------------|")
        for t in techs:
            name = t.get("name_cn", t.get("ticker", ""))
            close = t.get("close", "")
            pct = t.get("change_pct", "")
            pct_str = f"{pct:+.2f}%" if isinstance(pct, (int, float)) else str(pct)
            sectors = t.get("a_share_sectors", [])
            sectors_str = ", ".join(sectors) if sectors else "-"
            lines.append(
                f"| {_escape_md(name)} | {close} | {pct_str} | {sectors_str} |"
            )
        lines.append("")

    return "\n".join(lines), "us_market.md"


# ── 小型元数据文件转换 ────────────────────────────────


def convert_collection_summary(raw_dir: str) -> tuple[str, str]:
    """转换采集摘要。"""
    data = _load_json(os.path.join(raw_dir, "collection_summary.json"))
    if not data or not isinstance(data, dict):
        return "", "collection_summary.md"

    lines = ["# 数据采集摘要", ""]

    as_of = data.get("as_of_date", "")
    run_id = data.get("run_id", "")
    ok = data.get("ok_count", 0)
    err = data.get("error_count", 0)
    elapsed = data.get("total_elapsed_sec", 0)
    sv = data.get("strategy_version", "")

    lines.append(f"- **日期**: {as_of}")
    lines.append(f"- **Run ID**: {run_id}")
    lines.append(f"- **策略版本**: {sv}")
    lines.append(f"- **成功/失败**: {ok}/{err}")
    lines.append(f"- **耗时**: {elapsed}s")
    lines.append("")

    sources = data.get("sources", {})
    if sources:
        lines.append("## 各数据源状态")
        lines.append("")
        lines.append("| 数据源 | 状态 | 条目数 | 耗时(s) | 错误 |")
        lines.append("|--------|------|--------|---------|------|")
        for name, info in sources.items():
            status = info.get("status", "")
            count = info.get("count", "-")
            elapsed_s = info.get("elapsed_sec", "")
            error = info.get("error", "") or ""
            lines.append(
                f"| {name} | {status} | {count} | {elapsed_s} | "
                f"{_escape_md(str(error)[:50])} |"
            )
        lines.append("")

    return "\n".join(lines), "collection_summary.md"


def convert_trade_date(raw_dir: str) -> tuple[str, str]:
    """转换交易日期（极小文件，直接内联到 index）。"""
    data = _load_json(os.path.join(raw_dir, "trade_date.json"))
    if not isinstance(data, dict):
        return "", "trade_date.md"
    td = data.get("trade_date", "")
    return f"# 最近交易日\n\n{td}\n", "trade_date.md"


def convert_run_id(raw_dir: str) -> tuple[str, str]:
    """转换运行标识。"""
    data = _load_json(os.path.join(raw_dir, "run_id.json"))
    if not isinstance(data, dict):
        return "", "run_id.md"
    lines = ["# 运行标识", ""]
    for k, v in data.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    return "\n".join(lines), "run_id.md"


def convert_broker_account(raw_dir: str) -> tuple[str, str]:
    """转换券商账户数据。

    字段对照（fetch_broker_account 实际输出）：
      total / usable / day_earn / hold_earn
      hold_list[].code, name, hold_vol, usable_vol, hold_earn, day_earn
      order_list[].code, name, type, status, deal_price, deal_volume
    """
    filepath = os.path.join(raw_dir, "broker_account.json")
    if not os.path.exists(filepath):
        return "", "broker_account.md"

    data = _load_json(filepath)
    if not data or not isinstance(data, dict):
        return "", "broker_account.md"

    lines = ["# 账户数据", ""]

    # 资金概况
    lines.append("## 资金概况")
    lines.append("")
    fund_keys = [
        ("total", "总资产"),
        ("usable", "可用资金"),
        ("day_earn", "当日盈亏"),
        ("hold_earn", "持仓盈亏"),
    ]
    for key, label in fund_keys:
        val = data.get(key)
        if val is not None:
            lines.append(
                f"- **{label}**: {float(val):,.2f}"
                if isinstance(val, (int, float, str)) and str(val).lstrip("-").replace(".", "", 1).isdigit()
                else f"- **{label}**: {val}"
            )
    lines.append("")

    # 持仓
    hold_list = data.get("hold_list", [])
    if hold_list:
        lines.append("## 当前持仓")
        lines.append("")
        lines.append("| 股票 | 代码 | 持仓量 | 可卖量 | 持仓盈亏 | 当日盈亏 |")
        lines.append("|------|------|--------|--------|----------|----------|")
        for p in hold_list:
            name = p.get("name", "")
            code = p.get("code", "")
            hold_vol = p.get("hold_vol", "")
            usable_vol = p.get("usable_vol", "")
            hold_earn = p.get("hold_earn", "")
            day_earn = p.get("day_earn", "")
            lines.append(f"| {name} | {code} | {hold_vol} | {usable_vol} | {hold_earn} | {day_earn} |")
        lines.append("")

    # 当日委托
    order_list = data.get("order_list", [])
    if order_list:
        lines.append("## 当日委托")
        lines.append("")
        lines.append("| 股票 | 代码 | 方向 | 成交价 | 成交量 | 状态 |")
        lines.append("|------|------|------|--------|--------|------|")
        for o in order_list:
            name = o.get("name", "")
            code = o.get("code", "")
            direction = o.get("type", "")
            price = o.get("deal_price", o.get("order_price", ""))
            qty = o.get("deal_volume", o.get("order_volume", ""))
            status = o.get("status", "")
            lines.append(f"| {name} | {code} | {direction} | {price} | {qty} | {status} |")
        lines.append("")

    return "\n".join(lines), "broker_account.md"


# ── 已有 Markdown 文件直接复制 ────────────────────────


def _copy_existing_md(raw_dir: str, filename: str) -> tuple[str, str]:
    """直接读取已存在的 Markdown 文件。"""
    filepath = os.path.join(raw_dir, filename)
    if not os.path.exists(filepath):
        return "", filename
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read(), filename
    except Exception as e:
        logger.warning("读取 %s 失败: %s", filepath, e)
        return "", filename


# ── 索引生成 ──────────────────────────────────────────


def generate_index(
    output_dir: str,
    raw_dir: str,
    results: list[tuple[str, str, float, str]],
    as_of_date: str,
) -> str:
    """生成 filtered/index.md 索引文件。

    Args:
        output_dir: filtered/ 目录路径。
        raw_dir: raw/ 目录路径。
        results: [(filename, category, size_kb, read_mode), ...]
            read_mode: "direct"(主 agent 直读) 或 "subagent"(子 agent 分析)
        as_of_date: 数据日期。

    Returns:
        索引文件内容。
    """
    lines = [f"# 数据索引 {as_of_date}", ""]
    lines.append("本目录包含经过格式转换的 Markdown 文件，是 LLM 的输入数据源。")
    lines.append("原始 JSON 数据存储在 `raw/` 目录中，用于审计和回溯。")
    lines.append("")
    lines.append("读取方式说明：")
    lines.append("- **direct**: 主 agent 直接读取")
    lines.append("- **subagent**: 由子 agent 进行语义分析后输出到 `report/`")
    lines.append("")

    # 按类别分组
    categories: dict[str, list[tuple[str, float, str]]] = {}
    for filename, category, size_kb, read_mode in results:
        if not filename:
            continue
        categories.setdefault(category, []).append((filename, size_kb, read_mode))

    total_size = 0.0
    total_files = 0

    for cat_name, files in categories.items():
        lines.append(f"## {cat_name}")
        lines.append("")
        lines.append("| 文件 | 大小(KB) | 读取方式 |")
        lines.append("|------|---------|---------|")
        for fname, size, mode in files:
            lines.append(f"| {fname} | {size:.1f} | {mode} |")
            total_size += size
            total_files += 1
        lines.append("")

    lines.append(f"---")
    lines.append(f"**总计**: {total_files} 个文件, {total_size:.1f} KB")

    # 对比原始数据大小
    raw_total = 0.0
    if os.path.exists(raw_dir):
        for f in os.listdir(raw_dir):
            raw_total += _file_size_kb(os.path.join(raw_dir, f))
    if raw_total > 0:
        ratio = total_size / raw_total * 100
        lines.append(f"**原始数据**: {raw_total:.1f} KB")
        lines.append(f"**压缩比**: {ratio:.1f}%")

    lines.append("")
    return "\n".join(lines)


def convert_watchlist_signals(raw_dir: str) -> tuple[str, str]:
    """转换 watchlist 状态机信号为 Markdown。"""
    filepath = os.path.expanduser("~/.ashare-assistant/signals/watchlist_signals.json")
    if not os.path.exists(filepath):
        return "", "watchlist_signals.md"

    data = _load_json(filepath)
    if not data or not isinstance(data, dict):
        return "", "watchlist_signals.md"
    signals = data.get("signals")
    exits = data.get("exits")
    if not isinstance(signals, list):
        return "", "watchlist_signals.md"
    if not isinstance(exits, list):
        exits = []

    lines = [
        "# Watchlist 状态机信号",
        "",
        f"- 扫描时间: {data.get('scanned_at', 'N/A')}",
        f"- 市场风险: {(data.get('market') or {}).get('danger_level', 'N/A')}",
        f"- 状态信号数: {len(signals)}",
        f"- 出场信号数: {len(exits)}",
        "",
        "## 状态信号",
        "",
        "| 股票 | 代码 | 状态 | 价格 | VR20D | DEV20W | 目标仓位 | 次日动作 |",
        "|------|------|------|------|-------|--------|----------|----------|",
    ]

    has_rows = False
    for item in signals:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        code = item.get("code", "")
        state = item.get("state", "")
        price = float(item.get("price", 0.0) or 0.0)
        vr20d = float(item.get("vr20d", 0.0) or 0.0)
        dev20w = float(item.get("dev20w", 0.0) or 0.0) * 100.0
        position_target = float(item.get("position_target", 0.0) or 0.0) * 100.0
        action = item.get("action_next_day", "")
        lines.append(
            f"| {name} | {code} | {state} | {price:.2f} | {vr20d:.2f} | {dev20w:+.1f}% | {position_target:.0f}% | {action} |"
        )
        reason = str(item.get("reason", "")).strip()
        if reason:
            lines.append(f"|  |  |  |  |  |  |  | 理由: {_escape_md(reason)} |")
        has_rows = True

    lines += [
        "",
        "## 出场信号",
        "",
    ]
    if not exits:
        lines.append("无出场信号。")
    else:
        lines.append("| 股票 | 代码 | 状态 | 价格 | 次日动作 | 理由 |")
        lines.append("|------|------|------|------|----------|------|")
        for item in exits:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| {name} | {code} | {state} | {price:.2f} | {action} | {reason} |".format(
                    name=item.get("name", ""),
                    code=item.get("code", ""),
                    state=item.get("state", ""),
                    price=float(item.get("price", 0.0) or 0.0),
                    action=item.get("action_next_day", ""),
                    reason=_escape_md(str(item.get("reason", ""))),
                )
            )

    if not has_rows and not exits:
        return "", "watchlist_signals.md"

    lines.append("")
    return "\n".join(lines), "watchlist_signals.md"


# ── 主逻辑 ────────────────────────────────────────────

# 转换器注册表：(转换函数, 类别名, 读取方式)
# 读取方式: "direct" = 主 agent 直读, "subagent" = sub agent 输入
_CONVERTERS: list[tuple[Callable, str, str]] = [
    # 新闻类 — 正文较长，交给 sub agent 做语义分析
    (convert_news_headline, "新闻资讯", "subagent"),
    (convert_news_daily, "新闻资讯", "subagent"),
    (convert_news_opportunity, "新闻资讯", "subagent"),
    (convert_news_realtime, "新闻资讯", "subagent"),
    (convert_news_flash, "新闻资讯", "direct"),  # 快讯较短，可直读
    # 淘股吧社区 — 帖子正文较长，交给 sub agent
    (convert_taoguba_recommend, "社区讨论", "subagent"),
    (convert_taoguba_hot_discussion, "社区讨论", "subagent"),
    (convert_taoguba_hot, "社区讨论", "subagent"),
    # 市场数据 — 结构化数据，压缩后较小，主 agent 直读
    (convert_market_sectors, "市场数据", "direct"),
    (convert_funding, "市场数据", "direct"),
    (convert_us_market, "市场数据", "direct"),
    # 元数据 — 极小，主 agent 直读
    (convert_collection_summary, "采集元数据", "direct"),
    (convert_trade_date, "采集元数据", "direct"),
    (convert_run_id, "采集元数据", "direct"),
    (convert_broker_account, "账户数据", "direct"),
    # 观察列表买入信号
    (convert_watchlist_signals, "趋势分析", "direct"),
]

# 已有的 Markdown 文件（直接复制到 filtered/）
# (文件名, 类别名, 读取方式)
_EXISTING_MD_FILES: list[tuple[str, str, str]] = [
    ("ths_report.md", "涨停分析", "direct"),
    ("trend_report.md", "趋势分析", "direct"),
]


def filter_all(raw_dir: str, output_dir: str) -> dict:
    """执行全量 JSON→Markdown 转换。

    Args:
        raw_dir: 原始数据目录。
        output_dir: filtered 输出目录。

    Returns:
        转换结果摘要。
    """
    os.makedirs(output_dir, exist_ok=True)

    # (filename, category, size_kb, read_mode)
    results: list[tuple[str, str, float, str]] = []
    converted = 0
    skipped = 0
    errors = 0

    # JSON → Markdown 转换
    for converter_fn, category, read_mode in _CONVERTERS:
        try:
            content, filename = converter_fn(raw_dir)
            if not content:
                skipped += 1
                logger.info("跳过 %s（无数据）", filename)
                continue

            out_path = os.path.join(output_dir, filename)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)

            size_kb = _file_size_kb(out_path)
            results.append((filename, category, size_kb, read_mode))
            converted += 1
            logger.info("转换完成: %s (%.1f KB)", filename, size_kb)
        except Exception as e:
            errors += 1
            logger.exception("转换失败 (%s): %s", converter_fn.__name__, e)

    # 复制已有的 Markdown 文件
    for md_file, category, read_mode in _EXISTING_MD_FILES:
        content, filename = _copy_existing_md(raw_dir, md_file)
        if content:
            out_path = os.path.join(output_dir, filename)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            size_kb = _file_size_kb(out_path)
            results.append((filename, category, size_kb, read_mode))
            converted += 1
            logger.info("复制完成: %s (%.1f KB)", filename, size_kb)
        else:
            skipped += 1

    # 生成索引
    as_of_date = os.path.basename(os.path.dirname(output_dir.rstrip("/")))
    index_content = generate_index(output_dir, raw_dir, results, as_of_date)
    index_path = os.path.join(output_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)

    summary = {
        "converted": converted,
        "skipped": skipped,
        "errors": errors,
        "files": [(f, s) for f, _, s, _ in results],
        "total_size_kb": sum(s for _, _, s, _ in results),
    }

    logger.info(
        "转换完成: %d 成功, %d 跳过, %d 失败, 总大小 %.1f KB",
        converted,
        skipped,
        errors,
        summary["total_size_kb"],
    )

    return summary


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="将 raw/ JSON 数据转换为 filtered/ Markdown"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="原始数据目录（raw/）",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Markdown 输出目录（filtered/）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[filter] %(message)s",
    )

    summary = filter_all(args.input_dir, args.output_dir)

    print(
        f"[filter] 完成: {summary['converted']} 转换, "
        f"{summary['skipped']} 跳过, {summary['errors']} 失败",
        file=sys.stderr,
    )
    print(f"[filter] 总大小: {summary['total_size_kb']:.1f} KB", file=sys.stderr)


if __name__ == "__main__":
    main()
