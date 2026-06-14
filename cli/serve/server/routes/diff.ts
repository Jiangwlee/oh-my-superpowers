// GET /api/diff -> git working-tree changes for the diff panel.
// Returns per-file {path, status, added, deleted, mtimeMs, hunks} for tracked
// changes (vs HEAD, staged + unstaged combined) plus untracked files as adds.
//
// Redline compliance:
//  - execFile with a fixed arg array, NO shell, cwd = workspace (no user path
//    is ever interpolated into a git argument).
//  - the diff is scoped to the workspace subtree (`--relative` + `-- .`) so a
//    workspace nested inside a larger repo never leaks outside changes.
//  - file mtime is read through resolveRel so a reported path cannot escape the
//    workspace.
//  - git runs asynchronously so a large diff never blocks chat/terminal I/O on
//    the single server process; untracked work is bounded.
import type { ServerResponse } from "node:http";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { statSync, lstatSync, readFileSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import type { ProjectContext } from "../config.js";
import { sendJson } from "../sse.js";
import { resolveRel, isSafe, TEXT_EXTENSIONS } from "../fs/workspace.js";

const execFileP = promisify(execFile);

const MAX_BUFFER = 1 << 26; // 64 MiB; protects against pathological diffs
const GIT_TIMEOUT = 15000; // ms per git invocation
const MAX_UNTRACKED_FILES = 200; // bound per-file work for new files
const MAX_UNTRACKED_LINES = 800; // cap synthesized adds for huge new files
const MAX_UNTRACKED_BYTES = 512 * 1024; // skip reading very large new files
// Git's canonical empty-tree object: lets us diff an unborn repo (no HEAD) so
// staged-but-uncommitted files still show up.
const EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904";

type Kind = "hunk" | "add" | "del" | "ctx" | "meta";
interface Hunk {
  header: string;
  lines: [Kind, string][];
}
interface DiffFile {
  path: string;
  status: "A" | "M" | "D" | "R";
  added: number;
  deleted: number;
  mtimeMs: number | null;
  hunks: Hunk[];
}

// Run git async. Returns ok=false with whatever stdout was produced: some git
// subcommands (`diff --no-index`, `rev-parse --verify`) exit non-zero by design
// yet still emit the output we need.
async function git(cfg: ProjectContext, args: string[]): Promise<{ ok: boolean; stdout: string }> {
  try {
    const { stdout } = await execFileP("git", args, {
      cwd: cfg.workspace,
      encoding: "utf-8",
      maxBuffer: MAX_BUFFER,
      timeout: GIT_TIMEOUT,
    });
    return { ok: true, stdout };
  } catch (err) {
    const stdout = (err as { stdout?: string })?.stdout;
    return { ok: false, stdout: typeof stdout === "string" ? stdout : "" };
  }
}

function mtimeOf(cfg: ProjectContext, path: string): number | null {
  try {
    return statSync(resolveRel(cfg.workspace, path)).mtimeMs;
  } catch {
    return null;
  }
}

// Parse a unified `git diff` patch into per-file hunks. We only keep the
// displayable lines (hunk headers + +/-/context); git's index/mode lines are
// dropped, matching the inline view.
function parsePatch(cfg: ProjectContext, patch: string): DiffFile[] {
  const files: DiffFile[] = [];
  let cur: DiffFile | null = null;
  let oldPath = "";
  let newPath = "";
  const flush = (): void => {
    if (!cur) return;
    const path = cur.status === "D" ? oldPath : newPath || oldPath;
    cur.path = path;
    cur.mtimeMs = cur.status === "D" ? null : mtimeOf(cfg, path);
    files.push(cur);
  };
  for (const line of patch.split("\n")) {
    if (line.startsWith("diff --git ")) {
      flush();
      cur = { path: "", status: "M", added: 0, deleted: 0, mtimeMs: null, hunks: [] };
      oldPath = "";
      newPath = "";
      continue;
    }
    if (!cur) continue;
    if (line.startsWith("new file mode")) cur.status = "A";
    else if (line.startsWith("deleted file mode")) cur.status = "D";
    else if (line.startsWith("rename from ")) {
      cur.status = "R";
      oldPath = line.slice("rename from ".length);
    } else if (line.startsWith("rename to ")) {
      cur.status = "R";
      newPath = line.slice("rename to ".length);
    } else if (line.startsWith("--- ")) {
      const p = line.slice(4);
      if (p !== "/dev/null") oldPath = p.replace(/^a\//, "");
    } else if (line.startsWith("+++ ")) {
      const p = line.slice(4);
      if (p !== "/dev/null") newPath = p.replace(/^b\//, "");
    } else if (line.startsWith("@@")) {
      cur.hunks.push({ header: line, lines: [] });
    } else if (cur.hunks.length) {
      const hunk = cur.hunks[cur.hunks.length - 1];
      if (line.startsWith("+")) {
        cur.added++;
        hunk.lines.push(["add", line]);
      } else if (line.startsWith("-")) {
        cur.deleted++;
        hunk.lines.push(["del", line]);
      } else if (line.startsWith("\\")) {
        hunk.lines.push(["meta", line]);
      } else {
        hunk.lines.push(["ctx", line]);
      }
    }
  }
  flush();
  return files;
}

// Synthesize an "all added" card for one untracked file by reading it directly
// — no per-file git subprocess. Symlinks, binaries and oversized files are
// summarized rather than read, so a single /api/diff stays cheap and bounded.
function untrackedCard(cfg: ProjectContext, path: string): DiffFile {
  let lines: [Kind, string][] = [];
  let added = 0;
  let mtimeMs: number | null = null;
  try {
    // lstat the LEXICAL path (not resolveRel's canonical path, which follows the
    // final symlink) so an untracked symlink — even one resolving inside the
    // workspace — is summarized, never read through.
    const lexical = resolve(join(cfg.workspace, path));
    if (!isSafe(cfg.workspace, lexical)) {
      lines = [["meta", "\\ outside workspace"]];
    } else {
      const st = lstatSync(lexical);
      if (st.isSymbolicLink()) {
        lines = [["meta", "\\ symlink"]];
      } else {
        mtimeMs = st.mtimeMs;
        if (!TEXT_EXTENSIONS.has(extname(path).toLowerCase())) {
          lines = [["meta", "\\ binary or non-text file"]];
        } else if (st.size > MAX_UNTRACKED_BYTES) {
          lines = [["meta", `\\ file too large to preview (${st.size} bytes)`]];
        } else {
          const raw = readFileSync(lexical, "utf-8");
          const arr = raw.length ? raw.split("\n") : [];
          if (arr.length && arr[arr.length - 1] === "") arr.pop(); // drop trailing-newline empty
          added = arr.length;
          for (const l of arr.slice(0, MAX_UNTRACKED_LINES)) lines.push(["add", `+${l}`]);
          if (added > MAX_UNTRACKED_LINES) {
            lines.push(["meta", `\\ ${added - MAX_UNTRACKED_LINES} more added lines`]);
          }
        }
      }
    }
  } catch {
    lines = [["meta", "\\ unreadable"]];
  }
  return {
    path,
    status: "A",
    added,
    deleted: 0,
    mtimeMs,
    hunks: lines.length ? [{ header: `@@ -0,0 +1,${added} @@`, lines }] : [],
  };
}

// List untracked files (bounded) and synthesize their add cards.
async function untrackedFiles(cfg: ProjectContext): Promise<DiffFile[]> {
  // `-- .` scopes the listing to the workspace subtree (cwd), not the whole repo.
  const listed = await git(cfg, ["ls-files", "--others", "--exclude-standard", "-z", "--", "."]);
  if (!listed.ok) return [];
  const paths = listed.stdout.split("\0").filter(Boolean);
  const out = paths.slice(0, MAX_UNTRACKED_FILES).map((p) => untrackedCard(cfg, p));
  if (paths.length > MAX_UNTRACKED_FILES) {
    out.push({
      path: `… ${paths.length - MAX_UNTRACKED_FILES} more untracked files (truncated)`,
      status: "A",
      added: 0,
      deleted: 0,
      mtimeMs: null,
      hunks: [],
    });
  }
  return out;
}

export async function handleDiff(res: ServerResponse, cfg: ProjectContext): Promise<void> {
  if (!(await git(cfg, ["rev-parse", "--is-inside-work-tree"])).ok) {
    sendJson(res, { git: false, files: [] });
    return;
  }
  const hasHead = (await git(cfg, ["rev-parse", "--verify", "HEAD"])).ok;
  // `--relative` emits workspace-relative paths and `-- .` restricts the diff to
  // the workspace subtree, so a workspace nested in a larger repo stays scoped.
  // Base is HEAD, or the empty tree for an unborn repo (keeps staged files).
  const base = hasHead ? "HEAD" : EMPTY_TREE;
  // --no-ext-diff/--no-textconv stop git from running repo-configured external
  // diff or textconv programs when serving this network-facing endpoint.
  const patch = await git(cfg, [
    "-c", "core.quotepath=false",
    "diff", "--no-ext-diff", "--no-textconv", "--relative", base, "--", ".",
  ]);
  const tracked = patch.ok ? parsePatch(cfg, patch.stdout) : [];
  const files = [...tracked, ...(await untrackedFiles(cfg))];
  files.sort((a, b) => (b.mtimeMs ?? 0) - (a.mtimeMs ?? 0));
  sendJson(res, { git: true, files });
}
