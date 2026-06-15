import type { ServerResponse } from "node:http";
import { readFileSync, statSync } from "node:fs";
import { dirname, extname } from "node:path";
import type { ProjectContext } from "../config.js";
import { resolveRel } from "../fs/workspace.js";
import { sendErrorJson } from "../sse.js";

const RAW_TYPES: Record<string, string> = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".htm": "text/html; charset=utf-8",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function contentType(path: string): string {
  return RAW_TYPES[extname(path).toLowerCase()] || "application/octet-stream";
}

function isFile(path: string): boolean {
  try {
    return statSync(path).isFile();
  } catch {
    return false;
  }
}

function injectBase(html: string, baseHref: string): string {
  const base = `<base href="${baseHref}">`;
  if (/<base\s/i.test(html)) return html;
  if (/<head[^>]*>/i.test(html)) return html.replace(/<head[^>]*>/i, (match) => `${match}\n${base}`);
  return `${base}\n${html}`;
}

export function handleHtmlPreview(res: ServerResponse, ctx: ProjectContext, projectId: string, rel: string): void {
  const path = resolveRel(ctx.workspace, rel);
  if (!isFile(path)) {
    sendErrorJson(res, 404, "file not found");
    return;
  }
  const ext = extname(path).toLowerCase();
  if (ext !== ".html" && ext !== ".htm") {
    sendErrorJson(res, 400, "not an html file");
    return;
  }
  const dir = dirname(rel).replace(/\\/g, "/");
  const rawBase = `/api/raw/${encodeURIComponent(projectId)}/${dir === "." ? "" : `${dir.split("/").map(encodeURIComponent).join("/")}/`}`;
  const html = injectBase(readFileSync(path, "utf-8"), rawBase);
  const body = Buffer.from(html, "utf-8");
  res.writeHead(200, {
    "Content-Type": "text/html; charset=utf-8",
    "Content-Length": String(body.length),
    "Cache-Control": "no-store",
  });
  res.end(body);
}

export function handleRawFile(res: ServerResponse, ctx: ProjectContext, rel: string): void {
  const path = resolveRel(ctx.workspace, rel);
  if (!isFile(path)) {
    sendErrorJson(res, 404, "file not found");
    return;
  }
  const body = readFileSync(path);
  res.writeHead(200, {
    "Content-Type": contentType(path),
    "Content-Length": String(body.length),
    "Cache-Control": "no-store",
  });
  res.end(body);
}
