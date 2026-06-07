---
name: invoice
description: >-
  Use when managing a unified local invoice registry with `omp invoice`:
  scheduled scans of configured local source directories, pending invoice
  extraction, ownership assignment, claim/substitute classification, status
  updates, listing, and archive operations. Do NOT use for downloading email,
  reading mailboxes, or source-specific chat app automation.
---

# invoice

Maintain one local invoice registry for reimbursement workflows. The registry
does not understand WeChat, email, or other business channels; callers provide
files or configure local directories, and `omp invoice` records source IDs only
for audit and dedupe.

## Hard Gates

| Condition | Action |
|---|---|
| User asks to fetch or process email | Use `mail-pipeline`; register only its resulting files with `omp invoice add` if needed. |
| User asks for daily invoice intake from configured folders | Use `omp invoice scan`, not `add --source`. |
| Field extraction is needed from a PDF | Use the Agent's multimodal PDF reading. Do not use regex, text scraping, OCR, or deterministic scripts to infer invoice fields. |
| A pending invoice lacks a readable invoice number | Do not submit. Leave it pending and report what field is missing. |
| A pending item is a duplicate, non-invoice attachment, or wrong file | Use `omp invoice discard --id <id> --reason <text>`; never delete source files manually. |
| Owner has no substitute rule | Classify new invoices as `claim` unless user gives a direct reason to mark `substitute`. |
| User asks whether a file was already imported | Use `omp invoice pending`, `omp invoice list`, or `omp invoice status`; source directories are not the factual registry. |

## Daily Intake

Run this loop for scheduled invoice intake, such as every day at 23:00:

1. Ensure storage exists:

   ```bash
   omp invoice init --apply
   ```

2. Scan configured local directory sources:

   ```bash
   omp invoice scan
   ```

   Load `references/config.md` if sources or owner rules need inspection.

3. List pending files:

   ```bash
   omp invoice pending
   ```

4. For each pending PDF, inspect the PDF with the Agent's multimodal reading
   ability and extract the required fields in `references/registry.md`. Load
   the owner's `substitute_rule` from `config/owners.yaml`; decide `purpose`
   as `claim` or `substitute`.

5. Submit each resolved pending item:

   ```bash
   omp invoice submit --id <pending_id> --purpose claim --fields '{"invoice_number":"123","invoice_date":"2026-06-01","amount":100.0,"seller":"某公司"}'
   ```

6. Discard pending items that are confirmed duplicates or not invoice PDFs:

   ```bash
   omp invoice discard --id <pending_id> --reason "duplicate invoice already registered"
   ```

7. Finish with:

   ```bash
   omp invoice status
   ```

Done when `status` reports zero pending invoices or every remaining pending
file has a reported reason.

## Manual Registration

Use `add` only for manual or external-system registration. It copies a file into
pending and assigns an audit `source_id`; the normal scheduled source path is
`scan`.

```bash
omp invoice add /path/to/invoice.pdf --owner 李江维 --source-id manual
omp invoice pending
omp invoice submit --id <pending_id> --purpose substitute --fields '{"invoice_number":"123","invoice_date":"2026-06-01","amount":100.0,"seller":"某公司"}'
```

## Registry Operations

| Need | Command |
|---|---|
| List available invoices | `omp invoice list` |
| Filter by owner, purpose, status, or date | `omp invoice list --owner 李江维 --purpose claim --status available --since 2026-01-01` |
| Mark an invoice used by reimbursement | `omp invoice mark-used --invoice-number <number> --reason <text>` |
| Hide an invoice from default lists | `omp invoice archive --invoice-number <number> --reason <text>` |
| Drop a pending duplicate or wrong file | `omp invoice discard --id <id> --reason <text>` |
| Show counts and data directory | `omp invoice status` |

Load `references/cli.md` for the full command contract.

## References

| Need | File |
|---|---|
| Data directory, source config, owner substitute rules | `references/config.md` |
| Registry fields, status, purpose, dedupe rules | `references/registry.md` |
| Complete CLI command map | `references/cli.md` |
