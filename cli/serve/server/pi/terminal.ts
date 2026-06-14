// WS /ws/terminal: minimal WebSocket server (no ws library, no native deps)
// that spawns pty_helper.py and bridges ws<->stdio. Ported from main.py
// _handle_terminal_ws + _run_terminal_socket, but the PTY lives in Python.
import type { IncomingMessage } from "node:http";
import type { Duplex } from "node:stream";
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import type { Config } from "../config.js";
import { PTY_HELPER_PATH } from "../config.js";

const WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

function sessionPathValid(id: string): boolean {
  return /^[A-Za-z0-9._-]{8,80}$/.test(id);
}

// Encode a text frame (opcode 0x1), unmasked (server->client).
function encodeTextFrame(text: string): Buffer {
  const payload = Buffer.from(text, "utf-8");
  const len = payload.length;
  let header: Buffer;
  if (len < 126) {
    header = Buffer.from([0x81, len]);
  } else if (len < 65536) {
    header = Buffer.alloc(4);
    header[0] = 0x81;
    header[1] = 126;
    header.writeUInt16BE(len, 2);
  } else {
    header = Buffer.alloc(10);
    header[0] = 0x81;
    header[1] = 127;
    header.writeBigUInt64BE(BigInt(len), 2);
  }
  return Buffer.concat([header, payload]);
}

const CLOSE_FRAME = Buffer.from([0x88, 0x00]);

// Incremental client-frame parser. Returns parsed frames and keeps a residual.
interface ParsedFrame {
  opcode: number;
  payload: Buffer;
}

function parseFrames(buf: Buffer): { frames: ParsedFrame[]; rest: Buffer } {
  const frames: ParsedFrame[] = [];
  let offset = 0;
  while (offset + 2 <= buf.length) {
    const b0 = buf[offset];
    const b1 = buf[offset + 1];
    const opcode = b0 & 0x0f;
    const masked = (b1 & 0x80) !== 0;
    let length = b1 & 0x7f;
    let cursor = offset + 2;
    if (length === 126) {
      if (cursor + 2 > buf.length) break;
      length = buf.readUInt16BE(cursor);
      cursor += 2;
    } else if (length === 127) {
      if (cursor + 8 > buf.length) break;
      length = Number(buf.readBigUInt64BE(cursor));
      cursor += 8;
    }
    let mask: Buffer = Buffer.alloc(0);
    if (masked) {
      if (cursor + 4 > buf.length) break;
      mask = buf.subarray(cursor, cursor + 4);
      cursor += 4;
    }
    if (cursor + length > buf.length) break;
    let payload = buf.subarray(cursor, cursor + length);
    if (masked) {
      const unmasked = Buffer.allocUnsafe(length);
      for (let i = 0; i < length; i++) unmasked[i] = payload[i] ^ mask[i % 4];
      payload = unmasked;
    }
    frames.push({ opcode, payload: Buffer.from(payload) });
    offset = cursor + length;
  }
  return { frames, rest: Buffer.from(buf.subarray(offset)) };
}

export function handleTerminalUpgrade(
  req: IncomingMessage,
  socket: Duplex,
  cfg: Config,
): void {
  const key = req.headers["sec-websocket-key"];
  const upgrade = String(req.headers["upgrade"] || "").toLowerCase();
  if (upgrade !== "websocket" || !key) {
    socket.write("HTTP/1.1 400 Bad Request\r\n\r\n");
    socket.destroy();
    return;
  }
  const accept = createHash("sha1").update(key + WS_GUID).digest("base64");
  socket.write(
    "HTTP/1.1 101 Switching Protocols\r\n" +
      "Upgrade: websocket\r\n" +
      "Connection: Upgrade\r\n" +
      `Sec-WebSocket-Accept: ${accept}\r\n\r\n`,
  );

  const url = new URL(req.url || "/", "http://localhost");
  const sessionId = url.searchParams.get("sessionId") || "";

  const sendText = (text: string): void => {
    if (!socket.destroyed) socket.write(encodeTextFrame(text));
  };
  const closeSocket = (): void => {
    if (!socket.destroyed) {
      socket.write(CLOSE_FRAME);
      socket.end();
    }
  };

  if (!sessionId) {
    sendText("sessionId is required\r\n");
    closeSocket();
    return;
  }
  if (!sessionPathValid(sessionId)) {
    sendText("invalid session id\r\n");
    closeSocket();
    return;
  }

  const sessionPath = `${cfg.sessionsDir}/${sessionId}.jsonl`;
  const helper = spawn(
    "python3",
    [PTY_HELPER_PATH, "--session", sessionPath, "--model", cfg.model, "--cwd", cfg.workspace],
    { stdio: ["pipe", "pipe", "inherit"] },
  );

  helper.on("error", (err) => {
    sendText(`pty helper failed: ${String(err)}\r\n`);
    closeSocket();
  });

  // helper stdout: newline-delimited JSON -> ws text / close.
  let outBuf = "";
  helper.stdout.setEncoding("utf-8");
  helper.stdout.on("data", (chunk: string) => {
    outBuf += chunk;
    const lines = outBuf.split("\n");
    outBuf = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      let msg: { type?: string; data?: string };
      try {
        msg = JSON.parse(line) as { type?: string; data?: string };
      } catch {
        continue;
      }
      if (msg.type === "output" && typeof msg.data === "string") sendText(msg.data);
      else if (msg.type === "exit") closeSocket();
    }
  });

  helper.on("close", () => {
    closeSocket();
  });

  // ws client frames -> helper stdin (input/resize pass straight through).
  let inBuf: Buffer = Buffer.alloc(0);
  const sendToHelper = (obj: unknown): void => {
    if (helper.stdin.writable) helper.stdin.write(JSON.stringify(obj) + "\n");
  };
  socket.on("data", (data: Buffer) => {
    inBuf = Buffer.concat([inBuf, data]);
    const { frames, rest } = parseFrames(inBuf);
    inBuf = rest;
    for (const frame of frames) {
      if (frame.opcode === 0x8) {
        // close
        try {
          helper.kill("SIGTERM");
        } catch {
          /* ignore */
        }
        closeSocket();
        return;
      }
      if (frame.opcode !== 0x1) continue; // only text
      let event: { type?: string; data?: string; rows?: number; cols?: number };
      try {
        event = JSON.parse(frame.payload.toString("utf-8"));
      } catch {
        continue;
      }
      if (event.type === "input" || event.type === "resize") sendToHelper(event);
    }
  });

  const cleanup = (): void => {
    try {
      if (helper.exitCode === null) helper.kill("SIGTERM");
    } catch {
      /* ignore */
    }
  };
  socket.on("close", cleanup);
  socket.on("error", cleanup);
}
