// GET /api/diff -> git working-tree changes for the diff panel.
// Returns per-file {path, status, added, deleted, mtimeMs, hunks} for tracked
// changes (vs HEAD, staged + unstaged combined) plus untracked files as adds.
//
// Redline compliance:
//  - spawnSync with a fixed arg array, NO shell, cwd = workspace (no user path
//    is ever interpolated into a git argument).
//  - file mtime is read through resolveRel so a reported path cannot escape the
//    workspace.
import type { ServerResponse } from "node:http";
import { spawnSync } from "node:child_process";
import { statSync } from "node:fs";
import type { Config } from "../config.js";
import { sendJson } from "../sse.js";
import { resolveRel, TEXT_EXTENSIONS } from "../fs/workspace.js";
import { extname } from "node:path";

const MAX_BUFFER = 1 << 26; // 64 MiB; protects against pathological diffs
const MAX_UNTRACKED_LINES = 800; // cap synthesized adds for huge new files

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

function git(cfg: Config, args: string[]): { ok: boolean; stdout: string } {
  const r = spawnSync("git", args, {
    cwd: cfg.workspace,
    encoding: "utf-8",
    maxBuffer: MAX_BUFFER,
  });
  return { ok: r.status === 0, stdout: r.stdout || "" };
}

function mtimeOf(cfg: Config, path: string): number | null {
  try {
    return statSync(resolveRel(cfg.workspace, path)).mtimeMs;
  } catch {
    return null;
  }
}

// Parse a unified `git diff` patch into per-file hunks. We only keep the
// displayable lines (hunk headers + +/-/context); git's index/mode lines are
// dropped, matching the prototype's inline view.
function parsePatch(cfg: Config, patch: string): DiffFile[] {
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

// Synthesize an "all added" diff card for each untracked file.
function untrackedFiles(cfg: Config): DiffFile[] {
  const out: DiffFile[] = [];
  const listed = git(cfg, ["ls-files", "--others", "--exclude-standard", "-z"]);
  if (!listed.ok) return out;
  for (const path of listed.stdout.split("\0").filter(Boolean)) {
    const isText = TEXT_EXTENSIONS.has(extname(path).toLowerCase());
    let lines: [Kind, string][] = [];
    let added = 0;
    if (isText) {
      const shown = git(cfg, ["diff", "--no-index", "--", "/dev/null", path]);
      // --no-index exits 1 when files differ; stdout still holds the patch.
      const body = shown.stdout.split("\n");
      let inHunk = false;
      for (const l of body) {
        if (l.startsWith("@@")) {
          inHunk = true;
          continue;
        }
        if (!inHunk) continue;
        if (l.startsWith("+")) {
          added++;
          if (lines.length < MAX_UNTRACKED_LINES) lines.push(["add", l]);
        }
      }
      if (added > MAX_UNTRACKED_LINES) {
        lines.push(["meta", `\\ ${added - MAX_UNTRACKED_LINES} more added lines`]);
      }
    } else {
      lines = [["meta", "\\ binary or non-text file"]];
    }
    out.push({
      path,
      status: "A",
      added,
      deleted: 0,
      mtimeMs: mtimeOf(cfg, path),
      hunks: lines.length ? [{ header: `@@ -0,0 +1,${added} @@`, lines }] : [],
    });
  }
  return out;
}

export function handleDiff(res: ServerResponse, cfg: Config): void {
  if (!git(cfg, ["rev-parse", "--is-inside-work-tree"]).ok) {
    sendJson(res, { git: false, files: [] });
    return;
  }
  const hasHead = git(cfg, ["rev-parse", "--verify", "HEAD"]).ok;
  const diffArgs = ["-c", "core.quotepath=false", "diff"];
  if (hasHead) diffArgs.push("HEAD");
  const patch = git(cfg, diffArgs);
  const tracked = patch.ok ? parsePatch(cfg, patch.stdout) : [];
  const files = [...tracked, ...untrackedFiles(cfg)];
  files.sort((a, b) => (b.mtimeMs ?? 0) - (a.mtimeMs ?? 0));
  sendJson(res, { git: true, files });
}
