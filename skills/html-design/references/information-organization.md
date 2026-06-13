# Information Organization

Choose the information model before choosing the visual style. The model
defines what the page asks the reader to do first, what belongs above the fold,
and which controls the prototype should expose.

## Researched Models

This list comes from a quick IA survey across Web Style Guide, Nielsen Norman
Group IA material, and common website-structure references. The recurring base
structures are hierarchical, sequential, matrix, and database-driven; exact and
ambiguous organization schemes add alphabetical, chronological, geographical,
topic, task, audience, and faceted/tagged variants.

| Model | Use When | Prototype Shape |
|---|---|---|
| Hierarchical tree | The user narrows from broad category to detail. | Sidebar or nested nav, parent/child sections, breadcrumbs. |
| Flat hierarchy | Most sections are peers and must be reachable quickly. | Top nav, section bands, shallow anchors. |
| Sequential flow | The user must follow ordered steps or a timeline. | Stepper, timeline, wizard, progress rail. |
| Chronological timeline | Time is the organizing truth. | Dated sections, reverse chronology, release/history lanes. |
| Alphabetical index | Users know the item name and need direct lookup. | A-Z index, search, compact directory rows. |
| Geographical map | Place or region is the primary filter. | Map/list split, region tabs, location metadata. |
| Matrix/network | Users browse across many possible paths. | Cross-links, cards with related paths, comparison grid. |
| Database/catalog | Many records need filtering, sorting, and scanning. | Table/card catalog, filter rail, sort controls, saved views. |
| Faceted/tagged | Multiple attributes matter equally. | Facet chips, tag groups, live count, query summary. |
| Topic-based | The user thinks in subject areas. | Topic clusters, category landing sections, semantic labels. |
| Task-based | The user arrives to complete actions. | Action lanes, workflow cards, primary task shortcuts. |
| Audience-based | Different reader groups need different paths. | Persona tabs, role cards, tailored entry points. |
| Priority/pyramid | The most important conclusion must land first. | Executive summary, ranked blocks, evidence below. |
| Comparison matrix | The user must choose between options. | Feature matrix, tradeoff columns, score rows. |
| Dashboard/status | The user monitors changing state. | KPI strip, alert lane, dense panels, drill-down affordances. |

## Selection Rules

- Use one primary model. Add a secondary model only when it solves a different
  reader task, such as hierarchical navigation plus faceted filtering.
- Match the model to the user's mental model, not to available components.
- Prefer task-based or priority/pyramid for operational pages where action
  speed matters.
- Prefer database/catalog or faceted/tagged for collections larger than one
  screen.
- Prefer sequential or chronological when order changes meaning.
- Prefer comparison matrix when the page exists to decide between alternatives.

## Prototype Controls

Expose controls that test the chosen model:

| Model Family | Useful Controls |
|---|---|
| Hierarchical / flat | Nav depth, section density, anchor placement. |
| Sequential / chronological | Step spacing, current-step emphasis, compact timeline mode. |
| Database / faceted | Filter visibility, row/card density, metadata prominence. |
| Matrix / comparison | Column count, scoring visibility, sticky headers. |
| Task / priority | Action prominence, summary size, secondary-detail visibility. |
| Dashboard/status | KPI density, alert emphasis, panel grouping. |

## Sources

- Web Style Guide, "Information Architecture":
  https://webstyleguide.com/4-information-architecture.html
- Nielsen Norman Group, "Information Architecture: Study Guide":
  https://www.nngroup.com/articles/ia-study-guide/
- UXPin, "Website Structure: A Complete Guide to the 4 Types":
  https://www.uxpin.com/studio/blog/web-structures-explained/
- Ohio State course notes, "Introduction to Information Architecture and site
  design":
  https://www.asc.ohio-state.edu/patterson.680/5140/notes.php?classID=5
