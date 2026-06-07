# Schemas

Every event written to JSONL should include:

```json
{
  "schema_version": "1.0",
  "processed_at": "2026-06-07T10:30:00+08:00",
  "account_id": "work",
  "source": {
    "mailbox": "INBOX",
    "message_id": "<message@example.com>",
    "imap_uid": "12345",
    "from": "billing@example.com",
    "to": ["me@example.com"],
    "subject": "Invoice INV-001",
    "date": "2026-06-06T18:20:00+08:00"
  },
  "classification": {
    "category": "invoices",
    "confidence": 0.92,
    "reason": "Subject and PDF attachment indicate an invoice."
  },
  "extracted": {},
  "attachments": [],
  "actions": [],
  "status": "dry_run"
}
```

Use `message_id + attachment sha256` for attachment-level dedupe when possible.

## extracted.invoice

Processors with `extract: invoice` fill `extracted.invoice` via multimodal LLM
extraction from the PDF attachment (no regex parsing):

```json
{
  "invoice_date": "2026-06-04",
  "invoice_number": "26427000000465806619",
  "amount": 314.4,
  "tax_rate": "*",
  "purchase_content": "通信服务费",
  "seller": "中国电信股份有限公司武汉分公司",
  "confidence": 0.96
}
```

- `amount` is the tax-inclusive total (价税合计).
- `tax_rate` keeps face-value markers such as `*` verbatim.
- All fields except `confidence` are required; extraction failure routes the
  message to `needs_review` and leaves `extracted` empty.
