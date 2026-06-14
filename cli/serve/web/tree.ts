// Shoelace file tree: lazy load + selection. Ported 1:1 from APP_HTML.
import { state, $ } from "./state.js";
import { loadDirectory } from "./api.js";

export async function loadTree(): Promise<void> {
  const tree = $("file-tree");
  const data = await loadDirectory("");
  tree.innerHTML = "";
  $("tree-count").textContent = String(data.count);
  for (const node of data.nodes) tree.appendChild(createTreeItem(node));
}

export function createTreeItem(node: any): HTMLElement {
  const item = document.createElement("sl-tree-item") as HTMLElement;
  item.textContent = node.name;
  item.title = node.path;
  item.dataset.path = node.path;
  item.dataset.type = node.type;
  item.classList.add(node.type === "directory" ? "folder" : "file");
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
    item.textContent = item.title.split("/").pop() || item.title;
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
    item.textContent = item.title.split("/").pop() || item.title;
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

export function syncTreeSelection(): void {
  document.querySelectorAll("sl-tree-item").forEach((item) => {
    (item as any).selected = (item as HTMLElement).dataset.path === state.selectedPath;
  });
}
