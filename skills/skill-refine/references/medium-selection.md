# Medium Selection

Use the strongest Markdown medium for the information shape.

## Selection rules

| Information shape | Preferred medium |
|---|---|
| Paths, loops, branch topology | `mermaid` |
| Finite mappings, decision matrices, scenario/output maps | table |
| Strict sequence | ordered list |
| Parallel points, checks, constraints | unordered list |
| Main narrative hierarchy | heading levels |
| Hard boundaries, protocol blocks, required wrappers | XML / Markdown tag blocks |

## Examples

### Use Mermaid when the problem is topology

Good for:

- branch points
- retries
- escalation
- downgrade / upgrade paths
- scenario routing

Do not use prose when the main problem is "how the path branches."

### Use tables when the problem is discrete mapping

Good for:

- scenario -> deliverable
- mode -> behavior
- condition -> response
- file type -> role
- question type -> rule

Do not use prose when the main problem is "which bucket maps to which rule."

### Use lists when the problem is order or parallelism

Use ordered lists for:

- step-by-step execution

Use unordered lists for:

- checks
- constraints
- examples
- grouped observations

## Anti-pattern

Do not flatten everything into paragraphs.

If the information already has a shape, expose that shape directly.
