# Invoice Configuration

Default root:

```text
~/.local/share/oh-my-superpowers/invoice/
```

Override with:

```text
INVOICE_DATA_DIR
```

Directory contract:

```text
config/
  sources.yaml
  owners.yaml
events/
  all.jsonl
files/
  pending/
  available/
state/
  invoices.sqlite
```

## Sources

`config/sources.yaml` explicitly maps source IDs to local directories and
owners. Source IDs are audit identifiers, not user-facing ownership rules.

```yaml
sources:
  example_wechat:
    kind: local_dir
    path: ~/path/to/invoice/inbox
    owner: Example Owner
```

Rules:

- `scan` reads `sources.yaml`.
- `kind` must be `local_dir` in v1.
- `owner` comes from the configured source.
- `scan` copies files into the registry and never moves or deletes source files.
- Supported file suffix is `.pdf`. Images are ignored by `scan`.

## Owners

`config/owners.yaml` stores owner-level substitute rules.

```yaml
owners:
  Example Owner:
    substitute_rule: |
      Natural-language rule for deciding whether an invoice is a substitute.
```

Rules:

- Empty `substitute_rule` means no substitute logic for that owner.
- The Agent reads the rule and decides `purpose`.
- Scripts do not call an LLM and do not infer `purpose`.
