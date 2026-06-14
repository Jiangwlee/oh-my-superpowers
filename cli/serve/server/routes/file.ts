import type { ServerResponse } from "node:http";
import { statSync, openSync, writeSync, ftruncateSync, closeSync, constants as fsConstants } from "node:fs";
import type { Config } from "../config.js";
import { sendJson, sendErrorJson } from "../sse.js";
import { resolveRel, readTextFile } from "../fs/workspace.js";

function isFile(p: string): boolean {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

export function handleFileGet(res: ServerResponse, cfg: Config, rel: string): void {
  const path = resolveRel(cfg.workspace, rel);
  if (!isFile(path)) {
    sendErrorJson(res, 404, "file not found");
    return;
  }
  const content = readTextFile(path);
  sendJson(res, { path: rel, content });
}

export function handleFilePut(res: ServerResponse, cfg: Config, body: string): void {
  const payload = JSON.parse(body) as { path?: unknown; content?: unknown };
  const rel = String(payload.path ?? "");
  const content = String(payload.content ?? "");
  const path = resolveRel(cfg.workspace, rel);
  if (!isFile(path)) {
    sendErrorJson(res, 404, "file not found");
    return;
  }
  // Open the guarded path with O_NOFOLLOW so the object we write is the object
  // that was just checked: if a workspace-writable process swaps the path to a
  // symlink between the isFile check and the open, the open fails (ELOOP)
  // rather than following the symlink outside the workspace. fd-based write/
  // truncate then operates on that exact object (path-escape redline guard).
  const noFollow = (fsConstants as Record<string, number>).O_NOFOLLOW ?? 0;
  let fd: number;
  try {
    fd = openSync(path, fsConstants.O_WRONLY | noFollow);
  } catch {
    sendErrorJson(res, 404, "file not found");
    return;
  }
  try {
    ftruncateSync(fd, 0);
    writeSync(fd, content, 0, "utf-8");
  } finally {
    closeSync(fd);
  }
  sendJson(res, { ok: true, path: rel });
}
