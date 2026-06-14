import type { ServerResponse } from "node:http";
import type { ProjectContext } from "../config.js";
import { sendErrorJson } from "../sse.js";
import { handleChat } from "../pi/runChat.js";

// POST /api/chat body parsing + validation (mirrors main.py do_POST).
export function handleChatRoute(res: ServerResponse, ctx: ProjectContext, body: string): void {
  let payload: { message?: unknown; sessionId?: unknown };
  try {
    payload = JSON.parse(body) as { message?: unknown; sessionId?: unknown };
  } catch {
    sendErrorJson(res, 400, "invalid json");
    return;
  }
  const message = String(payload.message ?? "").trim();
  const sessionId = String(payload.sessionId ?? "").trim();
  if (!message) {
    sendErrorJson(res, 400, "message is required");
    return;
  }
  if (!sessionId) {
    sendErrorJson(res, 400, "sessionId is required");
    return;
  }
  handleChat(res, ctx, message, sessionId);
}
