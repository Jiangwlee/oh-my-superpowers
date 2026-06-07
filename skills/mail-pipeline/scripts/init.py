"""Initialize mail-pipeline storage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import (
    DIRECTORIES,
    EVENT_FILES,
    config_dir,
    data_dir,
    default_accounts_yaml,
    default_processors_yaml,
    default_providers_yaml,
    events_dir,
)


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize mail-pipeline storage.")
    parser.add_argument("--dry-run", action="store_true", help="Preview directories without writing.")
    args = parser.parse_args()

    root = data_dir()
    account_config = config_dir(root) / "accounts.yaml"
    processor_config = config_dir(root) / "processors.yaml"
    provider_config = config_dir(root) / "providers.yaml"
    plan = {
        "data_dir": str(root),
        "directories": DIRECTORIES,
        "config_files": [str(account_config), str(processor_config), str(provider_config)],
        "event_files": [str(events_dir(root) / name) for name in EVENT_FILES],
        "dry_run": args.dry_run,
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))

    if args.dry_run:
        return
    for name in DIRECTORIES:
        (root / name).mkdir(parents=True, exist_ok=True)
    _write_if_missing(account_config, default_accounts_yaml())
    _write_if_missing(processor_config, default_processors_yaml())
    _write_if_missing(provider_config, default_providers_yaml())
    for name in EVENT_FILES:
        (events_dir(root) / name).touch(exist_ok=True)


if __name__ == "__main__":
    main()
