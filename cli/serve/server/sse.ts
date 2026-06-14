// SSE (text/event-stream) response helpers.
import type { ServerResponse } from "node:http";

export function startSse(res: ServerResponse): void {
  res.writeHead(200, {
    "Content-Type": "text/event-stream; charset=utf-8",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });
}

export function sendSse(res: ServerResponse, payload: unknown): void {
  res.write(`data: ${JSON.stringify(payload)}\n\n`);
}

export function sendJson(res: ServerResponse, payload: unknown, status = 200): void {
  const body = Buffer.from(JSON.stringify(payload), "utf-8");
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": String(body.length),
  });
  res.end(body);
}

export function sendErrorJson(res: ServerResponse, status: number, message: string): void {
  try {
    sendJson(res, { error: message }, status);
  } catch {
    /* client disconnected */
  }
}
