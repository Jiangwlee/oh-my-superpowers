// Editor: Preview/Edit/Diff + Gen UI mode tab. Ported 1:1 from APP_HTML.
import { state, $, esc, isMarkdown, isHtml } from "./state.js";
import { api } from "./api.js";
import { renderMarkdown } from "./markdown.js";
import { renderGitDiff } from "./diff.js";
import { GENUI_SHELL, postGenUi } from "./genui.js";
import { syncTreeSelection } from "./tree.js";

function formatBytes(bytes: number): string {
  if (!bytes) return "0 bytes";
  if (bytes < 1024) return `${bytes} bytes`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${Math.round((bytes / 1024 / 1024) * 10) / 10} MB`;
}

export function updateChrome(): void {
  const isText = state.fileKind === "text";
  $("active-file").textContent = state.selectedPath || "Select a file";
  $("file-status").textContent = state.selectedPath
    ? isText
      ? `${state.content.length} chars`
      : `${formatBytes(state.fileSize)} · ${state.fileKind}`
    : "no file";
  $("dirty-label").textContent = state.dirty ? "dirty" : "clean";
  const saveBtn = $("save-btn") as HTMLButtonElement;
  saveBtn.classList.toggle("dirty", state.dirty);
  saveBtn.disabled = !state.selectedPath || !isText;
  document
    .querySelectorAll("[data-mode]")
    .forEach((btn) => {
      const el = btn as HTMLButtonElement;
      el.classList.toggle("active", el.dataset.mode === state.mode);
      if (el.dataset.mode === "edit") el.disabled = !isText;
    });
  $("mode-label").textContent = `mode: ${state.mode}`;
}

export function setMode(mode: string): void {
  if (mode === "edit" && state.fileKind !== "text") return;
  state.mode = mode;
  updateChrome();
  renderEditor();
}

export function renderEditor(): void {
  const root = $("editor-surface");
  if (state.mode === "genui") {
    if (!state.genUiHtml) {
      root.innerHTML =
        '<div class="empty">No generative UI yet.\nAsk the assistant to build, visualize, or prototype something.</div>';
      return;
    }
    // Build the persistent shell once; push content (with scripts) once it loads.
    root.innerHTML = `<iframe class="html-frame" id="genui-frame" sandbox="allow-scripts allow-forms allow-popups allow-modals" srcdoc="${esc(GENUI_SHELL)}"></iframe>`;
    // Run scripts on load only when this paint is the definitive final document.
    // A mode switch triggered by a streamed delta paints partial HTML with
    // run=false; scripts run only once the final gen_ui event arrives.
    root.querySelector("#genui-frame")!.addEventListener("load", () => postGenUi(state.genUiFinal === true));
    return;
  }
  if (state.mode === "diff") {
    // Workspace-wide git diff; independent of the selected file.
    renderGitDiff(root);
    return;
  }
  if (!state.selectedPath) {
    root.innerHTML = '<div class="empty">Select a file from the project tree.</div>';
    return;
  }
  if (state.mode === "edit") {
    if (state.fileKind !== "text") {
      state.mode = "preview";
      updateChrome();
      renderEditor();
      return;
    }
    root.innerHTML = `<textarea class="editor-text" spellcheck="false">${esc(state.content)}</textarea>`;
    const ta = root.querySelector("textarea")!;
    ta.addEventListener("input", () => {
      state.content = ta.value;
      state.dirty = state.content !== state.original;
      updateChrome();
    });
    ta.focus();
    return;
  }
  if (state.mode === "preview") {
    if (state.fileKind === "image") {
      root.innerHTML = `<div class="preview image-preview"><img src="${esc(state.fileDataUrl)}" alt="${esc(state.selectedPath)}"><div class="image-caption">${esc(state.selectedPath)} · ${formatBytes(state.fileSize)}</div></div>`;
    } else if (state.fileKind === "meta") {
      root.innerHTML = `<div class="empty">Preview is unavailable.\n${esc(state.selectedPath)} · ${formatBytes(state.fileSize)}</div>`;
    } else if (isMarkdown(state.selectedPath)) {
      root.innerHTML = `<div class="preview">${renderMarkdown(state.content)}</div>`;
    } else if (isHtml(state.selectedPath)) {
      root.innerHTML = `<iframe class="html-frame" sandbox="allow-scripts allow-forms allow-popups allow-modals" srcdoc="${esc(state.content)}"></iframe>`;
    } else {
      root.innerHTML = `<pre class="preview">${esc(state.content)}</pre>`;
    }
    return;
  }
}

export async function selectFile(path: string): Promise<void> {
  if (state.dirty && !confirm("Discard unsaved changes?")) return;
  const data = await (await api(`/api/file?path=${encodeURIComponent(path)}`)).json();
  state.selectedPath = data.path;
  state.fileKind = data.kind === "image" || data.kind === "meta" ? data.kind : "text";
  state.fileSize = Number(data.size || 0);
  state.fileDataUrl = String(data.dataUrl || "");
  state.original = state.fileKind === "text" ? data.content ?? "" : "";
  state.content = state.fileKind === "text" ? data.content ?? "" : "";
  state.dirty = false;
  state.mode = "preview";
  updateChrome();
  syncTreeSelection();
  renderEditor();
}

export function clearSelectedFile(): void {
  state.selectedPath = "";
  state.original = "";
  state.content = "";
  state.fileKind = "text";
  state.fileSize = 0;
  state.fileDataUrl = "";
  state.dirty = false;
  state.mode = "preview";
  updateChrome();
  renderEditor();
}

export async function saveFile(): Promise<void> {
  if (!state.selectedPath || state.fileKind !== "text") return;
  await api("/api/file", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: state.selectedPath, content: state.content }),
  });
  state.original = state.content;
  state.dirty = false;
  updateChrome();
}
