---
name: code-graph
description: >-
  Use when an agent needs lightweight structural navigation of a local codebase:
  index JS/TS/Python/Bash projects, find symbols, inspect callers/callees,
  retrieve snippets, and check whether an index is stale.
  Do NOT use as a precise LSP replacement or for languages outside the MVP scope.
---

# code-graph

Build and query an agent-friendly project map for Linux repositories containing JavaScript, TypeScript, Python, or Bash.

## Workflow

1. Check existing indexes:

```bash
omp code-graph projects
```

2. Index the project when missing or stale:

```bash
omp code-graph index <repo-path> --project <name>
```

The indexer skips common dependency/build/local-reference/runtime directories by default, including `.git`, `.next`, `.claude`, `.agents`, `.pi`, `.memory`, `.codex`, `node_modules`, `dist`, `build`, `coverage`, `vendor`, and `github`. Add project-specific directory names with:

```bash
OMP_CODE_GRAPH_EXTRA_SKIP_DIRS=scratch,tmp-worktree omp code-graph index <repo-path> --project <name>
```

3. Use structured commands before broad grep/read:

```bash
omp code-graph search "auth" --project <name>
omp code-graph callers "loginUser" --project <name>
omp code-graph callees "handleLogin" --project <name>
omp code-graph snippet "<qualified_name>" --project <name>
```

4. Treat results as navigation hints. Read snippets before making claims about behavior.

## Boundaries

- MVP parser: syntax-level extraction, no LSP/type inference.
- CALLS edges are approximate for dynamic dispatch, framework magic, dependency injection, aliases, and same-name functions.
- No vector search, external embedding integration, or code question-answering in this MVP.

## CLI

Run `omp code-graph --help` and individual command `--help` for current arguments.
