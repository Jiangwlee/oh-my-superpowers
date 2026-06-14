// Project registry CRUD. GET lists, POST adds a directory (sandboxed to $HOME),
// DELETE unregisters (never deletes files).
import type { ServerResponse } from "node:http";
import { sendJson, sendErrorJson } from "../sse.js";
import { listProjects, addProject, removeProject } from "../projects/registry.js";

export function handleProjectsList(res: ServerResponse): void {
  sendJson(res, { projects: listProjects() });
}

export function handleProjectAdd(res: ServerResponse, body: string): void {
  let payload: { path?: unknown };
  try {
    payload = JSON.parse(body) as { path?: unknown };
  } catch {
    sendErrorJson(res, 400, "invalid json");
    return;
  }
  const path = String(payload.path ?? "").trim();
  if (!path) {
    sendErrorJson(res, 400, "path is required");
    return;
  }
  try {
    const project = addProject(path, new Date().toISOString());
    sendJson(res, { project });
  } catch (exc) {
    sendErrorJson(res, 400, String((exc as Error)?.message || exc));
  }
}

export function handleProjectRemove(res: ServerResponse, id: string): void {
  if (!id) {
    sendErrorJson(res, 400, "id is required");
    return;
  }
  const result = removeProject(id);
  if (result === "not_found") {
    sendErrorJson(res, 404, "unknown project");
    return;
  }
  if (result === "last") {
    sendErrorJson(res, 409, "cannot remove the last project");
    return;
  }
  sendJson(res, { ok: true, id });
}
