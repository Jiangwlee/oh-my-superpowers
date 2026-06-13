# omp serve Workbench

`omp serve` is the project-local Web workbench for Skill development. It turns the current repository into an interactive workspace for reading, previewing, editing, and generating Skills with Pi.

## Scope

Use `omp serve` when developing Skills inside the current project. It is not a general file manager, production web IDE, or multi-user collaboration server.

## Interface

The workbench has three columns:

| Area | Purpose |
|---|---|
| Left file tree | Browse the current project with lazy-loaded directories. |
| Center editor | Preview or edit files. Markdown and HTML files can be rendered directly. |
| Right assistant | Chat with a Pi Agent to inspect, generate, or modify Skill files. |

Markdown preview uses a GFM-capable renderer, so tables and common GitHub-flavored Markdown structures render in both the center preview and assistant messages.

## Session Model

Each browser page creates a new Pi session.

```text
open page A → .omp/serve/sessions/<page-a>.jsonl
open page B → .omp/serve/sessions/<page-b>.jsonl
```

Within one page, multiple prompts continue the same page-local conversation. Refreshing or opening a new page starts a fresh conversation.

The backend runs Pi as:

```bash
pi -p --mode json --approve --session .omp/serve/sessions/<page>.jsonl --model <model> <prompt>
```

`--approve` trusts project-local files for that run. The workbench displays only user and assistant turns; tool calls appear inside the assistant turn before the final assistant text.

## Commands

```text
omp serve [--workspace PATH] [--host HOST] [--port PORT] [--model MODEL] [--open/--no-open]
├── start   [--workspace PATH] [--host HOST] [--port PORT] [--model MODEL] [--open/--no-open]
├── stop    [--port PORT]
├── restart [--workspace PATH] [--host HOST] [--port PORT] [--model MODEL] [--open/--no-open]
└── dev     compatibility alias for omp serve
```

Common use:

```bash
omp serve start --workspace . --no-open
omp serve restart --workspace . --no-open
omp serve stop
```

Defaults:

| Option | Default |
|---|---|
| `--workspace` | `.` |
| `--host` | `0.0.0.0` |
| `--port` | `8765` |
| `--model` | `OMP_DEFAULT_MODEL_PI` or hardcoded fallback |
| `--open/--no-open` | `--open` |

Binding to `0.0.0.0` allows localhost, LAN, and Tailscale access.

## Implementation Notes

- Source: `cli/serve/main.py`
- Routing: `omp serve` is routed directly through the current Python executable to avoid a second `uv run` startup.
- Storage: page-local Pi sessions live under `.omp/serve/sessions/`.
- File access: API paths are resolved relative to `--workspace` and rejected if they escape the workspace.
- Tree loading: `/api/tree?path=<dir>` returns one directory level at a time.

## Verification

Before declaring `omp serve` changes complete, run:

```bash
python3 -m py_compile bin/omp cli/serve/main.py
omp serve --help
omp serve start --help
omp serve stop --help
omp serve restart --help
```

For UI changes, also verify the running page in Chrome/DevTools.
