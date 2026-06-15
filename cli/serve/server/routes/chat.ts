import { statSync } from "node:fs";
import type { ServerResponse } from "node:http";
import type { ProjectContext } from "../config.js";
import { resolveRel } from "../fs/workspace.js";
import { handleChat } from "../pi/runChat.js";
import { sendErrorJson } from "../sse.js";

function validateAttachments(ctx: ProjectContext, value: unknown): string[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > 20) return null;
  const out: string[] = [];
  for (const item of value) {
    const rel = String(item ?? "").trim().replace(/^\/+/, "");
    if (!rel) return null;
    const abs = resolveRel(ctx.workspace, rel);
    try {
      if (!statSync(abs).isFile()) return null;
    } catch {
      return null;
    }
    out.push(rel);
  }
  return [...new Set(out)];
}

// POST /api/chat body parsing + validation (mirrors main.py do_POST).
export function handleChatRoute(res: ServerResponse, ctx: ProjectContext, body: string): void {
  let payload: { message?: unknown; sessionId?: unknown; attachments?: unknown };
  try {
    payload = JSON.parse(body) as { message?: unknown; sessionId?: unknown; attachments?: unknown };
  } catch {
    sendErrorJson(res, 400, "invalid json");
    return;
  }
  const message = String(payload.message ?? "").trim();
  const sessionId = String(payload.sessionId ?? "").trim();
  const attachments = validateAttachments(ctx, payload.attachments);
  if (!message && (!attachments || attachments.length === 0)) {
    sendErrorJson(res, 400, "message is required");
    return;
  }
  if (!sessionId) {
    sendErrorJson(res, 400, "sessionId is required");
    return;
  }
  if (attachments === null) {
    sendErrorJson(res, 400, "invalid attachments");
    return;
  }
  handleChat(res, ctx, message || "Please use the attached files for this request.", sessionId, attachments);
}
