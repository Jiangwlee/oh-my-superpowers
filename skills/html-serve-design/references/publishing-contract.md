# Publishing Contract

Use html-serve only as a local static preview and publishing surface. This
skill designs templates for other skills; it does not become their runtime
publisher.

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
$HTML_SERVE_DATA_DIR/<project>/html-serve-design/<timestamp>-<target-skill>-<topic>.html
```

Recommended values:

| Token | Format |
|---|---|
| `<project>` | Current repository directory name, e.g. `oh-my-superpowers` |
| `<timestamp>` | `YYYY-MM-DDTHHMM` |
| `<target-skill>` | Target skill name, e.g. `deep-research` |
| `<topic>` | Short slug, e.g. `final-report` |

Derive the URL from the same relative path:

```text
${HTML_SERVE_BASE_URL:-http://localhost:${HTML_SERVE_PORT:-8888}}/<project>/html-serve-design/<filename>.html
```

When both public and local URLs are available, use the same relative path for
both bases. Do not compute a different filename or directory per access path.

## Runtime Ownership

After approval, copy the final template into the target skill:

```text
skills/<target-skill>/assets/<template-name>.html
```

Then document target-skill runtime behavior in that target skill's own
references. The target skill should write its normal outputs and, when
configured, publish a generated HTML page to html-serve.

Do not make the target skill read files from `skills/html-serve-design/` during
normal execution.

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
