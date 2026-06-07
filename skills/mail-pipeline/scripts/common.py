"""Shared helpers for the mail-pipeline skill."""

from __future__ import annotations

from dataclasses import dataclass
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


def pending_dir(root: Path) -> Path:
    """Return the pending-extraction manifest directory under a data root."""

    return root / "state" / "pending"


def logs_dir(root: Path) -> Path:
    """Return the logs directory under a data root."""

    return root / "logs"


def safe_name(value: str) -> str:
    """Sanitize a string for use as a single path component."""

    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value.strip())
    return cleaned.strip("._") or "message"


def within_root(root: Path, path: Path) -> bool:
    """Return True when path resolves inside root."""

    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def safe_relative_path(root: Path, value: str) -> Path:
    """Resolve a config-supplied relative path, rejecting escapes from root."""

    raw = Path(value)
    if raw.is_absolute():
        raise ValueError(f"path must be relative to data dir: {value}")
    target = root / raw
    if not within_root(root, target):
        raise ValueError(f"path escapes data dir: {value}")
    return target


def append_jsonl(path: Path, event: Any) -> None:
    """Append one event to a JSONL file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


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
      trash: Deleted Messages
"""


def default_processors_yaml() -> str:
    """Return starter processor config."""

    return """processors:
  - name: invoices
    description: "Identify invoice or billing emails, save PDF attachments, and extract invoice metadata."
    output_jsonl: events/invoices.jsonl
    file_dir: files/{account_id}/invoices
    extract: invoice
    rename_template: "{invoice_date}_{invoice_number}_{seller}"
    link_providers:
      - nuonuo
      - xforceplus
      - keruyun
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


@dataclass(slots=True)
class Account:
    """Configured IMAP account without secret material."""

    id: str
    provider: str
    host: str
    port: int
    username: str
    password_env: str
    inbox: str
    processed: str | None
    needs_review: str | None
    trash: str | None


@dataclass(slots=True)
class Processor:
    """Configured business processor."""

    name: str
    description: str
    output_jsonl: str
    file_dir: str | None
    allowed_actions: list[str]
    extract: str | None
    rename_template: str | None
    link_providers: list[str]


def accounts_config_path(root: Path) -> Path:
    """Return the account config path."""

    return config_dir(root) / "accounts.yaml"


def processors_config_path(root: Path) -> Path:
    """Return the processor config path."""

    return config_dir(root) / "processors.yaml"


def load_accounts(root: Path) -> list[Account]:
    """Load account config without reading password values."""

    path = accounts_config_path(root)
    if not path.exists():
        raise FileNotFoundError(f"accounts config not found: {path}. Run `omp mail-pipeline init --apply` first.")
    raw = load_yaml(path)
    accounts = raw.get("accounts") or []
    if not isinstance(accounts, list):
        raise ValueError("accounts.yaml must contain an `accounts` list")

    loaded: list[Account] = []
    seen: set[str] = set()
    for item in accounts:
        if not isinstance(item, dict):
            raise ValueError("each account entry must be a mapping")
        account_id = str(item.get("id", "")).strip()
        if not account_id:
            raise ValueError("account entry missing `id`")
        if account_id in seen:
            raise ValueError(f"duplicate account id: {account_id}")
        seen.add(account_id)
        folders = item.get("folders") or {}
        loaded.append(
            Account(
                id=account_id,
                provider=str(item.get("provider", "imap")),
                host=str(item.get("host", "")).strip(),
                port=int(item.get("port", 993)),
                username=str(item.get("username", "")).strip(),
                password_env=str(item.get("password_env", "")).strip(),
                inbox=str(folders.get("inbox", "INBOX")),
                processed=folders.get("processed"),
                needs_review=folders.get("needs_review"),
                trash=folders.get("trash"),
            )
        )
    return loaded


def load_processors(root: Path) -> list[Processor]:
    """Load processor config."""

    path = processors_config_path(root)
    if not path.exists():
        raise FileNotFoundError(f"processors config not found: {path}. Run `omp mail-pipeline init --apply` first.")
    raw = load_yaml(path)
    processors = raw.get("processors") or []
    if not isinstance(processors, list):
        raise ValueError("processors.yaml must contain a `processors` list")
    loaded: list[Processor] = []
    seen: set[str] = set()
    for item in processors:
        if not isinstance(item, dict):
            raise ValueError("each processor entry must be a mapping")
        name = str(item.get("name", "")).strip()
        if not name:
            raise ValueError("processor entry missing `name`")
        if name in seen:
            raise ValueError(f"duplicate processor name: {name}")
        seen.add(name)
        actions = item.get("allowed_actions") or []
        loaded.append(
            Processor(
                name=name,
                description=str(item.get("description", "")).strip(),
                output_jsonl=str(item.get("output_jsonl", f"events/{name}.jsonl")),
                file_dir=item.get("file_dir"),
                allowed_actions=[str(action) for action in actions],
                extract=item.get("extract"),
                rename_template=item.get("rename_template"),
                link_providers=[str(provider) for provider in (item.get("link_providers") or [])],
            )
        )
    return loaded


def select_accounts(accounts: list[Account], selected: str) -> list[Account]:
    """Select accounts by id or return all."""

    if selected == "all":
        return accounts
    matched = [account for account in accounts if account.id == selected]
    if not matched:
        valid = ", ".join(account.id for account in accounts) or "<none>"
        raise ValueError(f"unknown account {selected!r}; valid accounts: {valid}")
    return matched


def select_processors(processors: list[Processor], selected: str) -> list[Processor]:
    """Select processors by name or return all."""

    if selected == "all":
        return processors
    matched = [processor for processor in processors if processor.name == selected]
    if not matched:
        valid = ", ".join(processor.name for processor in processors) or "<none>"
        raise ValueError(f"unknown processor {selected!r}; valid processors: {valid}")
    return matched


def account_public_dict(account: Account) -> dict[str, Any]:
    """Return account metadata safe for command output."""

    return {
        "id": account.id,
        "provider": account.provider,
        "host": account.host,
        "port": account.port,
        "username": account.username,
        "password_env": account.password_env,
        "folders": {
            "inbox": account.inbox,
            "processed": account.processed,
            "needs_review": account.needs_review,
        },
    }


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML with PyYAML when available, otherwise use a small config parser."""

    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        return yaml.safe_load(text) or {}
    except ModuleNotFoundError:
        if "processors:" in text:
            return _load_simple_processors_yaml(text)
        return _load_simple_accounts_yaml(text)


def _load_simple_accounts_yaml(text: str) -> dict[str, Any]:
    """Parse the limited accounts.yaml shape used by this skill."""

    accounts: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    folders: dict[str, str] | None = None
    in_accounts = False
    in_folders = False
    for raw_line in text.splitlines():
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue
        stripped = line_without_comment.strip()
        indent = len(line_without_comment) - len(line_without_comment.lstrip(" "))
        if stripped == "accounts:":
            in_accounts = True
            continue
        if not in_accounts:
            continue
        if indent == 2 and stripped.startswith("- "):
            current = {}
            accounts.append(current)
            folders = None
            in_folders = False
            key_value = stripped[2:]
            if key_value:
                key, value = _parse_key_value(key_value)
                current[key] = value
            continue
        if current is None:
            continue
        if indent == 4 and stripped == "folders:":
            folders = {}
            current["folders"] = folders
            in_folders = True
            continue
        if ":" not in stripped:
            continue
        key, value = _parse_key_value(stripped)
        if in_folders and indent >= 6 and folders is not None:
            folders[key] = str(value)
        elif indent == 4:
            current[key] = value
            in_folders = False
    return {"accounts": accounts}


def _parse_key_value(value: str) -> tuple[str, Any]:
    key, _, raw = value.partition(":")
    parsed = raw.strip().strip("\"'")
    if parsed.isdigit():
        return key.strip(), int(parsed)
    return key.strip(), parsed


def _load_simple_processors_yaml(text: str) -> dict[str, Any]:
    """Parse the limited processors.yaml shape used by this skill."""

    processors: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_list_key: str | None = None
    in_processors = False
    for raw_line in text.splitlines():
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue
        stripped = line_without_comment.strip()
        indent = len(line_without_comment) - len(line_without_comment.lstrip(" "))
        if stripped == "processors:":
            in_processors = True
            continue
        if not in_processors:
            continue
        if indent == 2 and stripped.startswith("- "):
            current = {}
            processors.append(current)
            current_list_key = None
            key_value = stripped[2:]
            if key_value:
                key, value = _parse_key_value(key_value)
                current[key] = value
            continue
        if current is None:
            continue
        if indent == 4 and stripped.endswith(":"):
            current_list_key = stripped[:-1]
            current[current_list_key] = []
            continue
        if indent >= 6 and stripped.startswith("- ") and current_list_key:
            current[current_list_key].append(stripped[2:].strip().strip("\"'"))
            continue
        if indent == 4 and ":" in stripped:
            key, value = _parse_key_value(stripped)
            current[key] = value
            current_list_key = None
    return {"processors": processors}
