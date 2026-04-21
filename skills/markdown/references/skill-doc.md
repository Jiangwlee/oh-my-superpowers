# Skill documents

Use this guide for Markdown inside a skill directory, especially `SKILL.md`.

## Hard Gate

- Treat the skill directory as one system, not as isolated files.
- Do not let `SKILL.md` absorb material that belongs in `references/`, `assets/`, or scenario files.
- Do not change workflow meaning, routing logic, or output contracts while "improving writing."

## File roles

| File | Role |
|---|---|
| `SKILL.md` | entrypoint, boundary, workflow skeleton, references to deeper files |
| `references/*.md` | detailed rules, patterns, domain knowledge |
| `scenarios/*.md` | branch-specific SOP |
| `assets/*.md` | templates, skeletons, example outputs |

## `SKILL.md` role

`SKILL.md` should usually contain:

- trigger boundary
- hard gate
- global principles
- workflow skeleton
- pointers to deeper files when needed

Keep `SKILL.md` lean. Move long templates, large examples, and detailed variants out of it.

## Default organizing mode

Most skill documents should use:

- **Boundary-first** to establish what the skill is, when it applies, and what must not drift
- **Action-first** to carry the operational body

This usually creates a chapter flow like:

1. what the skill is for
2. hard gate or governing rules
3. workflow
4. scenario map or reference map
5. output, stop conditions, or appendix

Do not let appendices or reference material break the main execution line.

## Structure rules

Use one dominant structure:

- **Pipeline** when the skill is a workflow
- **Router** when the skill routes into scenarios
- **Reference** only when the skill is mostly stable guidance

Do not mix:

- steps
- principles
- appendices
- special cases

at the same heading level unless they are truly peers.

If the workflow branches or loops, use `mermaid` plus step prose instead of relying on prose alone.

Before locking the headings, ask:

1. What must the reader know before they can trust the workflow?
2. Which rules govern every branch and therefore belong before the workflow?
3. What is the body versus what is only support material?
4. What should the reader remember if they only skim the opening and closing sections?

## Medium selection

| Information shape | Preferred medium |
|---|---|
| scenario routing | table |
| mode differences | table |
| workflow topology | `mermaid` |
| stop conditions | table |
| global principles | bullet list |
| output skeletons that are always needed | short inline template |

Move long templates into `assets/`.

## Wording rules

- Write like SOP.
- Use strong verbs.
- Keep contracts explicit.
- Do not drift modal strength.
- Do not change counts, output contracts, or branch semantics while editing for style.
