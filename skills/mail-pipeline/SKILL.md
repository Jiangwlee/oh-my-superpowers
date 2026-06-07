---
name: mail-pipeline
description: >-
  Use when turning one or more IMAP mailboxes into structured local outputs:
  classified JSONL events, downloaded attachments, and auditable processing
  state. Use for repeatable mailbox ingestion, classification, and attachment
  archiving SOPs. Do NOT use for sending mail, MCP email tools, one-off email
  reading, or full email-client workflows.
---

# mail-pipeline

Process multiple IMAP mailboxes through a conservative local pipeline. AI may
classify and extract fields, but scripts perform mailbox access, file writes,
dedupe, and audit output.

## Hard Gates

| Condition | Action |
|---|---|
| User wants to send, reply, forward, or delete mail | Stop. This skill is read/organize only. |
| Mailbox credentials are requested in config or chat | Stop. Use password environment variables. |
| User asks for MCP integration | Explain that v1 is an IMAP pipeline; MCP is out of scope. |
| Action would modify mailbox state without `--apply` | Stop. Default is dry-run/read-only. |

## Workflow

1. Initialize storage and templates with `omp mail-pipeline init`.
2. Configure accounts in `config/accounts.yaml`; secrets stay in environment variables.
3. Validate account connectivity with `omp mail-pipeline accounts check`.
4. Run a dry-run ingest with `omp mail-pipeline run --account <id> --limit <n>`.
5. Review JSONL decisions and only then rerun with `--apply`.
6. Use `omp mail-pipeline status` to inspect runs, counts, and errors.

## CLI

```bash
omp mail-pipeline <subcommand> [args]
```

| Command | Purpose |
|---|---|
| `init` | Create the data directory, config templates, event files, and state directory. |
| `accounts list` | Show configured account IDs without printing secrets. |
| `accounts check` | Validate IMAP connectivity for configured accounts. |
| `run` | Process messages through configured processors. Defaults to dry-run. |
| `status` | Report recent runs, output files, and state summary. |

## Storage

Default root: `~/.local/share/oh-my-superpowers/mail-pipeline/`

Override with `MAIL_PIPELINE_DATA_DIR`.

See `references/storage.md` for the directory contract and `references/config.md`
for account and processor config.

## References

| Need | File |
|---|---|
| Storage layout and event files | `references/storage.md` |
| Account and processor config | `references/config.md` |
| Processing stages and safety defaults | `references/pipeline.md` |
| JSONL schemas | `references/schemas.md` |
