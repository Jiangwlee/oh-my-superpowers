"""L3 semantic lint — LLM-based What/Why vs How detection.

Calls Pi via ``omp dispatch run pi`` (Claude as fallback) per project
convention. The LLM call is injected as a callable so tests can monkeypatch
without spawning a real runtime.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


# Sentinel category emitted by the LLM for "passage describes How rather than What/Why".
HOW_LEAK_CATEGORY = "how-leak"


@dataclass(frozen=True)
class SemanticFinding:
    file: Path
    line: int
    category: str
    severity: str        # CRITICAL | HIGH | MEDIUM | LOW
    snippet: str
    suggestion: str


# Type alias for the LLM caller. Tests inject a fake.
LLMCaller = Callable[[str, str | None, int], str]


# ---------------------------------------------------------------------------
# Default LLM caller — shells out to omp dispatch
# ---------------------------------------------------------------------------


def call_pi_via_dispatch(prompt: str, model: str | None, timeout: int) -> str:
    """Default LLM caller: ``omp dispatch run pi <prompt>``.

    Returns the runtime's stdout. Raises ``subprocess.CalledProcessError`` on
    non-zero exit. The caller is responsible for handling the error
    (typically by recording a Finding rather than aborting the lint run).

    Note: ``omp dispatch run`` does not expose a ``--no-session`` flag because
    headless dispatch sessions are managed internally and never persist to
    the user's session pool — this matches the project convention for Pi.
    """
    cmd = ["omp", "dispatch", "run", "pi", prompt]
    if model:
        cmd.extend(["--model", model])
    cmd.extend(["--timeout", str(timeout)])
    completed = subprocess.run(
        cmd, capture_output=True, text=True, check=True
    )
    return completed.stdout


# ---------------------------------------------------------------------------
# Prompt + parsing
# ---------------------------------------------------------------------------


_PROMPT_TEMPLATE = """\
You are a documentation auditor. The file below is a project documentation
file under a "docs-contract" regime: it must describe **What** the system
is and **Why** decisions were made. It must NOT describe **How** the code
works (function calls, control flow, step-by-step procedures, file
internals — those belong in code or commits).

Identify passages that describe How rather than What/Why. For each finding
return ONE JSON object on its own line with fields:

    {{"line": <1-based line in the body>, "category": "how-leak",
     "severity": "MEDIUM", "snippet": "<short quote, <80 chars>",
     "suggestion": "<what to do — 1 sentence>"}}

Rules:
- Output only NDJSON (one JSON object per line). No prose, no markdown fences.
- If nothing is found, output literally: NONE
- Maximum 20 findings per file. Most-egregious first.
- Do not flag links to ADRs or other doc-type files; those are What/Why.

File path: {path}
Doc-type: {doc_type}

--- BEGIN BODY ---
{body}
--- END BODY ---
"""


def build_prompt(path: Path, doc_type: str, body: str) -> str:
    return _PROMPT_TEMPLATE.format(path=path, doc_type=doc_type, body=body)


def parse_response(text: str, file: Path) -> list[SemanticFinding]:
    """Parse NDJSON LLM output into SemanticFinding list.

    Lines that fail to parse are silently skipped — robust to LLM noise
    around the JSON. The literal token ``NONE`` (case-insensitive) means
    no findings.
    """
    text = text.strip()
    if text.upper() == "NONE" or not text:
        return []

    findings: list[SemanticFinding] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        try:
            findings.append(
                SemanticFinding(
                    file=file,
                    line=int(data.get("line", 0)) or 1,
                    category=str(data.get("category", "how-leak")),
                    severity=str(data.get("severity", "MEDIUM")).upper(),
                    snippet=str(data.get("snippet", ""))[:200],
                    suggestion=str(data.get("suggestion", ""))[:300],
                )
            )
        except (TypeError, ValueError):
            continue
    return findings


# ---------------------------------------------------------------------------
# git diff helper for on-diff trigger
# ---------------------------------------------------------------------------


def changed_md_files(project_root: Path) -> set[Path] | None:
    """Return absolute paths of .md files with uncommitted changes vs HEAD.

    Uses ``git diff --name-only HEAD`` so the caller catches edits made
    between commits — matching the on-diff trigger's intent of "lint what
    the developer just touched". Returns None when git is unavailable so
    the caller can fall back to lint-all behavior.
    """
    if not (project_root / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    files: set[Path] = set()
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.endswith(".md"):
            files.add((project_root / line).resolve())
    return files


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------


_ENV_VAR_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def resolve_model(
    cli_override: str | None,
    config_model: str | None,
    env_var: str = "OMP_DEFAULT_MODEL_PI",
) -> str | None:
    """Resolve model per project convention:
    --model > config semantic_lint.model > env > None (let dispatch pick).

    Expands ``${VAR}`` placeholders inside the config value.
    """
    if cli_override:
        return cli_override
    if config_model:
        def _expand(m: re.Match[str]) -> str:
            return os.environ.get(m.group(1), m.group(0))
        return _ENV_VAR_RE.sub(_expand, config_model)
    return os.environ.get(env_var) or None
