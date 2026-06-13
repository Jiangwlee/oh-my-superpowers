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
| `HTML_SERVE_BASE_URL` | recommended | User-facing URL base. Prefer a Tailscale URL for this host; fall back to `http://localhost:${HTML_SERVE_PORT:-8888}` only when no public base is configured. |

Do not hardcode personal paths, LAN IPs, or Tailscale IPs in committed skill
files. Use environment variables or document that the user must configure
their local `.env`.

## URL Policy

Generate two URLs when possible:

| URL | When to use |
|---|---|
| Public URL | Use `${HTML_SERVE_BASE_URL}` when set. On this host, configure it as the Tailscale reachable base URL. This is the preferred URL to show the user. |
| Local URL | Use `http://localhost:${HTML_SERVE_PORT:-8888}` as a fallback and service health check URL. |

Final responses should lead with the public URL. Include the localhost URL only
when `HTML_SERVE_BASE_URL` is unset, when troubleshooting, or when explicitly
useful as a secondary access path.

Local `.env` example:

```env
HTML_SERVE_DATA_DIR=/absolute/path/to/html-serve-data
HTML_SERVE_PORT=8888
HTML_SERVE_BASE_URL=http://<tailscale-host-or-ip>:8888
```

## Prototype Paths

Publish design prototypes under a namespaced project directory:

```text
$HTML_SERVE_DATA_DIR/<project>/html-design/<timestamp>-<topic>-<direction>.html
```

Recommended values:

| Token | Format |
|---|---|
| `<project>` | Current repository directory name, e.g. `oh-my-superpowers` |
| `<timestamp>` | `YYYY-MM-DDTHHMM` |
| `<topic>` | Short task slug, e.g. `daily-brief` |
| `<direction>` | Design direction slug, e.g. `editorial` |

Derive the URL from the same relative path:

```text
${HTML_SERVE_BASE_URL:-http://localhost:${HTML_SERVE_PORT:-8888}}/<project>/html-design/<filename>.html
```

When both public and local URLs are available, use the same relative path for
both bases. Do not compute a different filename or directory per access path.

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
cd docker/html-serve
docker compose ps
curl -I http://localhost:${HTML_SERVE_PORT:-8888}/
```

If it is not running, tell the user to start it:

```bash
cd docker/html-serve
docker compose up -d
```

Use localhost for service checks even when the final shared link uses
`HTML_SERVE_BASE_URL`; service checks verify the container on the current host.
