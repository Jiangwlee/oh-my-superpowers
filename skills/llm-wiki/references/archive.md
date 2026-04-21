# Archive Guidance

Karpathy's pattern treats valuable query outputs as cumulative knowledge. If an output should help a future query, it belongs in the wiki rather than only in chat history.

## Archive-worthy Outputs

- durable research summaries
- comparison notes
- project retrospectives
- query answers that add reusable understanding

## How To Archive

Only archive when the user explicitly asks to save or archive the answer.

1. Write the answer as a new wiki page using `references/archive-template.md` (once moved: `assets/archive-template.md`).
   - `Sources`: markdown links to the wiki articles cited in the answer.
   - No `Raw:` field — content comes from compiled wiki, not raw/.
   - File name reflects the query topic (e.g., `transformer-architectures-overview.md`).
   - Place in the most relevant topic directory.
2. Always create a new page. Never merge into existing articles — archive pages are point-in-time snapshots and are never cascade-updated.
3. Update `wiki/index.md`: add entry, prefix Summary with `[Archived]`.
4. Append to `wiki/log.md`:

   ```
   - YYYY-MM-DD  query | Archived: <page title>
   ```
