import type { IncomingMessage, ServerResponse } from "node:http";
import { constants as fsConstants, existsSync, mkdirSync, openSync, writeSync, closeSync } from "node:fs";
import { basename, extname, join, relative, sep } from "node:path";
import { Readable } from "node:stream";
import type { ProjectContext } from "../config.js";
import { sendJson, sendErrorJson } from "../sse.js";
import { resolveRel } from "../fs/workspace.js";

const MAX_UPLOAD_FILE_SIZE_BYTES = 100 * 1024 * 1024;
const BLOCKED_EXTENSIONS = new Set([".exe", ".bat", ".cmd", ".msi", ".dmg", ".app"]);
const BLOCKED_MIME_TYPES = new Set([
  "application/vnd.microsoft.portable-executable",
  "application/x-apple-diskimage",
  "application/x-msdownload",
  "application/x-msdos-program",
  "application/x-msi",
  "application/x-ms-installer",
]);

function requestHeaders(req: IncomingMessage): Headers {
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (Array.isArray(value)) headers.set(key, value.join(", "));
    else if (value !== undefined) headers.set(key, value);
  }
  return headers;
}

function isUploadFile(entry: FormDataEntryValue): entry is File {
  return (
    typeof entry === "object" &&
    entry !== null &&
    "name" in entry &&
    typeof entry.name === "string" &&
    "size" in entry &&
    typeof entry.size === "number" &&
    "arrayBuffer" in entry &&
    typeof entry.arrayBuffer === "function"
  );
}

function validateUploadFile(file: File): { ok: true } | { ok: false; status: number; error: string } {
  if (file.size > MAX_UPLOAD_FILE_SIZE_BYTES) return { ok: false, status: 413, error: "file too large" };
  const extension = extname(file.name).toLowerCase();
  const mimeType = file.type.toLowerCase();
  if (BLOCKED_EXTENSIONS.has(extension) || BLOCKED_MIME_TYPES.has(mimeType)) {
    return { ok: false, status: 400, error: "file type is not allowed" };
  }
  return { ok: true };
}

function cleanFileName(name: string): string {
  const cleaned = basename(name.replace(/\\/g, "/")).trim();
  return cleaned && cleaned !== "." && cleaned !== ".." ? cleaned : "upload.bin";
}

function availableUploadPath(directory: string, filename: string): string {
  const extension = extname(filename);
  const stem = extension ? filename.slice(0, -extension.length) : filename;
  for (let index = 0; index < 10_000; index += 1) {
    const candidate = index === 0 ? filename : `${stem} (${index})${extension}`;
    const target = join(directory, candidate);
    if (!existsSync(target)) return target;
  }
  throw new Error("unable to allocate upload path");
}

function toRel(workspace: string, target: string): string {
  return relative(workspace, target).split(sep).join("/");
}

async function parseForm(req: IncomingMessage): Promise<FormData> {
  const request = new Request("http://localhost/api/files/upload", {
    method: "POST",
    headers: requestHeaders(req),
    body: Readable.toWeb(req) as BodyInit,
    duplex: "half",
  } as RequestInit & { duplex: "half" });
  return request.formData();
}

export async function handleFileUpload(req: IncomingMessage, res: ServerResponse, ctx: ProjectContext): Promise<void> {
  const form = await parseForm(req);
  const directoryRel = String(form.get("directory") ?? "").replace(/^\/+|\/+$/g, "");
  const directory = resolveRel(ctx.workspace, directoryRel);
  const uploads = form.getAll("files").filter(isUploadFile);
  if (uploads.length === 0) {
    sendErrorJson(res, 400, "no files uploaded");
    return;
  }

  for (const file of uploads) {
    const validation = validateUploadFile(file);
    if (!validation.ok) {
      sendErrorJson(res, validation.status, validation.error);
      return;
    }
  }

  if (!existsSync(directory) && directoryRel !== "uploads") {
    sendErrorJson(res, 404, "directory not found");
    return;
  }
  mkdirSync(directory, { recursive: true });
  const noFollow = (fsConstants as Record<string, number>).O_NOFOLLOW ?? 0;
  const created: string[] = [];
  for (const file of uploads) {
    const filename = cleanFileName(file.name);
    const target = availableUploadPath(directory, filename);
    const buffer = Buffer.from(await file.arrayBuffer());
    const fd = openSync(target, fsConstants.O_WRONLY | fsConstants.O_CREAT | fsConstants.O_EXCL | noFollow, 0o666);
    try {
      writeSync(fd, buffer, 0, buffer.length);
    } finally {
      closeSync(fd);
    }
    created.push(toRel(ctx.workspace, target));
  }
  sendJson(res, { ok: true, files: created });
}
