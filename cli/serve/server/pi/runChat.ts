// POST /api/chat -> spawn pi, stream JSONL stdout, map to SSE.
// Ported 1:1 from main.py do_POST / _stream_pi.
import type { ServerResponse } from "node:http";
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import type { Config } from "../config.js";
import { RENDER_UI_EXTENSION_PATH } from "../config.js";
import { startSse, sendSse } from "../sse.js";
import { createPiLineMapper, truncate } from "./events.js";

function sessionPath(cfg: Config, sessionId: string): string {
  if (!/^[A-Za-z0-9._-]{8,80}$/.test(sessionId)) throw new Error("invalid session id");
  return join(cfg.sessionsDir, `${sessionId}.jsonl`);
}

// shlex.quote/join equivalent for the exec log line.
function shquote(s: string): string {
  if (s === "") return "''";
  if (/^[A-Za-z0-9_@%+=:,./-]+$/.test(s)) return s;
  return `'${s.replace(/'/g, "'\\''")}'`;
}

export function handleChat(
  res: ServerResponse,
  cfg: Config,
  message: string,
  sessionId: string,
): void {
  startSse(res);
  // Per-stream pi-event mapper so concurrent chats never share render_ui state.
  const mapper = createPiLineMapper();
  // Set once the client disconnects; guards against write-after-end/closed.
  let clientClosed = false;
  const send = (payload: unknown): void => {
    if (clientClosed || res.writableEnded || res.destroyed) return;
    sendSse(res, payload);
  };

  const session = sessionPath(cfg, sessionId);
  mkdirSync(cfg.sessionsDir, { recursive: true });

  const cmd = [
    "pi",
    "-p",
    "--mode",
    "json",
    "--approve",
    "--extension",
    RENDER_UI_EXTENSION_PATH,
    "--session",
    session,
    "--model",
    cfg.model,
    message,
  ];

  // Log the full command executed (prompt truncated for readability).
  const logCmd = cmd.slice(0, -1).map(shquote).join(" ");
  console.error(`[omp serve] exec: ${logCmd} ${shquote(truncate(message, 80))}`);

  const proc = spawn(cmd[0], cmd.slice(1), {
    cwd: cfg.workspace,
    stdio: ["ignore", "pipe", "pipe"],
  });

  proc.on("error", (err: NodeJS.ErrnoException) => {
    if (err.code === "ENOENT") {
      send({ type: "error", message: "pi binary not found in PATH" });
    } else {
      send({ type: "error", message: String(err.message || err) });
    }
    if (!res.writableEnded) res.end();
  });

  const stderrLines: string[] = [];
  proc.stderr.setEncoding("utf-8");
  let stderrBuf = "";
  proc.stderr.on("data", (chunk: string) => {
    stderrBuf += chunk;
    const lines = stderrBuf.split("\n");
    stderrBuf = lines.pop() || "";
    for (const l of lines) stderrLines.push(l.replace(/\s+$/, ""));
  });

  let sentDone = false;
  let stdoutBuf = "";
  proc.stdout.setEncoding("utf-8");

  const processLine = (raw: string): void => {
    const { events, done } = mapper.mapPiLine(raw);
    for (const ev of events) send(ev);
    if (done && !sentDone) {
      sentDone = true;
      // agent_end seen: terminate pi promptly (mirror proc.terminate path).
      if (proc.exitCode === null) {
        proc.kill("SIGTERM");
        setTimeout(() => {
          if (proc.exitCode === null) proc.kill("SIGKILL");
        }, 2000);
      }
    }
  };

  proc.stdout.on("data", (chunk: string) => {
    if (sentDone) return;
    stdoutBuf += chunk;
    const lines = stdoutBuf.split("\n");
    stdoutBuf = lines.pop() || "";
    for (const line of lines) {
      if (sentDone) break;
      processLine(line);
    }
  });

  proc.on("close", (code) => {
    if (!sentDone && stdoutBuf.trim()) processLine(stdoutBuf);
    const rc = code ?? 0;
    if (rc !== 0 && !sentDone) {
      const detail = stderrLines.slice(-8).join("\n") || `pi exited with ${rc}`;
      send({ type: "error", message: detail });
    }
    if (!sentDone) send({ type: "done", returncode: rc });
    if (!res.writableEnded) res.end();
  });

  // Client disconnected: kill pi.
  res.on("close", () => {
    clientClosed = true;
    if (proc.exitCode === null) {
      proc.kill("SIGTERM");
      setTimeout(() => {
        if (proc.exitCode === null) proc.kill("SIGKILL");
      }, 2000);
    }
  });
}
