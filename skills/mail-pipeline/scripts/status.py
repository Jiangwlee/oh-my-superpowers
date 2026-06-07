"""Report mail-pipeline status."""

from __future__ import annotations

import json

from common import data_dir


def main() -> None:
    root = data_dir()
    print(
        json.dumps(
            {
                "data_dir": str(root),
                "exists": root.exists(),
                "status": "not_implemented",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
