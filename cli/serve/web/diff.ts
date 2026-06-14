// Git diff panel: collapsible per-file cards -> inline unified diff.
// Data comes from GET /api/diff (server/routes/diff.ts). Replaces the old
// editor-local original-vs-content diff: the panel is now workspace-wide and
// independent of the selected file.
import { $, esc } from "./state.js";
import { api } from "./api.js";

interface DiffFile {
  path: string;
  status: "A" | "M" | "D" | "R";
  added: number;
  deleted: number;
  mtimeMs: number | null;
  hunks: { header: string; lines: [string, string][] }[];
}

function fmtTime(ms: number | null): string {
  if (!ms) return "";
  const d = new Date(ms);
  const now = new Date();
  const pad = (n: number): string => String(n).padStart(2, "0");
  if (d.toDateString() === now.toDateString()) return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function bar(added: number, deleted: number): string {
  const total = added + deleted;
  const n = Math.min(5, total);
  const a = total ? Math.round((added / total) * n) : 0;
  let html = '<span class="diff-bar">';
  for (let i = 0; i < n; i++) html += `<span class="${i < a ? "a" : "d"}"></span>`;
  for (let i = n; i < 5; i++) html += '<span class="n"></span>';
  return html + "</span>";
}

function fileCard(f: DiffFile): string {
  const slash = f.path.lastIndexOf("/");
  const dir = slash >= 0 ? f.path.slice(0, slash + 1) : "";
  const name = slash >= 0 ? f.path.slice(slash + 1) : f.path;
  let body = '<pre class="diff-lines">';
  for (const h of f.hunks) {
    body += `<span class="ln hunk">${esc(h.header)}</span>`;
    for (const [kind, text] of h.lines) body += `<span class="ln ${kind}">${esc(text)}</span>`;
  }
  if (!f.hunks.length) body += '<span class="ln meta">(no textual diff)</span>';
  body += "</pre>";
  return `<div class="file-card">
    <div class="file-card-head">
      <span class="chev">&#9654;</span>
      <span class="diff-badge ${f.status}">${f.status}</span>
      <span class="fname"><span class="dir">${esc(dir)}</span>${esc(name)}</span>
      <span class="diff-meta">${bar(f.added, f.deleted)}<span class="stat"><b>+${f.added}</b> <s>-${f.deleted}</s></span><span class="time">${fmtTime(f.mtimeMs)}</span></span>
    </div>
    <div class="file-card-body">${body}</div>
  </div>`;
}

export async function renderGitDiff(root: HTMLElement): Promise<void> {
  root.innerHTML = '<div class="empty">Loading git diff…</div>';
  let data: { git: boolean; files: DiffFile[] };
  try {
    data = await (await api("/api/diff")).json();
  } catch (err: any) {
    root.innerHTML = `<div class="empty">${esc(err.message || "failed to load diff")}</div>`;
    return;
  }
  if (!data.git) {
    root.innerHTML = '<div class="empty">Not a git repository.\nThe diff panel shows git working-tree changes.</div>';
    return;
  }
  if (!data.files.length) {
    root.innerHTML = '<div class="empty">No changes.\nworking tree clean — nothing to diff.</div>';
    return;
  }
  const totalAdd = data.files.reduce((s, f) => s + f.added, 0);
  const totalDel = data.files.reduce((s, f) => s + f.deleted, 0);
  const summary = `<div class="diff-summary"><span>${data.files.length} files changed · <span class="totals"><b>+${totalAdd}</b> <s>-${totalDel}</s></span></span><button class="diff-refresh" id="diff-refresh" title="Refresh git diff">&#x21bb;</button></div>`;
  root.innerHTML = `<div class="diff-panel">${summary}${data.files.map(fileCard).join("")}</div>`;
  root.querySelectorAll(".file-card-head").forEach((head) => {
    head.addEventListener("click", () => head.parentElement!.classList.toggle("open"));
  });
  $("diff-refresh").addEventListener("click", () => renderGitDiff(root));
}
