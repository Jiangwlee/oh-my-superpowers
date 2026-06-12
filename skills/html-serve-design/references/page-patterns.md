# Page Patterns

Choose one page pattern before writing CSS. A target skill may own multiple
templates, but each template should have one primary reading task.

## Pattern Map

| Pattern | Use for | Primary reader task | Starter |
|---|---|---|---|
| `report` | Research conclusions, investigation reports, design reports | Read a narrative argument and inspect sources | `assets/report-template.html` |
| `brief` | Daily digests, mail summaries, status summaries | Scan prioritized items and act on urgent ones | `assets/brief-template.html` |
| `review` | Code review, skill review, design critique | Triage findings and decide what to fix | `assets/review-template.html` |
| `index` | Collections of generated pages | Find a recent artifact by namespace/date | `assets/index-template.html` |
| `prototype` | New template design or significant redesign | Preview, tune, export design decisions | `assets/prototype-workbench.html` |

## Style Families

Style family is independent of page pattern. Select it from the target skill's
reader task, not from personal taste.

| Family | Best for | Shape |
|---|---|---|
| `editorial-report` | Deep research, long-form synthesis, design reports | Strong typographic entry point, generous rhythm, compact sources |
| `operational-brief` | Mail triage, status summaries, run outputs | Action-first lanes, dense lists, subdued typography |
| `digest-magazine` | Daily AI briefs, curated media digests | Scannable hierarchy, tiered stories, one distinctive editorial move |
| `review-console` | Code/skill/design review findings | Severity lanes, file/path metadata, decision affordances |
| `index-catalog` | html-serve home pages and artifact collections | Searchable directory, recency grouping, low visual drama |
| `prototype-lab` | Designing a new target-skill template | Split preview/control workspace with exportable decisions |

Recommended combinations:

| Target skill type | Pattern | Family |
|---|---|---|
| `deep-research` | `report` | `editorial-report` |
| `daily-ai-brief` | `brief` | `digest-magazine` |
| `mail-pipeline` | `brief` | `operational-brief` |
| `skill-review` / `code-review` | `review` | `review-console` |
| html-serve directory pages | `index` | `index-catalog` |

## Selection Rules

- Use `report` for `deep-research` final reports: conclusion first, supporting
  sections second, source list last.
- Use `brief` when the page is consumed repeatedly and the user needs the top
  items within one minute.
- Use `review` when each item needs a decision such as accept, defer, dismiss,
  or fix.
- Use `index` only when the page is itself navigation. Do not wrap every report
  in an index.
- Use `prototype` whenever designing a new target-skill template. The prototype
  is a design tool, not the final target skill output.
- If two families seem plausible, prototype both as two presets in the
  workbench instead of averaging them into a bland middle.

## Target Skill Packaging

When a pattern is accepted, package the target skill with:

```text
skills/<target-skill>/assets/<page-name>.html
skills/<target-skill>/references/<html-reporting-name>.md
```

The target reference must state:

- Input fields or source files used to populate the template.
- Output filename convention.
- html-serve relative path convention.
- What to do when html-serve is not configured or not running.
- Which artifacts remain the audit source outside the HTML page.

## Template Boundary

Templates should include only stable structure, style, and placeholder markers.
They should not include a real report copied from one run, personal URLs, or
temporary prototype notes.

## State Coverage

For interactive or generated pages, design the states the target skill can
produce:

| State | Required when |
|---|---|
| Populated | Always. This is the normal generated page. |
| Empty | A list, source set, finding set, or digest section can be empty. |
| Error | The page can include failed fetches, partial generation, or skipped sources. |
| Edge | Long titles, missing optional metadata, many sources, and mobile width. |

Static result pages do not need spinners unless they fetch client-side data.
If JavaScript loads data after page open, include a loading state and a timeout
fallback.
