// omp-serve node server entry: single HTTP+WS server.
// Serves the prebuilt web bundle, the JSON/file/tree APIs, the /api/chat SSE
// stream, and the /ws/terminal WebSocket (PTY in pty_helper.py).
import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";
import { readFileSync, existsSync, statSync } from "node:fs";
import { join, normalize } from "node:path";
import { loadConfig, WEB_DIST_DIR } from "./config.js";
import type { ProjectContext } from "./config.js";
import { sendErrorJson } from "./sse.js";
import { handleMeta } from "./routes/meta.js";
import { handleTree } from "./routes/tree.js";
import { handleFileGet, handleFilePut } from "./routes/file.js";
import { handleChatRoute } from "./routes/chat.js";
import { handleDiff } from "./routes/diff.js";
import { handleSessionHistory } from "./routes/session.js";
import { handleProjectsList, handleProjectAdd, handleProjectRemove } from "./routes/projects.js";
import { handleBrowse } from "./routes/browse.js";
import { handleTerminalUpgrade } from "./pi/terminal.js";
import { ensureBootstrap, resolveContext } from "./projects/registry.js";

const cfg = loadConfig();
// Register the CLI --workspace so the page always has at least one project.
ensureBootstrap(cfg.bootstrapWorkspace);

// Resolve the project-scoped context for a request from its `project` query
// param. Throws on an unknown/vanished project; callers translate to a 400.
function ctxFor(url: URL): ProjectContext {
  return resolveContext(cfg, url.searchParams.get("project") || "");
}

const STATIC_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".ico": "image/x-icon",
};

function extOf(p: string): string {
  const i = p.lastIndexOf(".");
  return i === -1 ? "" : p.slice(i).toLowerCase();
}

function serveStatic(res: ServerResponse, pathname: string): boolean {
  // Map "/" -> index.html; reject path traversal.
  let rel = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  rel = normalize(rel);
  if (rel.startsWith("..")) {
    sendErrorJson(res, 404, "not found");
    return true;
  }
  const file = join(WEB_DIST_DIR, rel);
  if (!existsSync(file) || !statSync(file).isFile()) return false;
  const body = readFileSync(file);
  const headers: Record<string, string> = {
    "Content-Type": STATIC_TYPES[extOf(file)] || "application/octet-stream",
    "Content-Length": String(body.length),
  };
  if (extOf(file) === ".html") headers["Cache-Control"] = "no-store";
  res.writeHead(200, headers);
  res.end(body);
  return true;
}

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (c: Buffer) => chunks.push(c));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf-8")));
    req.on("error", reject);
  });
}

const server = createServer((req, res) => {
  const url = new URL(req.url || "/", "http://localhost");
  const path = url.pathname;
  const method = req.method || "GET";
  try {
    if (method === "GET") {
      if (path === "/favicon.ico" && !existsSync(join(WEB_DIST_DIR, "favicon.ico"))) {
        res.writeHead(200, { "Content-Type": "image/x-icon", "Content-Length": "0" });
        res.end();
        return;
      }
      if (path === "/api/projects") {
        handleProjectsList(res);
        return;
      }
      if (path === "/api/browse") {
        handleBrowse(res, url.searchParams.get("path") || "");
        return;
      }
      if (path === "/api/meta") {
        handleMeta(res, ctxFor(url));
        return;
      }
      if (path === "/api/tree") {
        handleTree(res, ctxFor(url), url.searchParams.get("path") || "");
        return;
      }
      if (path === "/api/file") {
        handleFileGet(res, ctxFor(url), url.searchParams.get("path") || "");
        return;
      }
      if (path === "/api/session") {
        handleSessionHistory(res, ctxFor(url), url.searchParams.get("sessionId") || "");
        return;
      }
      if (path === "/api/diff") {
        handleDiff(res, ctxFor(url)).catch((exc) =>
          sendErrorJson(res, 500, String((exc as Error)?.message || exc)),
        );
        return;
      }
      if (serveStatic(res, path)) return;
      sendErrorJson(res, 404, "not found");
      return;
    }
    if (method === "HEAD") {
      // Parity with Python do_HEAD: probe "/", "/api/meta", "/api/tree"
      // without a body. "/" reports HTML, the API routes report JSON.
      if (path === "/" || path === "/api/meta" || path === "/api/tree") {
        res.writeHead(200, {
          "Content-Type":
            path === "/"
              ? "text/html; charset=utf-8"
              : "application/json; charset=utf-8",
          "Cache-Control": "no-store",
        });
        res.end();
        return;
      }
      sendErrorJson(res, 404, "not found");
      return;
    }
    if (method === "PUT") {
      if (path === "/api/file") {
        const ctx = ctxFor(url);
        readBody(req)
          .then((body) => handleFilePut(res, ctx, body))
          .catch((exc) => sendErrorJson(res, 400, String(exc?.message || exc)));
        return;
      }
      sendErrorJson(res, 404, "not found");
      return;
    }
    if (method === "POST") {
      if (path === "/api/chat") {
        const ctx = ctxFor(url);
        readBody(req)
          .then((body) => handleChatRoute(res, ctx, body))
          .catch((exc) => sendErrorJson(res, 400, String(exc?.message || exc)));
        return;
      }
      if (path === "/api/projects") {
        readBody(req)
          .then((body) => handleProjectAdd(res, body))
          .catch((exc) => sendErrorJson(res, 400, String(exc?.message || exc)));
        return;
      }
      sendErrorJson(res, 404, "not found");
      return;
    }
    if (method === "DELETE") {
      if (path === "/api/projects") {
        handleProjectRemove(res, url.searchParams.get("id") || "");
        return;
      }
      sendErrorJson(res, 404, "not found");
      return;
    }
    sendErrorJson(res, 404, "not found");
  } catch (exc) {
    sendErrorJson(res, 400, String((exc as Error)?.message || exc));
  }
});

// WebSocket upgrade for the terminal.
server.on("upgrade", (req, socket) => {
  const url = new URL(req.url || "/", "http://localhost");
  if (url.pathname === "/ws/terminal") {
    let ctx: ProjectContext;
    try {
      ctx = ctxFor(url);
    } catch {
      socket.destroy(); // unknown/invalid project
      return;
    }
    handleTerminalUpgrade(req, socket, ctx);
  } else {
    socket.destroy();
  }
});

server.listen(cfg.port, cfg.host, () => {
  console.error(
    `[omp serve] node server on http://${cfg.host}:${cfg.port}/  workspace: ${cfg.bootstrapWorkspace}`,
  );
});
