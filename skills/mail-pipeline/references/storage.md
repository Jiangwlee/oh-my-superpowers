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
files/
  <account-id>/
    invoices/
state/
  processed.sqlite
  pending/
    <pending-id>.json
logs/
  runs.jsonl
```

Secrets must not be stored anywhere under this directory.
