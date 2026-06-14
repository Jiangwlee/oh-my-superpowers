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

export function websocketUrl(path: string): string {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${window.location.host}${withProject(path)}`;
}
