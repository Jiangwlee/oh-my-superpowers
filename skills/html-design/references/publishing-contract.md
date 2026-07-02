# Publishing Contract

Use html-serve as a local static preview and publishing surface for prototype
review. Keep the final HTML and `DESIGN.md` in the task workspace unless the
user asks to package them elsewhere.

## Infrastructure

Project-managed compose files live at:

```text
docker/html-serve/
├── compose.yaml
├── env.example
└── nginx.conf
```

The local `.env` file is machine-specific and must not be committed.

## Environment Variables

| Variable | Required | Meaning |
|---|---:|---|
| `HTML_SERVE_DATA_DIR` | yes | Absolute path to the static file root served by nginx. |
| `HTML_SERVE_PORT` | no | Local port. Default: `8888`. |
| `HTML_SERVE_TAILSCALE_BASE_URL` | recommended | Explicit Tailnet URL base returned as `tailscale_url`. |
| `HTML_SERVE_BASE_URL` | no | Legacy public URL base; used as a Tailscale fallback when it is not localhost. |

Do not hardcode personal paths, LAN IPs, or Tailscale IPs in committed skill
files. Use environment variables or document that the user must configure
their local `.env`.

## URL Policy

Publish through `omp html-serve publish`. The command returns two URLs every
workflow should surface:

| URL field | Meaning |
|---|---|
| `localhost_url` | Local machine URL, normally `http://localhost:${HTML_SERVE_PORT:-8888}/...`. |
| `tailscale_url` | Tailnet-reachable URL, derived from `HTML_SERVE_TAILSCALE_BASE_URL`, `HTML_SERVE_BASE_URL`, or the local Tailscale identity. |

Final responses should include both URLs. Use `localhost_url` for same-host
checks and `tailscale_url` for cross-device review.

Local `.env` example:

```env
HTML_SERVE_DATA_DIR=/absolute/path/to/html-serve-data
HTML_SERVE_PORT=8888
HTML_SERVE_TAILSCALE_BASE_URL=http://<tailscale-host-or-ip>:8888
```

## Prototype Paths

Publish design prototypes under a namespaced project directory by passing this
relative path to `omp html-serve publish`:

```text
<project>/html-design/<timestamp>-<topic>-<direction>.html
```

Recommended values:

| Token | Format |
|---|---|
| `<project>` | Current repository directory name, e.g. `oh-my-superpowers` |
| `<timestamp>` | `YYYY-MM-DDTHHMM` |
| `<topic>` | Short task slug, e.g. `daily-brief` |
| `<direction>` | Design direction slug, e.g. `editorial` |

Example publish command:

```bash
omp html-serve publish <prototype.html> --to <project>/html-design/<filename>.html --source html-design --tag prototype --tag <project>
```

Use the returned `localhost_url` and `tailscale_url`. Do not compute a different
filename or directory per access path.

## Workspace Ownership

The task workspace owns exploration artifacts:

```text
<workspace>/designs/<reference-slug>/DESIGN.md
<workspace>/prototypes/<direction>.html
<workspace>/exports/<direction>.json
<workspace>/DESIGN.md
```

If the user later wants the approved prototype packaged into another project or
skill, copy the final HTML and `DESIGN.md` there in a separate implementation
step.

## Service Check

If the browser preview fails, check the service without changing the template:

```bash
omp html-serve status
```

If it is not running, tell the user to start it:

```bash
omp html-serve start
```

Use localhost for service checks even when the final shared link uses
`tailscale_url`; service checks verify the container on the current host.
