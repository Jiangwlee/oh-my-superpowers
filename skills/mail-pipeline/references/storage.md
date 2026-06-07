# Storage

Default root:

```text
~/.local/share/oh-my-superpowers/mail-pipeline/
```

Override with:

```text
MAIL_PIPELINE_DATA_DIR
```

Directory contract:

```text
config/
  accounts.yaml
  processors.yaml
events/
  all.jsonl
  invoices.jsonl
  spam_ads.jsonl
  important.jsonl
  needs_review.jsonl
  errors.jsonl
files/
  <account-id>/
    invoices/
    receipts/
    attachments/
    needs_review/
state/
  processed.sqlite
logs/
  runs.jsonl
```

Secrets must not be stored anywhere under this directory.
