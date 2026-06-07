# Pipeline

Stages:

1. Resolve data directory and load configs.
2. Select account IDs and processors.
3. Fetch candidate messages from IMAP.
4. Normalize each message into metadata, text, and attachment records.
5. Collect invoice PDFs: pdf/zip attachments (zip members expanded), else
   allowlisted provider link fetch (`--apply` only).
6. Stage PDFs and write a pending manifest per invoice message.
7. Execute actions only when `--apply` is present.
8. Write JSONL events and update dedupe state.
9. The calling agent reads each staged PDF, extracts fields, and finalizes
   via `submit` (validate, cross-check, rename, final event).
10. The calling agent judges each message from the `messages` summary (and
    body content when needed) and executes decisions through the `mailbox`
    interfaces: `mark-read` (`\Seen`) and `move` (`UID MOVE`, falling back
    to COPY+`\Deleted`+EXPUNGE on servers without MOVE). Every action is
    appended to `events/all.jsonl` with the agent's reason.

Safety defaults:

- Dry-run is the default.
- No send, reply, forward, or delete tools.
- Secrets come from environment variables.
- Attachments stay under the configured data directory unless explicitly configured.
- Uncertain messages are routed to `needs_review`.
- Email URLs are fetched only when the host matches a registered link
  provider; everything else in an email body is treated as untrusted.
- Scripts never call an LLM; field extraction belongs to the calling agent.
- Mailbox mutations are limited to `\Seen` flags and folder moves, happen
  only through the explicit `mailbox` commands, and are always decided by
  the calling agent per message — keyword classification is a routing hint
  and never drives a mailbox action.
