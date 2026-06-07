# Invoice CLI

All commands are routed through:

```bash
omp invoice <subcommand> [args]
```

| Command | Purpose |
|---|---|
| `init --apply` | Create data directories, SQLite state, and config templates. Plain `init` previews. |
| `scan [--source <id>] [--limit <n>]` | Scan configured local directory sources and copy new files into pending. |
| `add <file> --owner <owner> [--source-id manual]` | Manually copy one file into pending. |
| `pending` | List pending imported files awaiting Agent extraction. |
| `submit --id <id> --purpose claim\|substitute --fields <json>` | Finalize one pending invoice into the registry. |
| `discard --id <id> --reason <text>` | Drop one pending item and delete only its copied pending file. |
| `list [filters]` | List registered invoices; defaults to available, non-archived invoices. |
| `mark-used --invoice-number <number> [--reason <text>]` | Mark an invoice used. |
| `archive --invoice-number <number> [--reason <text>]` | Mark an invoice archived; default list output hides it. |
| `status` | Report data directory, pending count, and registry counts. |

## List Filters

```bash
omp invoice list \
  --owner 李江维 \
  --purpose claim \
  --status available \
  --since 2026-01-01 \
  --until 2026-06-30
```

Use `--status all` for all non-archived statuses. Add `--include-archived` to
include archived invoices.
