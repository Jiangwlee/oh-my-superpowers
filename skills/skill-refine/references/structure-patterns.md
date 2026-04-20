# Structure Patterns

Choose one dominant structure per Markdown file. Do not mix unrelated structures at the same level.

## Common primary patterns

| Pattern | Use when | Typical shape |
|---|---|---|
| **Pipeline** | The file describes ordered execution | intro -> steps -> outputs / stop conditions |
| **Router** | The file routes into branches | route table -> handoff map |
| **Reviewer** | The file evaluates against criteria | dimensions -> checks -> severity / decision |
| **Reference index** | The file helps load deeper material | what each file is for -> when to read it |
| **Template** | The file is copied or filled in | headings / placeholders / format rules |

## Rules

### 1. Pick one main line

Every file should make one structure dominant.

Bad:

- pipeline + manifesto + appendix all fighting for top-level space

Good:

- one main line, with supporting sections attached to it

### 2. Keep heading levels semantically clean

The same heading level should represent the same kind of thing.

Good examples:

- all top-level headings are workflow blocks
- all subheadings are steps
- all peer headings are output sections

Bad examples:

- one top-level heading is a step
- another is a principle set
- another is an exception appendix

### 3. Keep the homepage lean

For `SKILL.md`, keep only:

- trigger boundary
- hard gate
- global principles
- workflow skeleton
- references to deeper files when needed

Move detailed variants, templates, and long examples out of `SKILL.md`.

### 4. Make roles visible in the structure

The heading tree should tell the reader what the file is trying to do.

If a file is a pipeline, it should look like a pipeline.
If a file is a template, it should look like a template.
If a file is a reference index, it should look like a reference index.
