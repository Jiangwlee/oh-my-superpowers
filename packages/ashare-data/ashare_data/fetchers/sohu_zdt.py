"""Sohu historical up/down limit page fetcher.

Purpose: Fetch and parse the SSR historical zdt table from q.stock.sohu.com.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from bs4 import BeautifulSoup

from ashare_data.core.http_client import http_bytes

logger = logging.getLogger(__name__)

_SOHU_ZDT_URL = "https://q.stock.sohu.com/cn/zdt.shtml"
_SOHU_HEADERS = {
    "Referer": "https://q.stock.sohu.com/",
}


def fetch_sohu_zdt_history(anchor_date: date | None = None) -> list[dict[str, Any]]:
    """Fetch Sohu historical zdt rows from the SSR HTML page.

    Args:
        anchor_date: Anchor date used to infer the year for ``MM/DD`` rows.

    Returns:
        Parsed row list. Returns an empty list on errors.
    """
    try:
        body = http_bytes(_SOHU_ZDT_URL, headers=_SOHU_HEADERS, timeout=15, retries=3)
        html = _decode_sohu_html(body)
        return parse_sohu_zdt_history_html(html, anchor_date=anchor_date)
    except Exception as exc:
        logger.exception("fetch_sohu_zdt_history 出错: %s", exc)
        return []


def parse_sohu_zdt_history_html(
    html: str,
    anchor_date: date | None = None,
) -> list[dict[str, Any]]:
    """Parse Sohu historical zdt table HTML with BeautifulSoup.

    Args:
        html: Decoded HTML text.
        anchor_date: Anchor date used to infer the year for ``MM/DD`` rows.

    Returns:
        Parsed row list.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = _find_history_table(soup)
    if table is None:
        return []

    rows: list[dict[str, Any]] = []
    raw_dates: list[str] = []
    for tr in table.find_all("tr"):
        cells = [_clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        if len(cells) != 14:
            continue
        raw_dates.append(cells[0])
        rows.append(
            {
                "raw_trade_date": cells[0],
                "limit_up_count": _to_int(cells[1]),
                "limit_down_count": _to_int(cells[2]),
                "suspended_count": _to_int(cells[3]),
                "turnover_billion": _to_float(cells[4]),
                "shanghai": _parse_market_counts(cells[5:8]),
                "shenzhen": _parse_market_counts(cells[8:11]),
                "beijing": _parse_market_counts(cells[11:14]),
            }
        )

    resolved_dates = _resolve_trade_dates(raw_dates, anchor_date=anchor_date)
    for row, trade_date in zip(rows, resolved_dates, strict=False):
        row["trade_date"] = trade_date

    return rows


def _find_history_table(soup: BeautifulSoup) -> Any | None:
    """Find the SSR history table by header texts."""
    for table in soup.find_all("table"):
        header_text = _clean_text(table.get_text(" ", strip=True))
        if "涨停只数" in header_text and "跌停只数" in header_text and "成交额(亿)" in header_text:
            return table
    return None


def _clean_text(value: str) -> str:
    """Normalize whitespace."""
    return " ".join(value.replace("\xa0", " ").split())


def _decode_sohu_html(body: bytes) -> str:
    """Decode Sohu HTML bytes.

    The live page currently returns UTF-8 with BOM, while the response header may
    still claim GBK. Prefer UTF-8 variants first, then fall back to GBK.
    """
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="ignore")


def _to_int(value: str) -> int | None:
    """Parse integer-like text."""
    text = value.replace(",", "").strip()
    if text in {"", "--"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _to_float(value: str) -> float | None:
    """Parse float-like text."""
    text = value.replace(",", "").strip()
    if text in {"", "--"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_market_counts(value: str | list[str]) -> dict[str, int | None]:
    """Parse market up/flat/down counts."""
    if isinstance(value, list):
        parts = [part.strip() for part in value]
    else:
        parts = [part.strip() for part in value.replace(" ", "").split("/")]
    while len(parts) < 3:
        parts.append("")
    return {
        "advance_count": _to_int(parts[0]),
        "flat_count": _to_int(parts[1]),
        "decline_count": _to_int(parts[2]),
    }


def _resolve_trade_dates(raw_dates: list[str], anchor_date: date | None = None) -> list[str | None]:
    """Infer year for descending ``MM/DD`` rows using an anchor date."""
    if not raw_dates:
        return []

    current = anchor_date or date.today()
    current_year = current.year
    previous_month_day: tuple[int, int] | None = None
    resolved: list[str | None] = []

    for raw_date in raw_dates:
        parts = raw_date.split("/")
        if len(parts) != 2:
            resolved.append(None)
            continue
        try:
            month = int(parts[0])
            day_of_month = int(parts[1])
        except ValueError:
            resolved.append(None)
            continue

        month_day = (month, day_of_month)
        if previous_month_day is not None and month_day > previous_month_day:
            current_year -= 1
        previous_month_day = month_day
        resolved.append(f"{current_year:04d}-{month:02d}-{day_of_month:02d}")

    return resolved
