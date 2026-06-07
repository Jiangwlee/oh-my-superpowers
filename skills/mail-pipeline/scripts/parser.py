"""MIME message parsing for mail-pipeline."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class _TextExtractor(HTMLParser):
    """Collect visible text from an HTML body."""

    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self.chunks.append(data.strip())


def body_text(message: dict) -> str:
    """Return the message body as plain text (HTML stripped when needed)."""
    text = str(message.get("text") or "").strip()
    if text:
        return text
    html = str(message.get("html") or "")
    if not html:
        return ""
    extractor = _TextExtractor()
    extractor.feed(html)
    return " ".join(extractor.chunks)


@dataclass(slots=True)
class Attachment:
    """Parsed attachment payload and metadata."""

    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    content_b64: str


def _addresses(message: Message, header: str) -> list[str]:
    values = message.get_all(header, [])
    return [addr for _, addr in getaddresses(values) if addr]


def _date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except Exception:
        return value


def parse_bytes(raw: bytes, account_id: str, mailbox: str, imap_uid: str | None = None) -> dict[str, Any]:
    """Parse a raw RFC 822 message into normalized metadata and attachments."""

    message = BytesParser(policy=policy.default).parsebytes(raw)
    text_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[Attachment] = []

    for part in message.walk():
        if part.is_multipart():
            continue
        disposition = part.get_content_disposition()
        content_type = part.get_content_type()
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if disposition == "attachment" or filename:
            name = filename or "attachment"
            attachments.append(
                Attachment(
                    filename=name,
                    mime_type=content_type,
                    size_bytes=len(payload),
                    sha256=hashlib.sha256(payload).hexdigest(),
                    content_b64=base64.b64encode(payload).decode("ascii"),
                )
            )
            continue
        if content_type == "text/plain":
            text_parts.append(part.get_content())
        elif content_type == "text/html":
            html_parts.append(part.get_content())

    return {
        "account_id": account_id,
        "source": {
            "mailbox": mailbox,
            "message_id": message.get("Message-ID"),
            "imap_uid": imap_uid,
            "from": _addresses(message, "From"),
            "to": _addresses(message, "To"),
            "cc": _addresses(message, "Cc"),
            "subject": message.get("Subject", ""),
            "date": _date(message.get("Date")),
        },
        "text": "\n".join(part.strip() for part in text_parts if part.strip()),
        "html": "\n".join(part.strip() for part in html_parts if part.strip()),
        "attachments": [
            {
                "filename": item.filename,
                "mime_type": item.mime_type,
                "size_bytes": item.size_bytes,
                "sha256": item.sha256,
                "content_b64": item.content_b64,
            }
            for item in attachments
        ],
    }


def parse_file(path: Path, account_id: str = "fixture", mailbox: str = "INBOX") -> dict[str, Any]:
    """Parse a local fixture message file."""

    return parse_bytes(path.read_bytes(), account_id=account_id, mailbox=mailbox)
