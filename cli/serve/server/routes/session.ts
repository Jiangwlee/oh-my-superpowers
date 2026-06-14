// GET /api/session?sessionId=X -> the past turns of a pi session jsonl, so the
// chat panel can repaint history when a project (and its session) is resumed.
// pi keeps full context via --session; this only rebuilds the visible transcript.
import type { ServerResponse } from "node:http";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { ProjectContext } from "../config.js";
import { sendJson } from "../sse.js";

interface Turn {
  role: "user" | "assistant";
  text: string;
}

// Extract the concatenated visible text of a pi message's content parts.
// Thinking and tool parts are skipped — the transcript shows user/assistant
// prose, matching what the live stream renders into the chat panel.
function visibleText(content: unknown): string {
  if (!Array.isArray(content)) return "";
  return content
    .filter((p): p is { type: string; text: string } =>
      !!p && (p as { type?: unknown }).type === "text" && typeof (p as { text?: unknown }).text === "string",
    )
    .map((p) => p.text)
    .join("");
}

export function handleSessionHistory(res: ServerResponse, ctx: ProjectContext, sessionId: string): void {
  // Invalid id or missing file is not an error: a fresh session simply has no
  // history. Return an empty transcript so the caller renders a clean panel.
  if (!/^[A-Za-z0-9._-]{8,80}$/.test(sessionId)) {
    sendJson(res, { turns: [] });
    return;
  }
  let raw: string;
  try {
    raw = readFileSync(join(ctx.sessionsDir, `${sessionId}.jsonl`), "utf-8");
  } catch {
    sendJson(res, { turns: [] });
    return;
  }
  const turns: Turn[] = [];
  for (const line of raw.split("\n")) {
    if (!line.trim()) continue;
    let rec: { type?: string; message?: unknown };
    try {
      rec = JSON.parse(line);
    } catch {
      continue;
    }
    if (rec.type !== "message") continue;
    let msg = rec.message;
    if (typeof msg === "string") {
      try {
        msg = JSON.parse(msg);
      } catch {
        continue;
      }
    }
    const role = (msg as { role?: unknown })?.role;
    if (role !== "user" && role !== "assistant") continue;
    const text = visibleText((msg as { content?: unknown }).content);
    if (!text.trim()) continue; // skip thinking-only / tool-only turns
    turns.push({ role, text });
  }
  sendJson(res, { turns });
}
