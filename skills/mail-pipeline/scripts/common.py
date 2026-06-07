"""Shared helpers for the mail-pipeline skill."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "oh-my-superpowers" / "mail-pipeline"
EVENT_FILES = [
    "all.jsonl",
    "invoices.jsonl",
    "spam_ads.jsonl",
    "important.jsonl",
    "needs_review.jsonl",
    "errors.jsonl",
]
DIRECTORIES = ["config", "events", "files", "state", "logs"]


def data_dir() -> Path:
    """Return the mail-pipeline data directory."""

    env = os.environ.get("MAIL_PIPELINE_DATA_DIR")
    return Path(env).expanduser() if env else DEFAULT_DATA_DIR


def config_dir(root: Path) -> Path:
    """Return the config directory under a data root."""

    return root / "config"


def events_dir(root: Path) -> Path:
    """Return the events directory under a data root."""

    return root / "events"


def state_dir(root: Path) -> Path:
    """Return the state directory under a data root."""

    return root / "state"


def logs_dir(root: Path) -> Path:
    """Return the logs directory under a data root."""

    return root / "logs"


def dump_json(path: Path, payload: Any) -> None:
    """Write JSON with stable formatting."""

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_text_if_exists(path: Path) -> str | None:
    """Return text content when a file exists."""

    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def default_accounts_yaml() -> str:
    """Return a starter account config without secrets."""

    return """# Mailbox accounts. Store passwords/app passwords in environment variables.
accounts:
  - id: work
    provider: imap
    host: imap.example.com
    port: 993
    username: me@example.com
    password_env: MAIL_PIPELINE_WORK_PASSWORD
    folders:
      inbox: INBOX
      processed: AI/Processed
      needs_review: AI/NeedsReview
"""


def default_processors_yaml() -> str:
    """Return starter processor config."""

    return """processors:
  - name: invoices
    description: "Identify invoice or billing emails, save PDF attachments, and extract invoice metadata."
    output_jsonl: events/invoices.jsonl
    file_dir: files/{account_id}/invoices
    allowed_actions:
      - write_jsonl
      - save_attachment
      - add_label
      - move_email

  - name: spam_ads
    description: "Identify ads, promotions, newsletters, and low-value subscription emails."
    output_jsonl: events/spam_ads.jsonl
    allowed_actions:
      - write_jsonl
      - add_label
      - move_email

  - name: important
    description: "Extract tasks, deadlines, customer requests, account security notices, and other important information."
    output_jsonl: events/important.jsonl
    allowed_actions:
      - write_jsonl
      - add_label

  - name: needs_review
    description: "Catch uncertain messages for manual review."
    output_jsonl: events/needs_review.jsonl
    allowed_actions:
      - write_jsonl
      - add_label
"""
