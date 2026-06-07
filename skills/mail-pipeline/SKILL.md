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

Triage IMAP mailboxes in an agent-driven loop. Scripts provide deterministic
interfaces (fetch, stage, finalize, mailbox actions); the calling agent
judges every message by content.

## Hard Gates

| Condition | Action |
|---|---|
| User wants to send, reply, forward, or delete mail | Stop. Read/organize only: `\Seen` flags and folder moves, never permanent deletion. |
| Mailbox credentials are requested in config or chat | Stop. Passwords come from environment variables only. |
| User asks for MCP integration | Explain that v1 is an IMAP pipeline; MCP is out of scope. |
| A script would judge message content (classify, pick what to flag or move) | Stop. Scripts never call an LLM; classification and every mailbox action are agent decisions. |
| html-serve container not running when rendering the report | Tell user: `cd ~/Dockers/html-serve && docker compose up -d`; deliver the chat summary regardless. |

## Main Loop

1. Ensure storage exists: `omp mail-pipeline init --apply` (plain `init` only
   previews). Configure accounts per `references/config.md`; validate with
   `omp mail-pipeline accounts check`.
2. Fetch the work queue: `omp mail-pipeline list --account qq --since 2026-05-01`.
   Unread messages are the queue; read means handled. Add `--include-seen`
   only to revisit handled mail. `processed_before: true` means the message
   was staged or archived in an earlier run (dedupe state) — it never blocks
   notification or ad handling.
3. For each message: classify it by content against the Scenario Routing
   table. When subject and snippet are not enough, run
   `omp mail-pipeline show --account qq --uid 1581` for the full body. Load
   the matched SOP file and execute from its Step 1. After the SOP finishes,
   continue with the next message.
4. Render the report page from `assets/report-template.html` (replace the
   sample markers with this run's data; follow the template's section and
   merge rules) and write it to
   `~/Dockers/html-serve/data/mail-brief/<YYYY-MM-DD>-mail-brief.html` —
   one page per day, merged across same-day runs. Give the user both URLs:
   - `http://ubuntu-gem12.tail82a434.ts.net:8888/mail-brief/<date>-mail-brief.html`
   - `http://192.168.5.140:8888/mail-brief/<date>-mail-brief.html`

   Summarize the same content briefly in chat: action items first, then
   counts. Do not generate a Markdown archive — `events/*.jsonl` is the
   factual record.

Done when: every listed message has a scenario, a completed SOP, and is
marked read (or moved); `omp mail-pipeline status` shows zero pending
extractions; and the report is delivered. The report — not the unread flag
— carries action-required items and open questions.

## Scenario Routing

| Scenario | Judge by | SOP |
|---|---|---|
| invoice | Formal invoice delivery: pdf/zip invoice attachment, or a link from an invoice provider (nuonuo, xforceplus, keruyun) | `references/sops/invoice.md` |
| ad | Marketing, promotion, newsletter, or subscription noise with no personal or business value | `references/sops/ad.md` |
| notification | Service-generated notices (security alerts, billing reminders, account notices) that inform but deliver no formal invoice | `references/sops/notification.md` |
| anything else / uncertain | Fits no scenario above, or judgment is uncertain | `references/sops/default.md` |

## CLI

```bash
omp mail-pipeline <subcommand> [args]
```

| Command | Purpose |
|---|---|
| `init` | Create the data directory and config templates. Defaults to dry-run preview; `--apply` writes. |
| `accounts list` / `accounts check` | Show configured account IDs / validate IMAP connectivity. |
| `list` | List unread inbox messages with summaries (uid, from, subject, snippet, attachments, dedupe status). Read-only. `--since` bounds the range; `--include-seen` widens. |
| `show` | Show one message in full: body text and attachment list. Read-only. |
| `stage` | Stage one agent-judged invoice message: collect PDFs (pdf/zip attachments with zip expansion, or allowlisted provider links), save them, write a pending manifest. |
| `submit` | Finalize a pending extraction: validate fields, reject duplicate invoice numbers, cross-check provider metadata, rename, write the final event. `--discard --reason` drops a pending item. |
| `mailbox mark-read` / `mailbox move` | Execute an agent decision: flag `\Seen` / move to a configured folder. `--reason` is recorded in the audit event. |
| `status` | Report data-dir readiness, event counts, and pending extractions. |

## Storage

Default root: `~/.local/share/oh-my-superpowers/mail-pipeline/`

Override with `MAIL_PIPELINE_DATA_DIR`.

## References

| Need | File |
|---|---|
| Scenario SOPs (routed from Scenario Routing) | `references/sops/` |
| Report page template (Main Loop step 4) | `assets/report-template.html` |
| Interface flow and safety defaults | `references/pipeline.md` |
| Account and processor config | `references/config.md` |
| JSONL schemas | `references/schemas.md` |
| Storage layout and event files | `references/storage.md` |
