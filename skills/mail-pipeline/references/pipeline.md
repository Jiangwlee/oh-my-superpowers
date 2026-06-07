# Pipeline

Stages:

1. Resolve data directory and load configs.
2. Select account IDs and processors.
3. Fetch candidate messages from IMAP.
4. Normalize each message into metadata, text, and attachment records.
5. Classify and extract structured fields.
6. Plan actions.
7. Execute actions only when `--apply` is present.
8. Write JSONL events and update dedupe state.

Safety defaults:

- Dry-run is the default.
- No send, reply, forward, or delete tools.
- Secrets come from environment variables.
- Attachments stay under the configured data directory unless explicitly configured.
- Uncertain messages are routed to `needs_review`.
