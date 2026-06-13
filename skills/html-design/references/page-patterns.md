# Page Patterns

Choose one page pattern before writing CSS. A prototype may combine supporting
sections, but each HTML page should have one primary reader task.

## Pattern Map

| Pattern | Use for | Primary reader task | Starter |
|---|---|---|---|
| `report` | Research conclusions, investigation reports, design reports | Read a narrative argument and inspect sources | `assets/report-template.html` |
| `brief` | Daily digests, mail summaries, status summaries | Scan prioritized items and act on urgent ones | `assets/brief-template.html` |
| `review` | Code review, skill review, design critique | Triage findings and decide what to fix | `assets/review-template.html` |
| `index` | Collections of generated pages or resources | Find a recent artifact by namespace/date | `assets/index-template.html` |
| `prototype` | New page design or significant redesign | Preview, tune, and export design decisions | `assets/prototype-workbench.html` |

## Style Families

Style family is independent of page pattern. Select it from the audience,
domain, and content pressure, not from personal taste.

| Family | Best for | Shape |
|---|---|---|
| `editorial-report` | Deep research, long-form synthesis, design reports | Strong typographic entry point, generous rhythm, compact sources |
| `operational-brief` | Mail triage, status summaries, run outputs | Action-first lanes, dense lists, subdued typography |
| `digest-magazine` | Daily AI briefs, curated media digests | Scannable hierarchy, tiered stories, one distinctive editorial move |
| `review-console` | Code/skill/design review findings | Severity lanes, file/path metadata, decision affordances |
| `index-catalog` | Directory pages and artifact collections | Searchable directory, recency grouping, low visual drama |
| `prototype-lab` | Designing a new page direction | Split preview/control workspace with exportable decisions |

Recommended combinations:

| Scenario | Pattern | Family |
|---|---|---|
| Research or strategy report | `report` | `editorial-report` |
| Operational digest | `brief` | `operational-brief` |
| Media or trend brief | `brief` | `digest-magazine` |
| Review or audit findings | `review` | `review-console` |
| Resource catalog | `index` | `index-catalog` |

## Selection Rules

- Use `report` when the conclusion and evidence matter more than immediate
  action.
- Use `brief` when the page is consumed repeatedly and the user needs the top
  items within one minute.
- Use `review` when each item needs a decision such as accept, defer, dismiss,
  or fix.
- Use `index` only when the page is itself navigation. Do not wrap every report
  in an index.
- Use `prototype` whenever designing a new page. The prototype is a design
  tool, not the final static page.
- If two families seem plausible, prototype both as separate directions instead
  of averaging them into a bland middle.

## Output Packaging

When a direction is accepted, preserve:

```text
<workspace>/DESIGN.md
<workspace>/prototypes/<chosen-page>.html
<workspace>/exports/<design-decisions>.json
```

The final `DESIGN.md` must state:

- User scenario and audience.
- Primary information organization model.
- Selected design-system reference and what was adapted.
- Layout, typography, color, component, and interaction rules.
- Prototype controls that affected the final design.

## Template Boundary

Templates should include only stable structure, style, and placeholder markers.
They should not include personal URLs, temporary notes, or fake metrics that
could be mistaken for real content.

## State Coverage

For interactive or generated pages, design the states the page can produce:

| State | Required when |
|---|---|
| Populated | Always. This is the normal page. |
| Empty | A list, source set, finding set, or digest section can be empty. |
| Error | The page can include failed fetches, partial generation, or skipped sources. |
| Edge | Long titles, missing optional metadata, many sources, and mobile width. |

Static pages do not need spinners unless they fetch client-side data. If
JavaScript loads data after page open, include a loading state and a timeout
fallback.
