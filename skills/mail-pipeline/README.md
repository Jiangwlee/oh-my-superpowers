# mail-pipeline

Turn mailbox messages into structured local data: JSONL events, downloaded
attachments, and SQLite processing state.

## Current Scope

`mail-pipeline` is a conservative local pipeline.

- It supports IMAP account configuration, connectivity checks, and read-only
  IMAP ingestion (`--fixture-dir` switches to local `.eml` files).
- It writes structured JSONL output under a local data directory.
- It saves attachments only when `--apply` is used and the selected processor allows `save_attachment`.
- Invoice messages are staged for the calling AI agent: scripts collect PDFs
  (attachments, zip members, or allowlisted provider links), the agent reads
  them and finalizes via `submit`. Scripts never call an LLM.
- It does not send, reply, forward, or delete email.

## Command Tree

```text
omp mail-pipeline
├── init --dry-run | --apply
├── accounts
│   ├── list --account <id|all>
│   └── check --account <id|all>
├── run --account <id|all> --processor <name|all> --limit <n> --since <YYYY-MM-DD> --fixture-dir <dir> [--apply]
├── submit --id <pending-id> (--fields <json> [--invoice-file <name>] | --discard --reason <text>)
└── status
```

## Initialize Storage

Preview the workspace:

```bash
omp mail-pipeline init --dry-run
```

Create the workspace:

```bash
omp mail-pipeline init --apply
```

Default storage root:

```text
~/.local/share/oh-my-superpowers/mail-pipeline/
```

Override it when needed:

```bash
export MAIL_PIPELINE_DATA_DIR=/path/to/mail-pipeline-data
```

## Configure Accounts

Edit:

```text
~/.local/share/oh-my-superpowers/mail-pipeline/config/accounts.yaml
```

Example:

```yaml
accounts:
  - id: work
    provider: imap
    host: imap.company.com
    port: 993
    username: me@company.com
    password_env: MY_WORK_MAIL_APP_PASSWORD
    folders:
      inbox: INBOX
      processed: AI/Processed
      needs_review: AI/NeedsReview

  - id: personal
    provider: imap
    host: imap.example.com
    port: 993
    username: me@example.com
    password_env: MY_PERSONAL_MAIL_APP_PASSWORD
    folders:
      inbox: INBOX
      processed: AI/Processed
      needs_review: AI/NeedsReview
```

`password_env` names the environment variable that contains the password or app
password. The names are user-defined; they only need to match your shell
environment.

Set the secrets outside the YAML file:

```bash
export MY_WORK_MAIL_APP_PASSWORD='...'
export MY_PERSONAL_MAIL_APP_PASSWORD='...'
```

Do not write real passwords into `accounts.yaml`.

## Configure Processors

Edit:

```text
~/.local/share/oh-my-superpowers/mail-pipeline/config/processors.yaml
```

Example processor:

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

See `references/config.md` for `extract`, `rename_template`, and
`link_providers` semantics.

Important path rules:

- `output_jsonl` must be relative to `MAIL_PIPELINE_DATA_DIR`.
- `file_dir` must be relative to `MAIL_PIPELINE_DATA_DIR`.
- Paths that escape the data directory are rejected.

## Validate Accounts

List configured accounts without printing secrets:

```bash
omp mail-pipeline accounts list
```

List one account:

```bash
omp mail-pipeline accounts list --account work
```

Check IMAP connectivity:

```bash
omp mail-pipeline accounts check --account work
```

`accounts check` verifies login and selected inbox access. It fails if the
password environment variable is missing.

## Run The Pipeline

Dry-run local `.eml` fixtures:

```bash
omp mail-pipeline run \
  --fixture-dir tests/skills/mail-pipeline/fixtures \
  --limit 5
```

Dry-run returns planned events in stdout and does not write JSONL, attachments,
or SQLite state.

Apply the fixture run:

```bash
omp mail-pipeline run \
  --fixture-dir tests/skills/mail-pipeline/fixtures \
  --processor invoices \
  --apply
```

`--apply` writes:

- `events/all.jsonl`
- processor-specific JSONL such as `events/invoices.jsonl`
- allowed attachments under `files/<account-id>/<processor>/`
- dedupe state under `state/processed.sqlite`

Repeat `--apply` is idempotent for already processed message/attachment
combinations.

## Inspect Status

```bash
omp mail-pipeline status
```

Status reports:

- storage root
- required config file presence
- required directory presence
- JSONL event counts
- pending extractions waiting for `submit`
- readiness state: `not_initialized`, `partial`, or `ready`

## Output Layout

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
state/
  processed.sqlite
logs/
```

## Safety Notes

- Default mode is dry-run.
- `--apply` is required for file writes and state updates.
- Passwords must come from environment variables.
- The pipeline rejects output paths outside the configured data directory.
- v1 does not send, reply, forward, delete, or permanently discard email.
