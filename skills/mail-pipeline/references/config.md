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
      trash: Deleted Messages
```

`folders` maps logical names to server folder names; `mailbox move --to`
references a logical name (QQ mail: trash is `Deleted Messages`, the spam
folder is `Junk`).

`config/processors.yaml` defines business processors:

```yaml
processors:
  - name: invoices
    description: "Identify invoice or billing emails, save PDF attachments, and extract invoice metadata."
    output_jsonl: events/invoices.jsonl
    file_dir: files/{account_id}/invoices
    extract: invoice
    rename_template: "{invoice_date}_{invoice_number}_{seller}"
    link_providers:
      - nuonuo
      - xforceplus
      - keruyun
    allowed_actions:
      - write_jsonl
      - save_attachment
      - add_label
      - move_email
```

Keep processor names stable; downstream JSONL consumers may depend on them.

Optional processor fields:

- `extract` — extraction contract; `invoice` stages PDFs (from pdf/zip
  attachments, zip members expanded; only pdf/zip attachment types are
  processed) and writes a pending manifest for the calling agent to fill
  via `submit`. Scripts never call an LLM.
- `rename_template` — base filename rendered from submitted fields at
  `submit` time; each value is path-sanitized. Files keep their extensions.
- `link_providers` — allowlist of invoice link providers to fetch from when
  a message has no pdf/zip attachment. Registered providers: `nuonuo`
  (nnfp.jss.com.cn short link → detail API → PDF, with invoice_number/amount
  metadata for cross-check), `xforceplus` (saas.xforceplus.com delivery
  links, PDF kept by magic bytes), `keruyun` (invoice.keruyun.com short
  links from krystore@service.alibaba.com, redirect straight to the PDF).
  URLs from emails are never fetched unless
  their host matches a registered provider; provider requests bypass
  environment proxies. Link fetch only runs under `--apply`.
