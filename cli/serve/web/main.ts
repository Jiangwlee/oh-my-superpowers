// omp-serve web app entry: boot + event wiring. Ported 1:1 from APP_HTML.
import { state, $, esc, newSessionId } from "./state.js";
import { latestSession, rawFileUrl } from "./api.js";
import { loadTree, refreshTree, syncTreeSelection } from "./tree.js";
import { renderEditor, setMode, saveFile, selectFile, clearSelectedFile } from "./editor.js";
import { handleFileSuggestKeydown, sendMessage, updateFileSuggest, uploadChatFiles, loadSessionHistory } from "./chat.js";
import { refreshGitDiff } from "./diff.js";
import { setSideTab, fitTerminal } from "./terminal.js";
import { newSession } from "./session.js";
import { initProjects, loadMeta, wireProjectFooter } from "./projects.js";
import { deletePath, uploadFiles } from "./api.js";

function setTheme(theme: string): void {
  const next = theme === "light" ? "light" : "dark";
  document.body.dataset.theme = next;
  localStorage.setItem("ompServeTheme", next);
  $("theme-toggle").textContent = next === "light" ? "Dark" : "Light";
}

function toggleTheme(): void {
  setTheme(document.body.dataset.theme === "light" ? "dark" : "light");
}

function parentPath(path: string): string {
  const idx = path.lastIndexOf("/");
  return idx === -1 ? "" : path.slice(0, idx);
}

function treeUploadDirectory(): string {
  if (state.treeSelectedType === "directory") return state.treeSelectedPath;
  if (state.treeSelectedType === "file") return parentPath(state.treeSelectedPath);
  return "";
}

function deletedPathContainsSelected(path: string): boolean {
  return state.selectedPath === path || state.selectedPath.startsWith(`${path}/`);
}

function setTreeSelectionFromItem(item: HTMLElement): void {
  state.treeSelectedPath = item.dataset.path || "";
  state.treeSelectedType = item.dataset.type === "file" || item.dataset.type === "directory" ? item.dataset.type : "";
  syncTreeSelection();
}

function closeTreeMenus(except?: HTMLElement): void {
  document.querySelectorAll("sl-tree-item.menu-open").forEach((item) => {
    if (item !== except) item.classList.remove("menu-open");
  });
}

async function deleteTreeSelection(): Promise<void> {
  const target = state.treeSelectedPath;
  if (!target) return;
  if (!confirm(`Delete ${target}?`)) return;
  try {
    await deletePath(target);
    if (deletedPathContainsSelected(target)) clearSelectedFile();
    state.treeSelectedPath = "";
    state.treeSelectedType = "";
    await refreshTree();
    await refreshGitDiff();
  } catch (err: any) {
    $("file-list").innerHTML = `<div class="empty">${esc(err.message || "delete failed")}</div>`;
  }
}

function downloadTreeSelection(): void {
  if (!state.treeSelectedPath || state.treeSelectedType !== "file") return;
  const link = document.createElement("a");
  link.href = rawFileUrl(state.treeSelectedPath);
  link.download = state.treeSelectedPath.split("/").pop() || state.treeSelectedPath;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

document
  .querySelectorAll("[data-mode]")
  .forEach((btn) => btn.addEventListener("click", () => setMode((btn as HTMLElement).dataset.mode!)));
document
  .querySelectorAll("[data-side-tab]")
  .forEach((btn) => btn.addEventListener("click", () => setSideTab((btn as HTMLElement).dataset.sideTab!)));
$("save-btn").addEventListener("click", saveFile);
$("send-btn").addEventListener("click", sendMessage);
$("theme-toggle").addEventListener("click", toggleTheme);
$("chat-input").addEventListener("keydown", (event: Event) => {
  const e = event as KeyboardEvent;
  if (handleFileSuggestKeydown(e)) return;
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") sendMessage();
});
$("chat-input").addEventListener("input", () => {
  updateFileSuggest().catch(() => {});
});
$("file-tree").addEventListener("sl-selection-change", (event: Event) => {
  const selected = (event as CustomEvent).detail.selection?.[0];
  state.treeSelectedPath = selected?.dataset?.path || "";
  state.treeSelectedType = selected?.dataset?.type === "file" || selected?.dataset?.type === "directory" ? selected.dataset.type : "";
  syncTreeSelection();
  if (selected?.dataset?.type === "file") selectFile(selected.dataset.path);
});
$("file-tree").addEventListener("click", (event: Event) => {
  const target = event.target as HTMLElement;
  const item = target.closest("sl-tree-item") as HTMLElement | null;
  if (!item || !item.dataset.path) return;
  if (target.closest("[data-tree-menu-toggle]")) {
    event.preventDefault();
    event.stopPropagation();
    setTreeSelectionFromItem(item);
    const nextOpen = !item.classList.contains("menu-open");
    closeTreeMenus(item);
    item.classList.toggle("menu-open", nextOpen);
    return;
  }
  const action = target.closest("[data-tree-action]") as HTMLElement | null;
  if (!action) return;
  event.preventDefault();
  event.stopPropagation();
  setTreeSelectionFromItem(item);
  closeTreeMenus();
  if (action.dataset.treeAction === "upload") ($("tree-upload-input") as HTMLInputElement).click();
  if (action.dataset.treeAction === "download") downloadTreeSelection();
  if (action.dataset.treeAction === "delete") void deleteTreeSelection();
});
document.addEventListener("click", (event: Event) => {
  if (!(event.target as HTMLElement).closest("sl-tree-item")) closeTreeMenus();
});
$("new-session").addEventListener("click", newSession);
$("chat-upload").addEventListener("click", () => ($("chat-upload-input") as HTMLInputElement).click());
$("chat-upload-input").addEventListener("change", async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  input.value = "";
  try {
    await uploadChatFiles(files);
    await refreshTree();
    await refreshGitDiff();
  } catch (err: any) {
    $("chat-status").textContent = err.message || "upload failed";
  }
});
$("tree-upload-input").addEventListener("change", async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  input.value = "";
  if (!files.length) return;
  try {
    await uploadFiles(files, treeUploadDirectory());
    await refreshTree();
    await refreshGitDiff();
  } catch (err: any) {
    $("file-list").innerHTML = `<div class="empty">${esc(err.message || "upload failed")}</div>`;
  }
});
wireProjectFooter();
$("tree-refresh").addEventListener("click", async () => {
  const btn = $("tree-refresh") as HTMLButtonElement;
  if (btn.disabled) return;
  btn.disabled = true;
  btn.classList.add("spinning");
  try {
    await refreshTree(); // rebuild from root, restoring expanded directories
  } catch (err: any) {
    $("file-list").innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  } finally {
    btn.classList.remove("spinning");
    btn.disabled = false;
  }
});
window.addEventListener("resize", fitTerminal);

(async function boot() {
  try {
    setTheme(localStorage.getItem("ompServeTheme") || "dark");
    await initProjects(); // sets currentProjectId before any project-scoped request
    // Resume the project's most recent session if it has one, else open a fresh
    // one. Remembered so switching away and back resumes it.
    const existing = state.currentProjectId ? await latestSession() : null;
    const sessionId = existing || newSessionId();
    if (state.currentProjectId) state.projectSessions[state.currentProjectId] = sessionId;
    state.sessionId = sessionId;
    $("session-label").textContent = `session: ${sessionId.slice(0, 8)}`;
    await loadMeta();
    await loadTree();
    renderEditor();
    if (existing) await loadSessionHistory(sessionId); // repaint the resumed transcript
  } catch (err: any) {
    $("file-list").innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  }
})();
