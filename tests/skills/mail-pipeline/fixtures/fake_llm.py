"""Fake multimodal LLM for tests: prints fixed invoice field JSON."""

from __future__ import annotations

import json

print(
    json.dumps(
        {
            "invoice_date": "2026-06-04",
            "invoice_number": "26427000000465806619",
            "amount": 314.4,
            "tax_rate": "13%",
            "purchase_content": "通信服务费",
            "seller": "测试电信公司",
            "confidence": 0.95,
        },
        ensure_ascii=False,
    )
)
