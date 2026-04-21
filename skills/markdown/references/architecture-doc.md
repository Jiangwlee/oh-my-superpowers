# Architecture documents

Use this guide for Markdown that explains a system, component set, or technical design.

## Hard Gate

An architecture document should help the reader answer:

1. what exists
2. how the parts relate
3. how control or data flows
4. what decisions or trade-offs matter

Do not mix architecture explanation with implementation trivia unless the document is explicitly about implementation design.

## Recommended sections

Use only the sections that fit the document, but keep the structure predictable.

| Section | Purpose |
|---|---|
| Overview | What system this document explains |
| Components | The main pieces and their responsibilities |
| Flows | Data flow, control flow, or lifecycle flow |
| Interfaces | Public contracts, boundaries, inputs, outputs |
| Decisions / trade-offs | Why the design looks this way |
| Risks / constraints | Known limits, assumptions, sharp edges |

## Default organizing mode

Most architecture documents should use:

- **System-first** when the main job is to explain what exists and how it works
- **Decision-first** when the main job is to justify a specific design choice

Use `System-first` by default. Switch emphasis only when the document is mainly trying to win agreement on a decision.

Typical chapter flow for `System-first`:

1. overview
2. components
3. flows
4. interfaces
5. decisions or trade-offs
6. risks or constraints

Typical chapter flow for `Decision-first`:

1. decision
2. rationale
3. system impact
4. trade-offs
5. risks or follow-up

## Medium selection

| Information shape | Preferred medium |
|---|---|
| system topology | `mermaid` diagram |
| component responsibilities | table |
| request / event / lifecycle flow | `mermaid` or numbered sequence |
| interface details | table |
| decisions and trade-offs | bullet list or short subsections |

Use `mermaid` when the relationship or flow matters more than narrative prose.

## Wording rules

- Prefer precise nouns and verbs over abstract buzzwords.
- State responsibility directly: `The scheduler owns retry state.`
- Separate fact from decision: what exists vs why it exists.
- Use parallel phrasing when comparing components or options.
- Avoid vague filler like `robust`, `flexible`, or `powerful` unless you explain what they mean in this system.

## Common failure modes

- Too much concept prose, not enough structure
- Components named without responsibilities
- A flow described only in paragraphs when a diagram would be clearer
- Trade-offs implied but not stated
- Mixing implementation trivia with top-level architecture
