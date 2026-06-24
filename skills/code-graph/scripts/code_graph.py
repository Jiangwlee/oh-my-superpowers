#!/usr/bin/env python3
"""Lightweight multi-project code graph for JS/TS/Python/Bash.

The script intentionally implements a small, agent-friendly subset of
codebase-memory-mcp: symbol indexing, approximate CALLS edges, snippets, and
staleness checks.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CACHE_DIR = Path(os.environ.get("OMP_CODE_GRAPH_HOME", Path.home() / ".cache" / "omp-code-graph"))
DB_PATH = CACHE_DIR / "code-graph.sqlite"
SUPPORTED_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".sh", ".bash"}
DEFAULT_SKIP_DIRS = {
    ".agents",
    ".cache",
    ".claude",
    ".codex",
    ".git",
    ".hg",
    ".memory",
    ".mypy_cache",
    ".pi",
    ".svn",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".vite",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "github",
    "node_modules",
    "tmp",
    "vendor",
}
EXTRA_SKIP_DIRS = {
    item.strip()
    for item in os.environ.get("OMP_CODE_GRAPH_EXTRA_SKIP_DIRS", "").split(",")
    if item.strip()
}
SKIP_DIRS = DEFAULT_SKIP_DIRS | EXTRA_SKIP_DIRS
CALL_STOPWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "function",
    "class",
    "new",
    "echo",
    "then",
    "do",
}


@dataclass(frozen=True)
class Node:
    kind: str
    name: str
    qname: str
    file: str
    start_line: int
    end_line: int
    signature: str = ""


@dataclass(frozen=True)
class Call:
    caller_qname: str
    callee: str
    file: str
    line: int


@dataclass(frozen=True)
class ImportRef:
    source_file: str
    module: str
    line: int


def now_iso() -> str:
    """Return current UTC timestamp."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def module_name(rel_path: str) -> str:
    """Convert a repository path into a stable module-ish name."""

    return re.sub(r"[^A-Za-z0-9_]+", ".", str(Path(rel_path).with_suffix(""))).strip(".")


def qname_for(project: str, rel_path: str, name: str, parent: str | None = None) -> str:
    """Build a qualified name."""

    parts = [project, module_name(rel_path)]
    if parent:
        parts.append(parent)
    parts.append(name)
    return ".".join(p for p in parts if p)


def db() -> sqlite3.Connection:
    """Open the graph database and ensure schema."""

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS projects (
          name TEXT PRIMARY KEY,
          root_path TEXT NOT NULL,
          indexed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS files (
          project TEXT NOT NULL,
          path TEXT NOT NULL,
          sha256 TEXT NOT NULL,
          mtime_ns INTEGER NOT NULL,
          size INTEGER NOT NULL,
          indexed_at TEXT NOT NULL,
          PRIMARY KEY(project, path)
        );
        CREATE TABLE IF NOT EXISTS nodes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project TEXT NOT NULL,
          kind TEXT NOT NULL,
          name TEXT NOT NULL,
          qname TEXT NOT NULL,
          file TEXT NOT NULL,
          start_line INTEGER NOT NULL,
          end_line INTEGER NOT NULL,
          signature TEXT DEFAULT '',
          UNIQUE(project, qname)
        );
        CREATE TABLE IF NOT EXISTS edges (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project TEXT NOT NULL,
          source_id INTEGER NOT NULL,
          target_id INTEGER NOT NULL,
          type TEXT NOT NULL,
          detail TEXT DEFAULT '',
          confidence REAL DEFAULT 0.6,
          strategy TEXT DEFAULT 'name',
          UNIQUE(project, source_id, target_id, type)
        );
        CREATE INDEX IF NOT EXISTS idx_nodes_project_name ON nodes(project, name);
        CREATE INDEX IF NOT EXISTS idx_nodes_project_kind ON nodes(project, kind);
        CREATE INDEX IF NOT EXISTS idx_edges_project_source ON edges(project, source_id, type);
        CREATE INDEX IF NOT EXISTS idx_edges_project_target ON edges(project, target_id, type);
        """
    )
    return conn


def sha256(path: Path) -> str:
    """Hash one file."""

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(root: Path) -> list[Path]:
    """Return supported source files under root."""

    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".cache")]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() in SUPPORTED_EXTS and path.is_file():
                out.append(path)
    return sorted(out)


def read_text(path: Path) -> str:
    """Read source text with forgiving decoding."""

    return path.read_text(encoding="utf-8", errors="replace")


def call_name(node: ast.AST) -> str | None:
    """Extract a Python call target name."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def parse_python(project: str, rel: str, text: str) -> tuple[list[Node], list[Call], list[ImportRef]]:
    """Parse Python with stdlib ast."""

    nodes: list[Node] = [Node("File", Path(rel).name, qname_for(project, rel, "__file__"), rel, 1, len(text.splitlines()))]
    calls: list[Call] = []
    imports: list[ImportRef] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return nodes, calls, imports

    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cls = enclosing_class(node, parents)
            args = [a.arg for a in node.args.args]
            sig = f"{node.name}({', '.join(args)})"
            nodes.append(Node("Function", node.name, qname_for(project, rel, node.name, cls), rel, node.lineno, getattr(node, "end_lineno", node.lineno), sig))
        elif isinstance(node, ast.ClassDef):
            nodes.append(Node("Class", node.name, qname_for(project, rel, node.name), rel, node.lineno, getattr(node, "end_lineno", node.lineno), f"class {node.name}"))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportRef(rel, alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            mod = "." * node.level + (node.module or "")
            imports.append(ImportRef(rel, mod, node.lineno))

    func_ranges = [n for n in nodes if n.kind == "Function"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            callee = call_name(node.func)
            caller = innermost_node(func_ranges, getattr(node, "lineno", 0))
            if callee and caller:
                calls.append(Call(caller.qname, callee, rel, node.lineno))
    return nodes, calls, imports


def enclosing_class(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str | None:
    """Find the nearest Python class parent."""

    cur = parents.get(node)
    while cur:
        if isinstance(cur, ast.ClassDef):
            return cur.name
        cur = parents.get(cur)
    return None


def innermost_node(nodes: list[Node], line: int) -> Node | None:
    """Find the smallest range containing line."""

    matches = [n for n in nodes if n.start_line <= line <= n.end_line]
    if not matches:
        return None
    return min(matches, key=lambda n: n.end_line - n.start_line)


def brace_end(lines: list[str], start_idx: int) -> int:
    """Find a JavaScript-like brace block end line."""

    depth = 0
    seen = False
    for idx in range(start_idx, len(lines)):
        raw = re.sub(r"(['\"]).*?\1", "", lines[idx])
        depth += raw.count("{")
        if raw.count("{"):
            seen = True
        depth -= raw.count("}")
        if seen and depth <= 0:
            return idx + 1
    return start_idx + 1


def parse_js_ts(project: str, rel: str, text: str) -> tuple[list[Node], list[Call], list[ImportRef]]:
    """Extract common JS/TS definitions and calls with lightweight regexes."""

    lines = text.splitlines()
    nodes: list[Node] = [Node("File", Path(rel).name, qname_for(project, rel, "__file__"), rel, 1, len(lines))]
    calls: list[Call] = []
    imports: list[ImportRef] = []
    def_patterns = [
        re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)"),
        re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>"),
        re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*async\s+function"),
        re.compile(r"^\s*(?:public|private|protected|static|async|\s)*([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*[{:]"),
    ]
    class_pat = re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)")
    import_pat = re.compile(r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]|^\s*import\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\)")

    for idx, line in enumerate(lines):
        cls = class_pat.search(line)
        if cls:
            name = cls.group(1)
            nodes.append(Node("Class", name, qname_for(project, rel, name), rel, idx + 1, brace_end(lines, idx), f"class {name}"))
        imp = import_pat.search(line)
        if imp:
            imports.append(ImportRef(rel, next(g for g in imp.groups() if g), idx + 1))
        for pat in def_patterns:
            m = pat.search(line)
            if m and m.group(1) not in CALL_STOPWORDS:
                name = m.group(1)
                nodes.append(Node("Function", name, qname_for(project, rel, name), rel, idx + 1, brace_end(lines, idx), line.strip()))
                break

    funcs = [n for n in nodes if n.kind == "Function"]
    call_pat = re.compile(r"(?:^|[^.\w$])([A-Za-z_$][\w$]*)\s*\(")
    for idx, line in enumerate(lines):
        caller = innermost_node(funcs, idx + 1)
        if not caller:
            continue
        for m in call_pat.finditer(line):
            name = m.group(1)
            if name not in CALL_STOPWORDS and name != caller.name:
                calls.append(Call(caller.qname, name, rel, idx + 1))
    return nodes, calls, imports


def parse_bash(project: str, rel: str, text: str) -> tuple[list[Node], list[Call], list[ImportRef]]:
    """Extract Bash functions and simple function calls."""

    lines = text.splitlines()
    nodes: list[Node] = [Node("File", Path(rel).name, qname_for(project, rel, "__file__"), rel, 1, len(lines))]
    calls: list[Call] = []
    imports: list[ImportRef] = []
    func_pat = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][\w-]*)\s*(?:\(\))?\s*\{")
    source_pat = re.compile(r"^\s*(?:source|\.)\s+(.+)$")
    for idx, line in enumerate(lines):
        m = func_pat.search(line)
        if m:
            name = m.group(1)
            nodes.append(Node("Function", name, qname_for(project, rel, name), rel, idx + 1, bash_end(lines, idx), line.strip()))
        sm = source_pat.search(line)
        if sm:
            imports.append(ImportRef(rel, sm.group(1).strip().strip("\"'"), idx + 1))
    funcs = [n for n in nodes if n.kind == "Function"]
    for idx, line in enumerate(lines):
        caller = innermost_node(funcs, idx + 1)
        if not caller or line.lstrip().startswith("#"):
            continue
        token = re.match(r"^\s*([A-Za-z_][\w-]*)\b", line)
        if token:
            name = token.group(1)
            if name not in CALL_STOPWORDS and name != caller.name:
                calls.append(Call(caller.qname, name, rel, idx + 1))
    return nodes, calls, imports


def bash_end(lines: list[str], start_idx: int) -> int:
    """Find a Bash function end by brace depth."""

    return brace_end(lines, start_idx)


def parse_file(project: str, root: Path, path: Path) -> tuple[list[Node], list[Call], list[ImportRef]]:
    """Parse one supported file."""

    rel = path.relative_to(root).as_posix()
    text = read_text(path)
    ext = path.suffix.lower()
    if ext == ".py":
        return parse_python(project, rel, text)
    if ext in {".js", ".jsx", ".ts", ".tsx"}:
        return parse_js_ts(project, rel, text)
    return parse_bash(project, rel, text)


def rebuild_project(conn: sqlite3.Connection, project: str, root: Path) -> dict[str, int]:
    """Rebuild one project's graph."""

    files = iter_files(root)
    conn.execute("BEGIN")
    conn.execute("DELETE FROM edges WHERE project = ?", (project,))
    conn.execute("DELETE FROM nodes WHERE project = ?", (project,))
    conn.execute("DELETE FROM files WHERE project = ?", (project,))
    conn.execute(
        "INSERT OR REPLACE INTO projects(name, root_path, indexed_at) VALUES (?, ?, ?)",
        (project, str(root), now_iso()),
    )
    all_calls: list[Call] = []
    all_imports: list[ImportRef] = []
    seen_qnames: set[str] = set()
    node_count = 0
    for path in files:
        rel = path.relative_to(root).as_posix()
        stat = path.stat()
        nodes, calls, imports = parse_file(project, root, path)
        all_calls.extend(calls)
        all_imports.extend(imports)
        conn.execute(
            "INSERT INTO files(project, path, sha256, mtime_ns, size, indexed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (project, rel, sha256(path), stat.st_mtime_ns, stat.st_size, now_iso()),
        )
        for n in nodes:
            if n.qname in seen_qnames:
                continue
            seen_qnames.add(n.qname)
            conn.execute(
                """
                INSERT INTO nodes(project, kind, name, qname, file, start_line, end_line, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (project, n.kind, n.name, n.qname, n.file, n.start_line, n.end_line, n.signature),
            )
            node_count += 1
    create_edges(conn, project, all_calls, all_imports)
    conn.commit()
    edge_count = conn.execute("SELECT COUNT(*) FROM edges WHERE project = ?", (project,)).fetchone()[0]
    return {"files": len(files), "nodes": node_count, "edges": edge_count}


def create_edges(conn: sqlite3.Connection, project: str, calls: list[Call], imports: list[ImportRef]) -> None:
    """Resolve approximate imports and calls into graph edges."""

    by_qname = {r["qname"]: r for r in conn.execute("SELECT * FROM nodes WHERE project = ?", (project,))}
    by_name: dict[str, list[sqlite3.Row]] = {}
    for row in by_qname.values():
        by_name.setdefault(row["name"], []).append(row)
    for imp in imports:
        source = by_qname.get(qname_for(project, imp.source_file, "__file__"))
        target = find_import_target(project, by_qname, imp.module)
        if source and target:
            insert_edge(conn, project, source["id"], target["id"], "IMPORTS", imp.module, 0.5, "module_name")
    for call in calls:
        source = by_qname.get(call.caller_qname)
        if not source:
            continue
        target = resolve_call_target(by_name, call.callee, source["file"])
        if target and target["id"] != source["id"]:
            strategy = "same_file" if target["file"] == source["file"] else "unique_name"
            confidence = 0.8 if strategy == "same_file" else 0.6
            insert_edge(conn, project, source["id"], target["id"], "CALLS", f"{call.callee}@{call.line}", confidence, strategy)


def find_import_target(project: str, by_qname: dict[str, sqlite3.Row], module: str) -> sqlite3.Row | None:
    """Find a File node for an import-like module name."""

    suffix = re.sub(r"[^A-Za-z0-9_]+", ".", module).strip(".")
    for qname, row in by_qname.items():
        if row["kind"] == "File" and (qname.endswith(f".{suffix}.__file__") or qname == f"{project}.{suffix}.__file__"):
            return row
    return None


def resolve_call_target(by_name: dict[str, list[sqlite3.Row]], name: str, file: str) -> sqlite3.Row | None:
    """Resolve a call by local/same-file/unique-name heuristic."""

    candidates = [r for r in by_name.get(name, []) if r["kind"] == "Function"]
    same_file = [r for r in candidates if r["file"] == file]
    if same_file:
        return same_file[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def insert_edge(conn: sqlite3.Connection, project: str, source: int, target: int, typ: str, detail: str, confidence: float, strategy: str) -> None:
    """Insert one edge, ignoring duplicates."""

    conn.execute(
        """
        INSERT OR IGNORE INTO edges(project, source_id, target_id, type, detail, confidence, strategy)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (project, source, target, typ, detail, confidence, strategy),
    )


def project_from_path(path: Path) -> str:
    """Default project name."""

    return path.resolve().name


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert sqlite row to dict."""

    return {k: row[k] for k in row.keys()}


def print_json(data: Any) -> None:
    """Print JSON output."""

    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_index(args: argparse.Namespace) -> None:
    """Handle index."""

    root = Path(args.repo).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"repo path does not exist or is not a directory: {root}")
    project = args.project or project_from_path(root)
    with db() as conn:
        stats = rebuild_project(conn, project, root)
    print_json({"status": "indexed", "project": project, "root": str(root), **stats})


def cmd_projects(args: argparse.Namespace) -> None:
    """Handle projects."""

    with db() as conn:
        rows = [
            {
                **row_to_dict(row),
                "files": conn.execute("SELECT COUNT(*) FROM files WHERE project = ?", (row["name"],)).fetchone()[0],
                "nodes": conn.execute("SELECT COUNT(*) FROM nodes WHERE project = ?", (row["name"],)).fetchone()[0],
                "edges": conn.execute("SELECT COUNT(*) FROM edges WHERE project = ?", (row["name"],)).fetchone()[0],
            }
            for row in conn.execute("SELECT * FROM projects ORDER BY name")
        ]
    if args.json:
        print_json({"projects": rows})
    else:
        for row in rows:
            print(f"{row['name']}\tfiles={row['files']}\tnodes={row['nodes']}\tedges={row['edges']}\troot={row['root_path']}")


def changed_since_index(conn: sqlite3.Connection, project: str) -> dict[str, Any]:
    """Compute basic freshness status."""

    pr = conn.execute("SELECT * FROM projects WHERE name = ?", (project,)).fetchone()
    if not pr:
        raise SystemExit(f"project not indexed: {project}")
    root = Path(pr["root_path"])
    current = {p.relative_to(root).as_posix(): p for p in iter_files(root)}
    indexed = {r["path"]: r for r in conn.execute("SELECT * FROM files WHERE project = ?", (project,))}
    changed = 0
    for rel, path in current.items():
        row = indexed.get(rel)
        if not row:
            changed += 1
            continue
        st = path.stat()
        if st.st_size != row["size"] or st.st_mtime_ns != row["mtime_ns"]:
            changed += 1
    deleted = len(set(indexed) - set(current))
    added = len(set(current) - set(indexed))
    return {"project": project, "root_path": str(root), "indexed_at": pr["indexed_at"], "files": len(indexed), "added": added, "changed": changed, "deleted": deleted, "stale": bool(added or changed or deleted)}


def cmd_status(args: argparse.Namespace) -> None:
    """Handle status."""

    with db() as conn:
        data = changed_since_index(conn, args.project)
    if args.json:
        print_json(data)
    else:
        print(f"project: {data['project']}")
        print(f"root: {data['root_path']}")
        print(f"indexed_at: {data['indexed_at']}")
        print(f"files: {data['files']}")
        print(f"added={data['added']} changed={data['changed']} deleted={data['deleted']} stale={str(data['stale']).lower()}")


def cmd_search(args: argparse.Namespace) -> None:
    """Handle search."""

    params: list[Any] = []
    where = ["name LIKE ?"]
    params.append(f"%{args.query}%")
    if args.project:
        where.append("project = ?")
        params.append(args.project)
    if args.kind:
        where.append("kind = ?")
        params.append(args.kind)
    sql = f"""
      SELECT n.*,
        (SELECT COUNT(*) FROM edges e WHERE e.target_id = n.id AND e.type='CALLS') AS in_degree,
        (SELECT COUNT(*) FROM edges e WHERE e.source_id = n.id AND e.type='CALLS') AS out_degree
      FROM nodes n WHERE {' AND '.join(where)}
      ORDER BY kind, name LIMIT ?
    """
    params.append(args.limit)
    with db() as conn:
        rows = [row_to_dict(r) for r in conn.execute(sql, params)]
    emit_rows(rows, args.json)


def resolve_symbol(conn: sqlite3.Connection, project: str, symbol: str) -> sqlite3.Row:
    """Resolve a qname or short symbol name."""

    row = conn.execute("SELECT * FROM nodes WHERE project = ? AND qname = ?", (project, symbol)).fetchone()
    if row:
        return row
    rows = list(conn.execute("SELECT * FROM nodes WHERE project = ? AND name = ? AND kind='Function'", (project, symbol)))
    if len(rows) == 1:
        return rows[0]
    if not rows:
        raise SystemExit(f"symbol not found: {symbol}")
    names = "\n".join(r["qname"] for r in rows[:20])
    raise SystemExit(f"ambiguous symbol, use qname:\n{names}")


def cmd_trace(args: argparse.Namespace, inbound: bool) -> None:
    """Handle callers/callees."""

    with db() as conn:
        root = resolve_symbol(conn, args.project, args.symbol)
        if inbound:
            sql = """
              SELECT s.*, e.confidence, e.strategy, e.detail FROM edges e
              JOIN nodes s ON s.id = e.source_id
              WHERE e.project = ? AND e.target_id = ? AND e.type='CALLS'
              ORDER BY s.file, s.start_line LIMIT ?
            """
        else:
            sql = """
              SELECT t.*, e.confidence, e.strategy, e.detail FROM edges e
              JOIN nodes t ON t.id = e.target_id
              WHERE e.project = ? AND e.source_id = ? AND e.type='CALLS'
              ORDER BY t.file, t.start_line LIMIT ?
            """
        rows = [row_to_dict(r) for r in conn.execute(sql, (args.project, root["id"], args.limit))]
    emit_rows(rows, args.json)


def cmd_snippet(args: argparse.Namespace) -> None:
    """Handle snippet."""

    with db() as conn:
        node = resolve_symbol(conn, args.project, args.qname)
        pr = conn.execute("SELECT root_path FROM projects WHERE name = ?", (args.project,)).fetchone()
    root = Path(pr["root_path"])
    lines = read_text(root / node["file"]).splitlines()
    start = max(1, node["start_line"] - args.context)
    end = min(len(lines), node["end_line"] + args.context)
    code = "\n".join(lines[start - 1 : end])
    data = {**row_to_dict(node), "snippet_start": start, "snippet_end": end, "code": code}
    if args.json:
        print_json(data)
    else:
        print(f"{node['qname']} {node['file']}:{start}-{end}")
        print(code)


def emit_rows(rows: list[dict[str, Any]], json_output: bool) -> None:
    """Emit row list."""

    if json_output:
        print_json({"results": rows, "count": len(rows)})
        return
    for r in rows:
        degree = ""
        if "in_degree" in r:
            degree = f" in={r['in_degree']} out={r['out_degree']}"
        print(f"{r['kind']}\t{r['name']}\t{r['qname']}\t{r['file']}:{r['start_line']}-{r['end_line']}{degree}")


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""

    p = argparse.ArgumentParser(prog="code_graph.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    ix = sub.add_parser("index")
    ix.add_argument("repo")
    ix.add_argument("--project")
    ix.set_defaults(func=cmd_index)
    pr = sub.add_parser("projects")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_projects)
    st = sub.add_parser("status")
    st.add_argument("--project", required=True)
    st.add_argument("--json", action="store_true")
    st.set_defaults(func=cmd_status)
    se = sub.add_parser("search")
    se.add_argument("query")
    se.add_argument("--project")
    se.add_argument("--kind")
    se.add_argument("--limit", type=int, default=20)
    se.add_argument("--json", action="store_true")
    se.set_defaults(func=cmd_search)
    ca = sub.add_parser("callers")
    ca.add_argument("symbol")
    ca.add_argument("--project", required=True)
    ca.add_argument("--limit", type=int, default=50)
    ca.add_argument("--json", action="store_true")
    ca.set_defaults(func=lambda a: cmd_trace(a, True))
    ce = sub.add_parser("callees")
    ce.add_argument("symbol")
    ce.add_argument("--project", required=True)
    ce.add_argument("--limit", type=int, default=50)
    ce.add_argument("--json", action="store_true")
    ce.set_defaults(func=lambda a: cmd_trace(a, False))
    sn = sub.add_parser("snippet")
    sn.add_argument("qname")
    sn.add_argument("--project", required=True)
    sn.add_argument("--context", type=int, default=0)
    sn.add_argument("--json", action="store_true")
    sn.set_defaults(func=cmd_snippet)
    return p


def main() -> None:
    """Entrypoint."""

    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
