"""Tonghuashun site adapters backed by the reusable CDP collector."""

from __future__ import annotations

import logging

from ashare_data.cdp import CdpClient

logger = logging.getLogger(__name__)

_THS_QUOTE_CENTER_URL = "https://q.10jqka.com.cn/"


def fetch_indexflash_via_cdp() -> dict:
    """Fetch THS indexflash payload via a real browser session."""
    client = CdpClient()
    session = client.open_page(_THS_QUOTE_CENTER_URL)
    try:
        session.wait_for_network_idle(1.5)
        return session.fetch_json("/api.php?t=indexflash", headers={"Accept": "*/*"})
    finally:
        session.close()
