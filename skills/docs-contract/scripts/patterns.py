"""L2 lint patterns.

Each label maps to a deterministic detector that returns a list of
(line_number, snippet, hint) tuples for matches found in the document body.

Detectors operate on the markdown body string after frontmatter has been
stripped. They are intentionally heuristic; false positives are mitigated
by inline exemptions documented in references/lint-rules.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Match:
    line: int        # 1-based line number within the body
    snippet: str     # the matched substring (trimmed)
    hint: str        # short rule explanation for the report


# ---------------------------------------------------------------------------
# function-name
# ---------------------------------------------------------------------------

# Heuristic: foo(), Foo.bar(), module.func(), snake_case_name(), etc.
_FUNCTION_CALL_RE = re.compile(
    r"(?<![\w./-])"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*"   # base identifier
    r"(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"     # optional .attr chains
    r"\(\s*\)?"                            # opening paren (allow empty args)
)

# Words that are common English prose and should not be treated as code-like
_FUNCTION_CALL_DENYLIST: frozenset[str] = frozenset(
    {"e.g", "i.e", "etc", "fig", "vs"}
)


def detect_function_name(body: str) -> list[Match]:
    matches: list[Match] = []
    for line_no, line in _iter_lines(body):
        for m in _FUNCTION_CALL_RE.finditer(line):
            name = m.group("name")
            if name.lower() in _FUNCTION_CALL_DENYLIST:
                continue
            matches.append(
                Match(
                    line=line_no,
                    snippet=name + "()",
                    hint="looks like a function call (move to code or PR description)",
                )
            )
    return matches


# ---------------------------------------------------------------------------
# file-path
# ---------------------------------------------------------------------------

_FILE_PATH_RES: tuple[re.Pattern[str], ...] = (
    # absolute or relative path with at least one slash and a known extension
    re.compile(
        r"(?<![\w/])"
        r"(?:\.{1,2}/|/|src/|lib/|app/|cli/|scripts/|tests?/)"
        r"[\w\-./]+?"
        r"\.(?:py|ts|tsx|js|jsx|mjs|cjs|json|yaml|yml|toml|sh|md|sql|proto|rs|go|java|kt|swift|cpp|c|h|hpp)"
        r"(?::\d+)?"
        r"(?![\w])"
    ),
    # Windows-style src\foo\bar.py style
    re.compile(
        r"(?<![\w\\])"
        r"[A-Za-z]:?\\(?:[\w\-]+\\)+[\w\-]+\.[A-Za-z]{1,5}"
    ),
)


def detect_file_path(body: str) -> list[Match]:
    matches: list[Match] = []
    for line_no, line in _iter_lines(body):
        for pattern in _FILE_PATH_RES:
            for m in pattern.finditer(line):
                matches.append(
                    Match(
                        line=line_no,
                        snippet=m.group(0),
                        hint="file path leaks implementation detail",
                    )
                )
    return matches


# ---------------------------------------------------------------------------
# code-block
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*```")


def detect_code_block(body: str) -> list[Match]:
    matches: list[Match] = []
    in_block = False
    block_start = 0
    for line_no, line in _iter_lines(body):
        if _FENCE_RE.match(line):
            if not in_block:
                in_block = True
                block_start = line_no
            else:
                matches.append(
                    Match(
                        line=block_start,
                        snippet=f"fenced code block (lines {block_start}-{line_no})",
                        hint="code blocks belong in implementation, not What/Why docs",
                    )
                )
                in_block = False
    return matches


# ---------------------------------------------------------------------------
# step-verb
# ---------------------------------------------------------------------------

_STEP_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Allow Chinese comma between 先 and 再 — "先 X，再 Y" is the canonical form.
    re.compile(r"先[^。\n]{1,40}再[^。\n]{1,40}"),
    re.compile(r"^\s*(?:步骤|step)\s*\d+[:：]", re.IGNORECASE),
    re.compile(r"\bthen\b[^.\n]{1,40}\bnext\b", re.IGNORECASE),
    re.compile(r"^\s*\d+\.\s*(?:然后|下一步|接着)"),
)


def detect_step_verb(body: str) -> list[Match]:
    matches: list[Match] = []
    for line_no, line in _iter_lines(body):
        for pattern in _STEP_PATTERNS:
            m = pattern.search(line)
            if m:
                matches.append(
                    Match(
                        line=line_no,
                        snippet=m.group(0).strip(),
                        hint="procedural step belongs in code or procedures/",
                    )
                )
                break
    return matches


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


DETECTORS: dict[str, Callable[[str], list[Match]]] = {
    "function-name": detect_function_name,
    "file-path": detect_file_path,
    "code-block": detect_code_block,
    "step-verb": detect_step_verb,
}


def known_labels() -> tuple[str, ...]:
    return tuple(DETECTORS.keys())


# ---------------------------------------------------------------------------
# Inline exemptions
# ---------------------------------------------------------------------------

_EXEMPTION_RE = re.compile(
    r"<!--\s*docs-contract:\s*allow-([\w-]+)\s*-->",
)


@dataclass(frozen=True)
class ExemptionRange:
    label: str
    start_line: int           # 1-based, line of the comment
    end_line: int             # 1-based inclusive; defaults to next blank line


def parse_exemptions(body: str) -> list[ExemptionRange]:
    """Find inline exemption markers; each scope extends to the next blank line.

    Line numbers in the returned ranges are 1-based. A blank line ends the
    exemption (the blank line itself is included in the range). If the
    comment has no blank line after it, the scope extends to the last line.
    """
    lines = body.splitlines()
    ranges: list[ExemptionRange] = []
    for idx, line in enumerate(lines):
        for m in _EXEMPTION_RE.finditer(line):
            label = m.group(1)
            end_1based = len(lines)
            for j in range(idx + 1, len(lines)):
                if not lines[j].strip():
                    end_1based = j + 1
                    break
            ranges.append(
                ExemptionRange(
                    label=label, start_line=idx + 1, end_line=end_1based
                )
            )
    return ranges


def is_exempt(label: str, line_no: int, exemptions: list[ExemptionRange]) -> bool:
    for ex in exemptions:
        if ex.label != label:
            continue
        if ex.start_line <= line_no <= ex.end_line:
            return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iter_lines(body: str):
    for i, line in enumerate(body.splitlines(), start=1):
        yield i, line
