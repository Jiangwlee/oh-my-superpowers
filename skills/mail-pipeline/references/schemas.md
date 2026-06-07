# Schemas

Every event written to JSONL MUST include:

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
  "status": "pending_extraction"
}
```

The dedupe key MUST combine `account_id`, `message_id`, and the attachment
sha256 list; messages without attachments key on `message_id` alone.

Status values: `pending_extraction` (staged via `stage`, waiting for agent
fields via `submit`), `processed`, `discarded` (pending item dropped via
`submit --discard`, staged files removed, reason recorded).

`mailbox` commands append audit events with status `mailbox_action` (or
`mailbox_action_failed`): `source.imap_uids` lists the touched messages and
`actions[0]` carries the type (`mark_read`/`move_email`), target folder, and
the agent's `reason`. Attachment records gain `origin`
(`zip`/`link`), `source_zip`, or `source_url` when the PDF was expanded from
a zip or fetched from an allowlisted provider link.

## extracted.invoice

`stage` saves PDFs for the calling agent; the agent reads each staged PDF,
extracts fields, and submits them via `omp mail-pipeline submit` (no regex
parsing, no LLM call inside scripts):

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
- All fields except `confidence` are required; `stage` fails fast when a
  message has no pdf/zip attachment and no allowlisted link — the agent
  reroutes it per the invoice SOP.
- `submit` cross-checks `invoice_number` and `amount` against provider
  metadata when the PDF came from a link provider; mismatches reject the
  submit and keep the manifest pending. Provider dates are not compared
  (they reflect issuing-request time, not the invoice date on the PDF face).
