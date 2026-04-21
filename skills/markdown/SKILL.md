---
name: markdown
description: >-
  Use when writing or editing any Markdown file. Helps choose document
  structure, heading hierarchy, wording strength, and the right Markdown medium
  such as lists, tables, diagrams, and tag blocks. Includes focused guidance
  for skill documents and architecture documents. Do NOT use for non-Markdown
  files, code quality work, or factual research that should happen before
  writing.
---

# Markdown

Use this skill before writing Markdown, not after the document has already drifted.

## Hard Gate

- Use this skill only for Markdown writing and editing.
- Do not use it as a substitute for domain research.
- Do not change obligation strength by accident.
- Do not change required versus optional semantics by accident.
- Do not flatten structured content into generic prose.

## Workflow

### Step 1. Pick the document type

Route the file before you write.

| If the file is mainly... | Treat it as... |
|---|---|
| a skill entrypoint or skill-side guidance | **Skill document** |
| a system, component, or design explanation | **Architecture document** |
| anything else | a general Markdown document governed by this file |

### Step 2. Pick one dominant structure

Choose the main narrative before you write headings.

| If the document is mainly... | Use this structure |
|---|---|
| step-by-step execution | **Pipeline** |
| branch selection or scenario routing | **Router** |
| stable knowledge or rules | **Reference** |
| reusable output skeleton | **Template** |
| system or component explanation | **Architecture** |
| skill entrypoint and guidance | **Skill document** |

Use these rules:

- Pick one dominant shape.
- Do not mix unrelated structures at the same heading level.
- If a file already has a coherent structure, refine it instead of inventing a new one.
- Headings should reveal logic, not act as visual decoration.

### Step 3. Organize the chapter flow

Build the chapter structure before writing paragraphs.

First identify the document's core task.

| If the document mainly needs to... | Use this organizing mode |
|---|---|
| define scope and governing boundaries | **Boundary-first** |
| tell the reader what to do | **Action-first** |
| explain a system or design | **System-first** |
| justify a decision or conclusion | **Decision-first** |
| define a rule set or protocol | **Rule-first** |
| answer a driving question | **Question-first** |

Then place content by function, not by convenience.

| Position | Function | Typical content |
|---|---|---|
| opening | orient the reader | purpose, scope, document type, reader context |
| early | front-load governing information | hard gate, principles, definitions, assumptions |
| middle | carry the main weight | workflow, mechanism, argument, design, flow |
| late | hold supporting material | exceptions, edge cases, reference map, glossary |
| ending | reinforce the closing signal | output contract, checklist, takeaway, stop condition |

Ask these questions before you commit to headings:

Answer these questions internally before you commit to headings.

Do not forward this checklist to the user as-is.

1. What is the document's core task?
2. What must the reader understand first, or the rest will misfire?
3. What information governs everything after it and therefore must be front-loaded?
4. What is the real body of the document?
5. What content is only supporting material and should be pushed back?
6. If the document could keep only five top-level sections, which five would survive?
7. Are the most important signals placed near the beginning and the end?

Use these rules:

- Keep one dominant narrative line.
- Put scope and governing constraints near the top.
- Let the middle carry most of the explanatory weight.
- Push appendices, reference maps, and glossaries out of the main line.
- End with reinforcement, not drift.

Before you continue, stop and present the proposed chapter structure to the user.

The proposal should include:

- the organizing mode
- the proposed top-level sections in order
- one short sentence explaining the narrative logic

Wait for user confirmation before moving to Step 4.

### Step 4. Choose the strongest medium

Pick the strongest Markdown medium for the information shape.

| Information shape | Preferred medium |
|---|---|
| ordered execution | numbered list |
| parallel checks or constraints | bullet list |
| discrete mappings or comparisons | table |
| branches, loops, or workflow topology | `mermaid` |
| hard boundaries or protocol blocks | tag blocks such as `<HARD-GATE>` |
| document hierarchy | headings |

Use these rules:

- Use a table when the main question is "which thing maps to which rule?"
- Use `mermaid` when the main question is "how does the path branch or loop?"
- Use a numbered list when order matters.
- Use bullets when the items are parallel and non-sequential.
- Use headings only for real hierarchy.

### Step 5. Write with contract-strength language

| Rule | Why it matters |
|---|---|
| prefer imperative | Imperative wording makes the action visible immediately. It removes weak setup phrases and increases force. |
| avoid meta-commentary | Meta-commentary explains the document instead of delivering the rule. Cutting it improves density and sharpness. |
| keep repeated sections syntactically parallel | Parallel syntax makes comparisons and repeated structure easier to scan. It also makes missing items easier to notice. |
| do not drift `must` / `should` / `may` | These words encode different obligation levels. Changing them changes the contract. |
| do not drift `required` / `optional` | These words define boundaries. If they drift, the reader no longer knows what is mandatory. |

Examples:

| Weaker | Stronger |
|---|---|
| This section is intended to help the reader understand the workflow. | Use this section to understand the workflow. |
| It may be helpful to inspect the repository first. | Inspect the repository first. |
| There should not be more than one clarifying question in one turn. | Ask at most one clarifying question per turn. |

### Step 6. Check local structure and scanability

- Use descriptive headings.
- Keep heading levels logically nested.
- Do not skip heading levels.
- Keep same-level headings semantically parallel.
- Do not use headings as a styling trick.
- If a section is optional, signal that clearly in the heading or in the surrounding contract.
- Keep the opening and ending stronger than the transitional middle.

### Step 7. Check paragraph and list quality

- Keep paragraphs short.
- Lead with the most important information.
- Introduce lists when context is needed.
- Keep list items parallel in grammar and scope.
- Do not flatten structured content into long prose paragraphs.

### Step 8. Load the scenario guide when needed

Load the relevant reference only when the file matches one of these two high-frequency types.

| Document type | Load |
|---|---|
| skill Markdown | `references/skill-doc.md` |
| architecture Markdown | `references/architecture-doc.md` |

If neither applies, use the core rules in this file directly.
