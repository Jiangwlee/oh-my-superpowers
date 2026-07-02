// Workspace filesystem access with path-escape guards. Ported 1:1 from
// main.py (_is_safe, _resolve_rel, _list_directory, _read_text_file).
import { readdirSync, statSync, lstatSync, readFileSync, realpathSync } from "node:fs";
import { resolve, join, sep } from "node:path";

export const DEFAULT_IGNORES = new Set<string>([
  ".agents",
  ".claude",
  ".git",
  ".hg",
  ".omp",
  ".pi",
  ".svn",
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  ".venv",
  "__pycache__",
  "node_modules",
  "dist",
  "build",
  ".next",
]);

export const TEXT_EXTENSIONS = new Set<string>([
  ".css", ".csv", ".html", ".htm", ".js", ".json", ".jsonl", ".jsx",
  ".md", ".mdx", ".py", ".sh", ".toml", ".ts", ".tsx", ".txt", ".yaml", ".yml",
]);

// Resolve a path through symlinks if it exists; otherwise resolve lexically.
// Mirrors Path.resolve() semantics used by _is_safe in main.py.
function canonical(p: string): string {
  try {
    return realpathSync(p);
  } catch {
    return resolve(p);
  }
}

// _is_safe: target must equal root or be nested under root.
export function isSafe(root: string, target: string): boolean {
  const r = canonical(root);
  const t = canonical(target);
  if (t === r) return true;
  return t.startsWith(r.endsWith(sep) ? r : r + sep);
}

// _resolve_rel: join workspace + rel, reject escapes. Mirrors Python
// _resolve_rel which returns (workspace / rel).resolve() — the canonical real
// path. Returning the canonical target (not the lexical one) closes a symlink
// swap race: callers open the already-resolved path, so a symlink swapped
// after the safety check cannot redirect reads/writes outside the workspace.
export function resolveRel(workspace: string, relPath: string): string {
  const lexical = resolve(join(workspace, relPath));
  if (!isSafe(workspace, lexical)) throw new Error("path escapes workspace");
  return canonical(lexical);
}

export function isVisibleEntry(name: string): boolean {
  return !DEFAULT_IGNORES.has(name) && !name.startsWith(".");
}

function hasVisibleChild(directory: string): boolean {
  try {
    return readdirSync(directory).some(isVisibleEntry);
  } catch {
    return false;
  }
}

export interface TreeNode {
  type: "directory" | "file";
  name: string;
  path: string;
  hasChildren: boolean;
}

function extOf(name: string): string {
  const i = name.lastIndexOf(".");
  return i === -1 ? "" : name.slice(i).toLowerCase();
}

export function listDirectory(workspace: string, relPath: string): TreeNode[] {
  const directory = resolve(join(workspace, relPath));
  if (!isSafe(workspace, directory)) throw new Error("path escapes workspace");
  let st;
  try {
    st = statSync(directory);
  } catch {
    throw new Error("directory not found");
  }
  if (!st.isDirectory()) throw new Error("directory not found");

  let names: string[];
  try {
    names = readdirSync(directory);
  } catch {
    return [];
  }

  type Entry = { name: string; isDir: boolean; isFile: boolean };
  const entries: Entry[] = [];
  for (const name of names) {
    const full = join(directory, name);
    // lstat (no symlink follow) so a symlink's external target can never
    // classify the entry as a directory and trigger readdir outside the
    // workspace. Symlinks whose resolved target escapes the workspace are
    // skipped entirely (path-escape/symlink-escape redline guard).
    let lst;
    try {
      lst = lstatSync(full);
    } catch {
      continue;
    }
    if (lst.isSymbolicLink()) {
      if (!isSafe(workspace, full)) continue; // resolves outside workspace
      // Safe symlink: classify by its (in-workspace) target via stat.
      let est;
      try {
        est = statSync(full);
      } catch {
        continue;
      }
      entries.push({ name, isDir: est.isDirectory(), isFile: est.isFile() });
      continue;
    }
    entries.push({ name, isDir: lst.isDirectory(), isFile: lst.isFile() });
  }
  // Sort: directories first, then case-insensitive name.
  entries.sort((a, b) => {
    if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
    return a.name.toLowerCase() < b.name.toLowerCase() ? -1 : a.name.toLowerCase() > b.name.toLowerCase() ? 1 : 0;
  });

  const nodes: TreeNode[] = [];
  for (const entry of entries) {
    if (!isVisibleEntry(entry.name)) continue;
    const rel = relPath ? `${relPath}/${entry.name}` : entry.name;
    if (entry.isDir) {
      nodes.push({ type: "directory", name: entry.name, path: rel, hasChildren: hasVisibleChild(join(directory, entry.name)) });
    } else if (entry.isFile) {
      nodes.push({ type: "file", name: entry.name, path: rel, hasChildren: false });
    }
  }
  return nodes;
}

// List immediate subdirectories of absDir, constrained to `root` (the browse
// sandbox, e.g. $HOME). Hidden and conventionally-ignored dirs are filtered.
// lstat (no follow) skips symlinked directories so a symlink cannot redirect
// the picker outside the sandbox. Used by the "+ add project" directory picker.
export function listSubdirectories(root: string, absDir: string): { name: string; path: string }[] {
  if (!isSafe(root, absDir)) throw new Error("path escapes sandbox");
  let names: string[];
  try {
    names = readdirSync(absDir);
  } catch {
    return [];
  }
  const dirs: { name: string; path: string }[] = [];
  for (const name of names) {
    if (name.startsWith(".") || DEFAULT_IGNORES.has(name)) continue;
    const full = join(absDir, name);
    try {
      if (!lstatSync(full).isDirectory()) continue;
    } catch {
      continue;
    }
    if (!isSafe(root, full)) continue;
    dirs.push({ name, path: full });
  }
  dirs.sort((a, b) =>
    a.name.toLowerCase() < b.name.toLowerCase() ? -1 : a.name.toLowerCase() > b.name.toLowerCase() ? 1 : 0,
  );
  return dirs;
}

function looksBinary(data: Buffer): boolean {
  const slice = data.subarray(0, 8192);
  return slice.includes(0);
}

export function readTextFile(absPath: string): string {
  const ext = extOf(absPath);
  if (!TEXT_EXTENSIONS.has(ext)) {
    const data = readFileSync(absPath);
    if (looksBinary(data)) throw new Error("binary preview is not supported");
    return data.toString("utf-8");
  }
  return readFileSync(absPath, "utf-8");
}
