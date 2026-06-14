// omp-serve web app entry: boot + event wiring. Ported 1:1 from APP_HTML.
import { state, $, esc, newSessionId } from "./state.js";
import { api } from "./api.js";
import { loadTree } from "./tree.js";
import { renderEditor, setMode, saveFile, selectFile } from "./editor.js";
import { sendMessage } from "./chat.js";
import { setSideTab, fitTerminal } from "./terminal.js";

function setTheme(theme: string): void {
  const next = theme === "light" ? "light" : "dark";
  document.body.dataset.theme = next;
  localStorage.setItem("ompServeTheme", next);
  $("theme-toggle").textContent = next === "light" ? "Dark" : "Light";
}

function toggleTheme(): void {
  setTheme(document.body.dataset.theme === "light" ? "dark" : "light");
}

async function loadMeta(): Promise<void> {
  const data = await (await api("/api/meta")).json();
  state.workspace = data.workspace;
  $("workspace-label").textContent = `pi -p --mode json --approve · ${data.workspace} · ${data.model}`;
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
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") sendMessage();
});
$("file-tree").addEventListener("sl-selection-change", (event: Event) => {
  const selected = (event as CustomEvent).detail.selection?.[0];
  if (selected?.dataset?.type === "file") selectFile(selected.dataset.path);
});
window.addEventListener("resize", fitTerminal);

(async function boot() {
  try {
    setTheme(localStorage.getItem("ompServeTheme") || "dark");
    state.sessionId = newSessionId();
    $("session-label").textContent = `session: ${state.sessionId.slice(0, 8)}`;
    await loadMeta();
    await loadTree();
    renderEditor();
  } catch (err: any) {
    $("file-list").innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  }
})();
