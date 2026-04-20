# Directory Consistency

Refine the skill directory as a system, not as isolated files.

## Role separation

Each Markdown zone should do one job well.

| Location | Job |
|---|---|
| `SKILL.md` | Entry, boundary, top-level workflow |
| `references/` | Detailed rules and delayed-load material |
| `scenarios/` | Branch-specific SOP |
| `assets/` | Templates and output skeletons |

If two files try to do the same job, the directory will drift.

## Common directory-level failures

### 1. `SKILL.md` is too heavy

Symptoms:

- long templates inline
- too much explanation
- deep details that belong in references

Fix:

- keep the top-level file lean
- move detail down

### 2. References duplicate the homepage

Symptoms:

- `SKILL.md` and `references/*.md` restate the same rules

Fix:

- keep one source of truth
- let `SKILL.md` point to deeper material instead of repeating it

### 3. Templates pollute structure

Symptoms:

- the heading tree is dominated by template placeholders

Fix:

- move large templates into `assets/`
- keep only short always-needed output structure inline

### 4. Scenario files and `SKILL.md` both explain the same workflow

Fix:

- let `SKILL.md` own the top-level workflow
- let scenario files own branch-specific detail

## Final check

After rewriting, ask:

- Does each file have one obvious job?
- Does `SKILL.md` feel like an entrypoint?
- Do deeper files feel like support, not competition?
- If I removed any one Markdown file, would I clearly know what role is missing?
