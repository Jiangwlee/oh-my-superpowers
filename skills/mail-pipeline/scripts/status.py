"""Report mail-pipeline status."""

from __future__ import annotations

import json

from common import DIRECTORIES, EVENT_FILES, config_dir, data_dir, events_dir, logs_dir, pending_dir, state_dir


def _status(root_exists: bool, directories: dict[str, bool], config: dict[str, object], event_counts: dict[str, int | None]) -> str:
    if not root_exists:
        return "not_initialized"
    dirs_ready = all(directories.get(name, False) for name in DIRECTORIES)
    config_ready = bool(config["accounts_exists"]) and bool(config["processors_exists"])
    events_ready = all(count is not None for count in event_counts.values())
    return "ready" if dirs_ready and config_ready and events_ready else "partial"


def main() -> None:
    root = data_dir()
    event_counts = {}
    for name in EVENT_FILES:
        path = events_dir(root) / name
        if path.exists():
            event_counts[name] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        else:
            event_counts[name] = None
    config = {
        "accounts": str(config_dir(root) / "accounts.yaml"),
        "accounts_exists": (config_dir(root) / "accounts.yaml").exists(),
        "processors": str(config_dir(root) / "processors.yaml"),
        "processors_exists": (config_dir(root) / "processors.yaml").exists(),
    }
    pending = []
    if pending_dir(root).exists():
        for path in sorted(pending_dir(root).glob("*.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            pending.append(
                {
                    "pending_id": manifest.get("pending_id", path.stem),
                    "subject": (manifest.get("source") or {}).get("subject"),
                    "files": [record.get("saved_path") for record in manifest.get("attachments") or []],
                }
            )
    directories = {
        "config": config_dir(root).exists(),
        "events": events_dir(root).exists(),
        "files": (root / "files").exists(),
        "state": state_dir(root).exists(),
        "logs": logs_dir(root).exists(),
    }
    print(
        json.dumps(
            {
                "data_dir": str(root),
                "exists": root.exists(),
                "config": config,
                "directories": directories,
                "event_counts": event_counts,
                "pending_extractions": pending,
                "status": _status(root.exists(), directories, config, event_counts),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
