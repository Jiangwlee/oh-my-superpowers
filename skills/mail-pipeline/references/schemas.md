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
