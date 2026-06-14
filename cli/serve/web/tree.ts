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
    (item as any).selected = (item as HTMLElement).dataset.path === state.selectedPath;
  });
}
