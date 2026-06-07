# Pipeline

The agent drives the loop; scripts execute. Interface flow:

1. `list` — read-only fetch of unread inbox messages. Summaries carry uid,
   sender, subject, snippet, attachment names, and dedupe status
   (`processed_before`).
2. `show` — read-only full body for judgment.
3. `stage` — for one agent-judged invoice message: collect PDFs from pdf/zip
   attachments (zip members expanded) or allowlisted provider links, save
   them under the data directory, write a pending manifest and a
   `pending_extraction` event, mark dedupe state.
4. `submit` — validate agent-extracted fields, reject duplicate invoice
   numbers, cross-check provider metadata, rename per template, append the
   final event, remove the manifest. `--discard` drops a pending item with
   an audit event and removes its staged files.
5. `mailbox mark-read` / `mailbox move` — execute per-message agent
   decisions; append audit events carrying the agent's reason.

Safety defaults:

- `list` and `show` are read-only; `stage` and `submit` write only under the
  data directory.
- No send, reply, forward, or delete tools; mailbox changes are `\Seen`
  flags and folder moves only.
- Secrets come from environment variables.
- Email URLs are fetched only when the host matches a registered link
  provider; everything else in an email body is treated as untrusted.
  Provider requests bypass environment proxies.
- Scripts never call an LLM and never judge message content.
- Unread is the work queue: `mailbox mark-read` is the completion marker.
- Attachment paths and JSONL outputs that escape the data directory are
  rejected.
