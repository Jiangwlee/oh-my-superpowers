import type { ServerResponse } from "node:http";
import { statSync, lstatSync, readFileSync, openSync, writeSync, ftruncateSync, closeSync, constants as fsConstants, rmSync, unlinkSync } from "node:fs";
import type { ProjectContext } from "../config.js";
import { sendJson, sendErrorJson } from "../sse.js";
import { resolveRel, readTextFile } from "../fs/workspace.js";

const MAX_IMAGE_PREVIEW_BYTES = 25 * 1024 * 1024;
const IMAGE_MIME_BY_EXT = new Map<string, string>([
  [".gif", "image/gif"],
  [".jpeg", "image/jpeg"],
  [".jpg", "image/jpeg"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".webp", "image/webp"],
]);

function isFile(p: string): boolean {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

function extOf(p: string): string {
  const idx = p.lastIndexOf(".");
  return idx === -1 ? "" : p.slice(idx).toLowerCase();
}

export function handleFileGet(res: ServerResponse, ctx: ProjectContext, rel: string): void {
  const path = resolveRel(ctx.workspace, rel);
  if (!isFile(path)) {
    sendErrorJson(res, 404, "file not found");
    return;
  }
  const st = statSync(path);
  const imageMime = IMAGE_MIME_BY_EXT.get(extOf(path));
  if (imageMime) {
    if (st.size > MAX_IMAGE_PREVIEW_BYTES) {
      sendJson(res, { path: rel, kind: "meta", size: st.size, message: "image too large to preview" });
      return;
    }
    const data = readFileSync(path).toString("base64");
    sendJson(res, { path: rel, kind: "image", mimeType: imageMime, dataUrl: `data:${imageMime};base64,${data}`, size: st.size });
    return;
  }
  const content = readTextFile(path);
  sendJson(res, { path: rel, kind: "text", content, size: st.size });
}

export function handleFilePut(res: ServerResponse, ctx: ProjectContext, body: string): void {
  const payload = JSON.parse(body) as { path?: unknown; content?: unknown };
  const rel = String(payload.path ?? "");
  const content = String(payload.content ?? "");
  const path = resolveRel(ctx.workspace, rel);
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

export function handleFileDelete(res: ServerResponse, ctx: ProjectContext, rel: string): void {
  if (!rel) {
    sendErrorJson(res, 400, "path is required");
    return;
  }
  const path = resolveRel(ctx.workspace, rel);
  let st;
  try {
    st = lstatSync(path);
  } catch {
    sendErrorJson(res, 404, "file not found");
    return;
  }
  if (st.isDirectory()) rmSync(path, { recursive: true, force: false });
  else unlinkSync(path);
  sendJson(res, { ok: true, path: rel });
}
