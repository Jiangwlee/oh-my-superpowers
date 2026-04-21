# Rewrite Playbook

Use this sequence when refining a skill directory.

## Pass 1: Inventory

List every Markdown file and assign its role.

Do not edit yet.

## Pass 2: Diagnose

For each file, decide:

- what structure it should use
- what expression problems it has
- what medium shifts it needs
- what content belongs elsewhere

## Pass 3: Lock invariants

Before rewriting, write down what must not change.

Typical invariants:

- workflow ordering
- branch logic
- counts and caps
- output contracts
- stop conditions
- optional vs required behavior

If a possible rewrite would improve style but change one of these, reject that rewrite.

## Pass 4: Plan the move

Before editing a file, decide:

- keep
- cut
- compress
- re-head
- table-ify
- diagram-ify
- move to another file

Also choose one rewrite mode:

- `structure + expression`
- `expression-only`

Use `expression-only` whenever the file already has a coherent structure.

## Pass 5: Rewrite

Rewrite the file in one coherent pass.

Targets:

- clear main line
- strong headings
- less prose
- stronger instruction language
- correct medium

## Positive examples

### Good refine: preserve structure, improve expression

Before:

```markdown
## Key Principles
- **One question at a time** — MUST NOT ask multiple clarifying questions in one turn.
```

After:

```markdown
## Key Principles
- **One question at a time** — Ask at most one clarifying question per turn.
```

Why it is good:

- same principle
- same behavior
- clearer language

### Good refine: convert mapping prose into a table

Before:

```markdown
- **S3** — its sole deliverable is a design doc at `docs/...`
```

After:

```markdown
| Scenario | Deliverable | Notes |
|---|---|---|
| **S3** | Design doc only | Save to `docs/...` |
```

Why it is good:

- same contract
- stronger medium for a discrete mapping

## Negative examples

### Bad refine: collapse multiple options into one

Before:

```markdown
Offer two paths for code implementation:
- Inline
- Hand off to S3
```

After:

```markdown
Offer exactly one recommendation.
```

Why it is bad:

- changes option count
- changes downstream behavior
- violates semantic preservation

### Bad refine: replace a coherent structure with a different organizing model

Before:

```markdown
## Hard Gate
## Key Principles
## Workflow
```

After:

```markdown
## Hard Gate
## File Map
## Global Rules
## Workflow
```

Why it is bad:

- changes the document's organizing model
- demotes first-class principles into a weaker bucket
- not necessary if the original structure is already coherent

## Pass 6: Directory check

After all file rewrites:

- remove duplicated guidance where possible
- align tone across files
- ensure `SKILL.md` stays the lightest entrypoint
- ensure `references/` and `assets/` carry the right load

## Pass 7: Final output

Report only:

- which Markdown files changed
- what kinds of improvements were made
- what was intentionally left alone
