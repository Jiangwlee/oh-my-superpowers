# mail-pipeline

Turn mailbox messages into structured local data through an agent-driven
triage loop: JSONL events, archived attachments, and SQLite processing
state.

## What

- Read-only IMAP ingestion: `list` (unread work queue with summaries) and
  `show` (full body) feed the calling agent's judgment.
- Scenario handling by the agent: invoices are staged (`stage`), extracted
  by the agent reading the PDF, and finalized (`submit`); ads and handled
  notifications are dispatched through explicit `mailbox` actions.
- Auditable state: every action appends a JSONL event; dedupe lives in
  SQLite; invoice files are renamed `{invoice_date}_{invoice_number}_{seller}`.

## Why this shape

- Scripts do deterministic work only (fetch, save, validate, rename,
  audit); classification and every mailbox decision belong to the calling
  AI agent. Scripts never call an LLM.
- Mailbox safety: no send/reply/forward/delete; only `\Seen` flags and
  folder moves, each carrying the agent's recorded reason.
- Unread is the work queue: marking read is the completion signal, so
  repeated runs converge instead of re-processing.

## Command Tree

```text
omp mail-pipeline
├── init [--apply]
├── accounts (list | check) --account <id|all>
├── list --account <id|all> [--since <YYYY-MM-DD>] [--limit <n>] [--include-seen]
├── show --account <id> --uid <uid>
├── stage --account <id> --uid <uid>
├── submit --id <pending-id> (--fields <json> [--invoice-file <name>] | --discard --reason <text>)
├── mailbox (mark-read | move [--to <folder>]) --account <id> --uid <uid>... [--reason <text>]
└── status
```

## Storage

Default root `~/.local/share/oh-my-superpowers/mail-pipeline/` (override:
`MAIL_PIPELINE_DATA_DIR`). Secrets stay in environment variables, never in
config files or the data directory.

## Where the details live

| Topic | File |
|---|---|
| Agent workflow and scenario routing | `SKILL.md` |
| Per-scenario SOPs | `references/sops/` |
| Interface flow and safety defaults | `references/pipeline.md` |
| Account / processor configuration | `references/config.md` |
| JSONL event schemas | `references/schemas.md` |
| Directory contract | `references/storage.md` |
