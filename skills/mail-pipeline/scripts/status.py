"""Report mail-pipeline status."""

from __future__ import annotations

import json

from common import EVENT_FILES, config_dir, data_dir, events_dir, logs_dir, state_dir


def main() -> None:
    root = data_dir()
    event_counts = {}
    for name in EVENT_FILES:
        path = events_dir(root) / name
        if path.exists():
            event_counts[name] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        else:
            event_counts[name] = None
    print(
        json.dumps(
            {
                "data_dir": str(root),
                "exists": root.exists(),
                "config": {
                    "accounts": str(config_dir(root) / "accounts.yaml"),
                    "accounts_exists": (config_dir(root) / "accounts.yaml").exists(),
                    "processors": str(config_dir(root) / "processors.yaml"),
                    "processors_exists": (config_dir(root) / "processors.yaml").exists(),
                },
                "directories": {
                    "events": events_dir(root).exists(),
                    "state": state_dir(root).exists(),
                    "logs": logs_dir(root).exists(),
                },
                "event_counts": event_counts,
                "status": "ready" if root.exists() else "not_initialized",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
