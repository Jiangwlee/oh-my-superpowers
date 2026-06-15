// Shoelace file tree: lazy load + selection. Ported 1:1 from APP_HTML.
import { state, $, esc } from "./state.js";
import { loadDirectory } from "./api.js";

export async function loadTree(): Promise<void> {
  const tree = $("file-tree");
  const data = await loadDirectory("");
  tree.innerHTML = "";
  $("tree-count").textContent = String(data.count);
  for (const node of data.nodes) tree.appendChild(createTreeItem(node));
}

function renderItemLabel(item: HTMLElement, name: string): void {
  const type = item.dataset.type || "file";
  const isDirectory = type === "directory";
  item.insertAdjacentHTML(
    "afterbegin",
    `<span class="tree-row"><span class="tree-name">${esc(name)}</span><button class="tree-menu-toggle" title="File actions" aria-label="File actions" data-tree-menu-toggle>⋯</button><span class="tree-menu"><button data-tree-action="upload">Upload</button><button data-tree-action="download" ${isDirectory ? "disabled title=\"Only files can be downloaded\"" : ""}>Download</button><button class="danger" data-tree-action="delete">Delete</button></span></span>`,
  );
}

export function createTreeItem(node: any): HTMLElement {
  const item = document.createElement("sl-tree-item") as HTMLElement;
  item.title = node.path;
  item.dataset.path = node.path;
  item.dataset.type = node.type;
  item.classList.add(node.type === "directory" ? "folder" : "file");
  renderItemLabel(item, node.name);
  if (node.path === state.treeSelectedPath) item.classList.add("tree-selected");
  if (node.type === "directory" && node.hasChildren) {
    item.setAttribute("lazy", "");
    item.addEventListener("sl-lazy-load", async (event) => {
      event.stopPropagation();
      await populateDirectory(item);
    });
  }
  if (node.path === state.selectedPath) (item as any).selected = true;
  return item;
}

export async function populateDirectory(item: HTMLElement): Promise<void> {
  const path = item.dataset.path || "";
  try {
    const data = await loadDirectory(path);
    item.innerHTML = "";
    renderItemLabel(item, item.title.split("/").pop() || item.title);
    for (const node of data.nodes) item.appendChild(createTreeItem(node));
    if (!data.nodes.length) {
      const empty = document.createElement("sl-tree-item") as HTMLElement;
      empty.textContent = "(empty)";
      (empty as any).disabled = true;
      empty.classList.add("empty");
      item.appendChild(empty);
    }
  } catch (err: any) {
    item.innerHTML = "";
    renderItemLabel(item, item.title.split("/").pop() || item.title);
    const empty = document.createElement("sl-tree-item") as HTMLElement;
    empty.textContent = err.message || "failed to load";
    (empty as any).disabled = true;
    empty.classList.add("empty");
    item.appendChild(empty);
  } finally {
    (item as any).lazy = false;
    item.removeAttribute("lazy");
  }
}

function findTreeItem(path: string): HTMLElement | null {
  for (const el of Array.from(document.querySelectorAll("sl-tree-item"))) {
    if ((el as HTMLElement).dataset.path === path) return el as HTMLElement;
  }
  return null;
}

// Rebuild the tree from root but restore the previously-expanded directories,
// so a refresh (manual or post-turn auto) does not collapse the user's view.
// Dirs that no longer exist are silently dropped; selection is restored by
// createTreeItem via state.selectedPath.
export async function refreshTree(): Promise<void> {
  // Capture expanded directory paths, shallow→deep so each parent is rebuilt
  // and populated before we look up its children.
  const expanded = Array.from(document.querySelectorAll("sl-tree-item"))
    .filter(
      (el) =>
        (el as any).expanded && (el as HTMLElement).dataset.type === "directory",
    )
    .map((el) => (el as HTMLElement).dataset.path || "")
    .filter(Boolean)
    .sort((a, b) => a.split("/").length - b.split("/").length);

  await loadTree();

  for (const path of expanded) {
    const item = findTreeItem(path);
    if (!item) continue; // directory removed since last expand
    await populateDirectory(item); // load children, clears lazy
    (item as any).expanded = true;
  }
}

export function syncTreeSelection(): void {
  document.querySelectorAll("sl-tree-item").forEach((item) => {
    const el = item as HTMLElement;
    const selected = el.dataset.path === state.treeSelectedPath;
    (item as any).selected = selected;
    el.classList.toggle("tree-selected", selected);
  });
}
