// Fetch wrappers — every request is scoped to the current project via a
// `project` query param so the single server resolves the right workspace.
import { state } from "./state.js";

// Append the current project id to a same-origin path. Management endpoints
// (/api/projects, /api/browse) ignore it, so attaching it unconditionally is
// harmless and keeps every data request project-scoped.
export function withProject(path: string): string {
  if (!state.currentProjectId) return path;
  const u = new URL(path, window.location.origin);
  u.searchParams.set("project", state.currentProjectId);
  return u.pathname + u.search;
}

export async function api(path: string, options?: RequestInit): Promise<Response> {
  const res = await fetch(withProject(path), options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res;
}

export async function loadDirectory(path: string): Promise<any> {
  const data = await (await api(`/api/tree?path=${encodeURIComponent(path || "")}`)).json();
  return data;
}

export async function uploadFiles(files: File[], directory = ""): Promise<string[]> {
  const form = new FormData();
  form.set("directory", directory);
  for (const file of files) form.append("files", file);
  const data = await (await api("/api/files/upload", { method: "POST", body: form })).json();
  return Array.isArray(data.files) ? data.files : [];
}

export async function deletePath(path: string): Promise<void> {
  await api(`/api/file?path=${encodeURIComponent(path)}`, { method: "DELETE" });
}

export async function searchFiles(query: string): Promise<{ path: string; name: string }[]> {
  const data = await (await api(`/api/files/search?q=${encodeURIComponent(query)}`)).json();
  return Array.isArray(data.files) ? data.files : [];
}

export function htmlPreviewUrl(path: string): string {
  return withProject(`/api/preview/html?path=${encodeURIComponent(path)}`);
}

export function rawFileUrl(path: string): string {
  const encoded = path.split("/").map(encodeURIComponent).join("/");
  return `/api/raw/${encodeURIComponent(state.currentProjectId)}/${encoded}`;
}

// The id of the current project's most recently used session, or null when it
// has no prior sessions. Used to resume the last conversation instead of always
// opening a blank session on page load / first project switch.
export async function latestSession(): Promise<string | null> {
  try {
    const data = await (await api("/api/sessions/latest")).json();
    return typeof data.sessionId === "string" ? data.sessionId : null;
  } catch {
    return null;
  }
}

export function websocketUrl(path: string): string {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${window.location.host}${withProject(path)}`;
}
