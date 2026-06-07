"""Link-delivered invoice fetching for mail-pipeline.

Emails are untrusted input: only URLs whose host matches an allowlisted
provider are ever fetched. Provider domains bypass environment proxies and
are requested directly.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any

# Registered providers: name -> hosts that trigger it.
PROVIDER_HOSTS = {
    "xforceplus": ["saas.xforceplus.com"],
    "nuonuo": ["nnfp.jss.com.cn"],
    "keruyun": ["invoice.keruyun.com"],
}

_NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_TIMEOUT = 60


class _HrefParser(HTMLParser):
    """Collect href/src URLs from an HTML body."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in ("href", "src") and value and value.startswith("http"):
                self.urls.append(html.unescape(value))


def _scan_bare_urls(text: str) -> list[str]:
    """Collect bare http(s) tokens from plain text."""
    urls: list[str] = []
    for token in text.split():
        if token.startswith("http"):
            urls.append(token.strip(".,;)>」』、。"))
    return urls


def extract_urls(message: dict) -> list[str]:
    """Extract candidate URLs from a message body.

    HTML bodies contribute both href/src attributes and bare URLs in text
    (some senders ship text/html parts containing plain text with a raw
    link). Plain-text bodies are token-scanned.
    """
    urls: list[str] = []
    body = message.get("html") or ""
    if body:
        parser = _HrefParser()
        parser.feed(body)
        urls.extend(parser.urls)
        urls.extend(_scan_bare_urls(html.unescape(body)))
    urls.extend(_scan_bare_urls(str(message.get("text") or "")))
    return list(dict.fromkeys(urls))


def match_provider(url: str, enabled: list[str]) -> str | None:
    """Return the enabled provider name whose host matches the URL, if any."""
    host = urllib.parse.urlsplit(url).hostname or ""
    for provider in enabled:
        if host in PROVIDER_HOSTS.get(provider, []):
            return provider
    return None


def _get(url: str, timeout: int = _TIMEOUT) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 mail-pipeline"})
    with _NO_PROXY_OPENER.open(request, timeout=timeout) as response:
        return response.read()


def _post_form(url: str, data: dict[str, str], headers: dict[str, str], timeout: int = _TIMEOUT) -> bytes:
    body = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"User-Agent": "Mozilla/5.0 mail-pipeline", **headers})
    with _NO_PROXY_OPENER.open(request, timeout=timeout) as response:
        return response.read()


def _resolve_final_url(url: str, timeout: int = _TIMEOUT) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 mail-pipeline"})
    with _NO_PROXY_OPENER.open(request, timeout=timeout) as response:
        return response.geturl()


def _is_pdf(payload: bytes) -> bool:
    return payload[:5] == b"%PDF-"


def _attachment_record(filename: str, payload: bytes, source_url: str) -> dict[str, Any]:
    return {
        "filename": filename,
        "mime_type": "application/pdf",
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "content_b64": base64.b64encode(payload).decode("ascii"),
        "origin": "link",
        "source_url": source_url,
    }


def _fetch_xforceplus(urls: list[str]) -> tuple[list[dict], dict]:
    """Fetch xforceplus delivery links; only PDF payloads are kept."""
    attachments: list[dict] = []
    for index, url in enumerate(urls):
        if "/api/invoice-sharing/delivery/receive" not in url:
            continue
        payload = _get(url)
        if _is_pdf(payload):
            attachments.append(_attachment_record(f"xforceplus_{index}.pdf", payload, url))
    return attachments, {}


def _fetch_nuonuo(urls: list[str]) -> tuple[list[dict], dict]:
    """Resolve a nuonuo short link to the detail API, then fetch the PDF."""
    short = next((url for url in urls if "getEwmImg" not in url), None)
    if short is None:
        return [], {}
    final_url = _resolve_final_url(short)
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(final_url).query)
    param_list = (query.get("paramList") or [None])[0]
    if not param_list:
        raise ValueError(f"nuonuo redirect missing paramList: {final_url}")
    encoded = urllib.parse.quote(param_list, safe="")
    payload = _post_form(
        "https://nnfp.jss.com.cn/sapi/scan2/getIvcDetailShow.do",
        {"paramList": encoded, "code": encoded, "shortLinkSource": "1"},
        {"referer": "https://nnfp.jss.com.cn/scan-invoice/printQrcode"},
    )
    detail = json.loads(payload.decode("utf-8"))
    if detail.get("status") != "0000":
        raise ValueError(f"nuonuo detail API status: {detail.get('status')}")
    vo = detail["data"]["invoiceSimpleVo"]
    pdf_url = vo.get("url")
    if not pdf_url:
        raise ValueError("nuonuo detail response has no PDF url")
    pdf = _get(pdf_url)
    if not _is_pdf(pdf):
        raise ValueError("nuonuo PDF url did not return a PDF")
    provider_meta = {
        "provider": "nuonuo",
        "invoice_number": vo.get("fphm"),
        "amount": vo.get("orderTotal"),
        "invoice_date": str(vo.get("invoiceDate") or "")[:10],
        "seller": vo.get("saleName"),
    }
    return [_attachment_record(f"nuonuo_{vo.get('fphm') or 'invoice'}.pdf", pdf, pdf_url)], provider_meta


def _fetch_keruyun(urls: list[str]) -> tuple[list[dict], dict]:
    """Fetch keruyun short links; they redirect straight to the invoice PDF."""
    attachments: list[dict] = []
    for index, url in enumerate(urls):
        payload = _get(url)
        if _is_pdf(payload):
            attachments.append(_attachment_record(f"keruyun_{index}.pdf", payload, url))
    return attachments, {}


_FETCHERS = {
    "xforceplus": _fetch_xforceplus,
    "nuonuo": _fetch_nuonuo,
    "keruyun": _fetch_keruyun,
}


def fetch_link_attachments(message: dict, enabled: list[str]) -> tuple[list[dict], dict]:
    """Fetch PDF attachments delivered via allowlisted provider links.

    Returns (attachment_records, provider_meta). Raises ValueError when a
    matched provider fails to deliver a PDF.
    """
    urls = extract_urls(message)
    by_provider: dict[str, list[str]] = {}
    for url in urls:
        provider = match_provider(url, enabled)
        if provider:
            by_provider.setdefault(provider, []).append(url)
    attachments: list[dict] = []
    provider_meta: dict = {}
    for provider, provider_urls in by_provider.items():
        fetched, meta = _FETCHERS[provider](provider_urls)
        attachments.extend(fetched)
        if meta:
            provider_meta = meta
    return attachments, provider_meta
