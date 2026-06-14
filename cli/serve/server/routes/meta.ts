import type { ServerResponse } from "node:http";
import type { Config } from "../config.js";
import { sendJson } from "../sse.js";

export function handleMeta(res: ServerResponse, cfg: Config): void {
  sendJson(res, {
    workspace: cfg.workspace,
    model: cfg.model,
    sessionMode: "page-local",
  });
}
