---
name: skill-refine
description: >-
  Rewrite Markdown files inside a skill directory to improve structure,
  hierarchy, clarity, concision, expressive strength, and directory-level
  consistency. Use when a skill's SKILL.md, references, scenarios, or
  Markdown assets feel structurally messy, verbose, weakly expressed, or
  inconsistent. Do NOT use for script/code fixes, spec-compliance review, or
  non-skill Markdown projects.
---

# Skill Refine

Refine the Markdown in a skill directory by rewriting files directly. This skill improves structure and expression. It does not produce a review report and it does not fix code.

## Hard Gate

<HARD-GATE>
Only change Markdown files inside the target skill directory. Do NOT change scripts, code, hooks, tests, JSON, or product behavior. Improve structure and expression without changing the intended meaning or workflow.
</HARD-GATE>

## Key Principles

- **Preserve meaning** — Rewrite for clarity and force without changing intended behavior.
- **Clarify the main line** — Every Markdown file must reveal a clear narrative or execution path.
- **Use the right medium** — Prefer tables, diagrams, lists, and tags when they express structure better than prose.
- **Keep file roles clean** — Each file should have one clear job; move overlapping content to the right file.
- **Write like SOP** — Prefer concise, accurate, forceful instructions over commentary, drift, or explanation.

## Workflow

### Step 0. Inventory the Markdown files

Scan the entire skill directory before editing anything.

| File group | Include |
|---|---|
| **Core** | `SKILL.md` |
| **References** | `references/**/*.md` |
| **Scenarios** | `scenarios/**/*.md` |
| **Assets** | Markdown templates and playbooks under `assets/**/*.md` |
| **Other Markdown** | Any additional `.md` file inside the skill directory |

Do not start with a single-file rewrite. Build the directory view first.

### Step 1. Identify file roles

Assign one primary role to each Markdown file.

| File type | Primary role |
|---|---|
| `SKILL.md` | Top-level entrypoint: trigger boundary, global guardrails, workflow skeleton, file routing |
| `references/*.md` | Detailed rules, patterns, domain knowledge, delayed-load guidance |
| `scenarios/*.md` | Branch-specific SOP |
| `assets/*.md` | Templates, skeletons, output artifacts, rewrite aids |
| Other Markdown | Only keep if it has a clear execution-facing role inside the skill |

If a file has multiple roles, split or reassign content mentally before rewriting.

### Step 2. Diagnose structure and expression

Read each file through six lenses:

| Lens | What to check |
|---|---|
| **Structure** | Is the main narrative clear? Are heading levels coherent? |
| **Expression** | Are sentences concise, accurate, and forceful? |
| **Medium choice** | Should prose become a table, Mermaid graph, list, or tag block? |
| **Information placement** | Is high-level content in the right file? Is detail buried in the wrong file? |
| **File role clarity** | Does this file stay within its job? |
| **Directory consistency** | Do neighboring Markdown files overlap, drift, or contradict each other? |

Load references as needed:

- Structure patterns → `references/structure-patterns.md`
- Expression patterns → `references/expression-patterns.md`
- Medium selection → `references/medium-selection.md`
- Directory consistency → `references/directory-consistency.md`
- Rewrite sequence → `assets/rewrite-playbook.md`

### Step 3. Choose rewrite strategy

Before editing, decide what kind of rewrite each file needs.

| Problem type | Rewrite move |
|---|---|
| No main line | Rebuild around one narrative or workflow |
| Mixed levels | Rework heading hierarchy |
| Verbose prose | Compress and harden sentences |
| Weak structure expression | Convert to table / Mermaid / list / tag block |
| Wrong file placement | Move detail to `references/` or `assets/`; keep `SKILL.md` lean |
| Repeated content across files | Keep one source of truth and delete or compress the duplicate |

Do not drift into freeform editing. Pick a rewrite move, then execute it.

### Step 4. Rewrite the files

Rewrite the Markdown directly.

- Rebuild headings around one main line per file.
- Convert weak prose into stronger structures when appropriate.
- Tighten wording until it reads like SOP, not explanation.
- Remove filler, drift, meta-commentary, and redundant restatement.
- Keep examples only when they materially improve execution.
- Keep templates out of `SKILL.md` unless they are short and always needed.

### Step 5. Check directory-level consistency

After rewriting individual files, review the skill directory as a system.

| Check | Pass condition |
|---|---|
| **Role separation** | `SKILL.md`, `references/`, `scenarios/`, and `assets/` do not compete for the same job |
| **Reference flow** | `SKILL.md` points to deeper files only when needed |
| **No structural drift** | Similar files use compatible structural logic |
| **No accidental duplication** | The same rule or template is not maintained in multiple places without reason |
| **Style coherence** | Markdown across the directory feels like one skill, not multiple authors fighting each other |

### Step 6. Report what changed

After editing, give a short summary:

- which Markdown files changed
- what improved structurally
- what improved expressively
- any intentional non-changes

Do not emit a long review report. The rewritten files are the main output.
