# Config

`config/accounts.yaml` stores mailbox connection metadata and environment
variable names for secrets:

```yaml
accounts:
  - id: work
    provider: imap
    host: imap.example.com
    port: 993
    username: me@example.com
    password_env: MAIL_PIPELINE_WORK_PASSWORD
    folders:
      inbox: INBOX
      processed: AI/Processed
      needs_review: AI/NeedsReview
```

`config/processors.yaml` defines business processors:

```yaml
processors:
  - name: invoices
    description: "Identify invoice or billing emails, save PDF attachments, and extract invoice metadata."
    output_jsonl: events/invoices.jsonl
    file_dir: files/{account_id}/invoices
    allowed_actions:
      - write_jsonl
      - save_attachment
      - add_label
      - move_email
```

Keep processor names stable; downstream JSONL consumers may depend on them.
