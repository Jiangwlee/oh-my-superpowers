// Multi-project support: the footer project tabs, switching, the "+ add"
// directory picker and the localStorage mirror.
//
// Source of truth is the backend registry (GET /api/projects). localStorage is
// only a fast-restore mirror reconciled on boot — the server always wins.
import { state, $, esc, newSessionId, type ProjectInfo } from "./state.js";
import { api } from "./api.js";
import { loadTree } from "./tree.js";
import { renderEditor, updateChrome } from "./editor.js";
import { newSession, bindSession } from "./session.js";
import { renderHistoryTurns } from "./chat.js";
import { openDialog, confirmDialog } from "./dialog.js";

const MIRROR_KEY = "ompServeProjects";

interface Mirror {
  projects: ProjectInfo[];
  currentProjectId: string;
}

function readMirror(): Mirror {
  try {
    const m = JSON.parse(localStorage.getItem(MIRROR_KEY) || "");
    if (Array.isArray(m?.projects)) {
      return { projects: m.projects, currentProjectId: String(m.currentProjectId || "") };
    }
  } catch {
    /* missing/corrupt */
  }
  return { projects: [], currentProjectId: "" };
}

function persist(): void {
  const mirror: Mirror = { projects: state.projects, currentProjectId: state.currentProjectId };
  localStorage.setItem(MIRROR_KEY, JSON.stringify(mirror));
}

// Project info shown in the top bar (workspace + model). Scoped to the current
// project, so it is refreshed on every switch.
export async function loadMeta(): Promise<void> {
  const data = await (await api("/api/meta")).json();
  state.workspace = data.workspace;
  $("workspace-label").textContent = `pi -p --mode json --approve · ${data.workspace} · ${data.model}`;
}

export function renderTabs(): void {
  const host = $("proj-tabs");
  host.innerHTML = "";
  for (const project of state.projects) {
    const tab = document.createElement("button");
    tab.className = `proj${project.id === state.currentProjectId ? " active" : ""}`;
    tab.dataset.id = project.id;
    tab.title = project.path;
    tab.innerHTML = `<span class="dot"></span><span class="name">${esc(project.name)}</span><span class="close" title="移除项目">×</span>`;
    host.appendChild(tab);
  }
}

// Reset every project-scoped surface (top bar, file tree, editor) to the
// current project. The pi session is rotated separately by the caller.
async function reloadProjectSurfaces(): Promise<void> {
  state.selectedPath = "";
  state.original = "";
  state.content = "";
  state.dirty = false;
  state.mode = "preview";
  await loadMeta();
  await loadTree();
  updateChrome();
  renderEditor();
}

export async function switchProject(id: string): Promise<void> {
  if (id === state.currentProjectId) return;
  const prev = state.currentProjectId;
  // Remember the session we are leaving so a later switch back resumes it.
  if (prev) state.projectSessions[prev] = state.sessionId;
  // The new id must be live before reloadProjectSurfaces so its project-scoped
  // requests resolve correctly; renderTabs gives immediate feedback.
  state.currentProjectId = id;
  renderTabs();
  // Resume this project's last session, or start a fresh one the first time.
  const resumed = state.projectSessions[id];
  const sessionId = resumed || newSessionId();
  state.projectSessions[id] = sessionId;
  bindSession(sessionId); // reset chat/terminal UI, bind pi --session to it
  try {
    await reloadProjectSurfaces();
    if (resumed) await loadSessionHistory(sessionId); // repaint past turns
    persist(); // only pin a project that actually loaded
  } catch (err: any) {
    // Roll back so a vanished/removed project never leaves a broken active tab.
    state.currentProjectId = prev;
    renderTabs();
    if (prev) {
      const prevSession = state.projectSessions[prev] || state.sessionId;
      bindSession(prevSession);
      await loadSessionHistory(prevSession).catch(() => {});
    }
    $("file-list").innerHTML = `<div class="empty">${esc(err?.message || "failed to open project")}</div>`;
  }
}

// Fetch a resumed session's past turns and repaint them. Best-effort: a missing
// or unreadable session just leaves a clean panel.
async function loadSessionHistory(sessionId: string): Promise<void> {
  try {
    const data = await (await api(`/api/session?sessionId=${encodeURIComponent(sessionId)}`)).json();
    if (Array.isArray(data.turns) && data.turns.length) renderHistoryTurns(data.turns);
  } catch {
    /* leave the cleared panel as-is */
  }
}

// Fetch the authoritative project list and reconcile the current selection:
// keep it if still valid, else fall back to the mirror's choice, else the first
// project. Renders tabs and persists.
export async function loadProjects(): Promise<void> {
  const data = await (await api("/api/projects")).json();
  state.projects = (data.projects || []).map((p: ProjectInfo) => ({ id: p.id, name: p.name, path: p.path }));
  const valid = (id: string): boolean => state.projects.some((p) => p.id === id);
  if (!valid(state.currentProjectId)) {
    const stored = readMirror().currentProjectId;
    state.currentProjectId = valid(stored) ? stored : state.projects[0]?.id || "";
  }
  persist();
  renderTabs();
}

// Boot: paint instantly from the mirror, then reconcile against the server.
export async function initProjects(): Promise<void> {
  const mirror = readMirror();
  state.projects = mirror.projects;
  state.currentProjectId = mirror.currentProjectId;
  renderTabs();
  await loadProjects();
}

async function removeProjectFlow(id: string): Promise<void> {
  const project = state.projects.find((p) => p.id === id);
  if (!project) return;
  // Keep at least one project so the registry never empties and no request ever
  // falls through to an unscoped state.
  if (state.projects.length <= 1) {
    openDialog({
      title: "无法移除",
      body: `<p class="omp-dialog-message">至少保留一个项目。先添加另一个项目，再移除「${esc(project.name)}」。</p>`,
      actions: [{ label: "知道了", variant: "primary" }],
    });
    return;
  }
  const ok = await confirmDialog({
    title: "移除项目",
    message: `从工作台移除「${project.name}」？只移除标签，不会删除磁盘上的任何文件。`,
    confirmLabel: "移除",
    cancelLabel: "取消",
    danger: true,
  });
  if (!ok) return;
  const wasCurrent = state.currentProjectId === id;
  try {
    await api(`/api/projects?id=${encodeURIComponent(id)}`, { method: "DELETE" });
  } catch {
    // Another tab may have removed projects concurrently (e.g. server refuses
    // to empty the registry). Re-sync from the server and stop.
    await loadProjects();
    return;
  }
  await loadProjects();
  if (wasCurrent) {
    newSession();
    await reloadProjectSurfaces();
  }
}

// "+ add project": a directory picker sandboxed to $HOME. Rows navigate into
// subdirectories; the primary action registers the currently-browsed directory.
function openAddDialog(): void {
  const body = document.createElement("div");
  body.className = "omp-browser-wrap";
  let current = "";

  const handle = openDialog({
    title: "选择一个目录作为项目",
    body,
    actions: [
      { label: "取消", variant: "default" },
      {
        label: "添加此目录",
        variant: "primary",
        onClick: () => {
          void addCurrent();
          return false; // keep open until the add resolves
        },
      },
    ],
  });

  async function render(path: string): Promise<void> {
    let data: { path: string; parent: string | null; home: string; entries: { name: string; path: string }[] };
    try {
      data = await (await api(`/api/browse?path=${encodeURIComponent(path)}`)).json();
    } catch (err: any) {
      body.innerHTML = `<div class="omp-browser-err">${esc(err.message || err)}</div>`;
      return;
    }
    current = data.path;
    const rel = data.path.startsWith(data.home) ? "~" + data.path.slice(data.home.length) : data.path;
    const rows = [
      data.parent ? `<div class="row up" data-path="${esc(data.parent)}"><span class="ic">↰</span><span>..</span></div>` : "",
      ...data.entries.map(
        (e) => `<div class="row" data-path="${esc(e.path)}"><span class="ic">▸</span><span>${esc(e.name)}</span></div>`,
      ),
    ].join("");
    body.innerHTML =
      `<div class="omp-crumb">当前目录：<b>${esc(rel)}</b></div>` +
      `<div class="omp-browser">${rows || '<div class="row empty">（无子目录）</div>'}</div>`;
    body.querySelectorAll<HTMLElement>(".omp-browser .row[data-path]").forEach((row) => {
      row.addEventListener("click", () => render(row.dataset.path || ""));
    });
  }

  async function addCurrent(): Promise<void> {
    try {
      const res = await api("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: current }),
      });
      const { project } = await res.json();
      handle.close();
      await loadProjects();
      await switchProject(project.id);
    } catch (err: any) {
      const note = body.querySelector(".omp-crumb");
      if (note) note.innerHTML = `<span class="omp-browser-err">${esc(err.message || err)}</span>`;
    }
  }

  void render("");
}

// Wire footer controls. Tab click switches; the × removes (with confirm); the
// + opens the picker.
export function wireProjectFooter(): void {
  $("proj-tabs").addEventListener("click", (event: Event) => {
    const target = event.target as HTMLElement;
    const tab = target.closest(".proj") as HTMLElement | null;
    if (!tab) return;
    const id = tab.dataset.id || "";
    if (target.classList.contains("close")) {
      void removeProjectFlow(id);
      return;
    }
    void switchProject(id);
  });
  $("proj-add").addEventListener("click", openAddDialog);
}
