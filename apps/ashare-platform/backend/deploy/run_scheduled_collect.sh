#!/usr/bin/env bash
set -euo pipefail

cd /app

python - <<'PY'
from __future__ import annotations

import json

from app.core.runtime import today_cn
from app.core.trade_calendar import resolve_trade_dates
from app.tasks.collect_all import run as run_collect_all

today = today_cn()
trade_dates = resolve_trade_dates(end_date=today, days=1)
if not trade_dates:
    print(json.dumps({"status": "skip", "reason": "no_trade_dates", "today": today}, ensure_ascii=False))
    raise SystemExit(0)

latest_trade_date = trade_dates[-1]
if latest_trade_date != today:
    print(
        json.dumps(
            {"status": "skip", "reason": "not_trade_day", "today": today, "latest_trade_date": latest_trade_date},
            ensure_ascii=False,
        )
    )
    raise SystemExit(0)

result = run_collect_all(trade_date=today, with_ephemeral=True)
print(json.dumps({"status": "ok", "trade_date": today, "result": result}, ensure_ascii=False))
PY
