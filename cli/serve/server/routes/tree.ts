import type { ServerResponse } from "node:http";
import type { Config } from "../config.js";
import { sendJson } from "../sse.js";
import { listDirectory } from "../fs/workspace.js";

export function handleTree(res: ServerResponse, cfg: Config, rel: string): void {
  const nodes = listDirectory(cfg.workspace, rel);
  sendJson(res, { path: rel, nodes, count: nodes.length });
}
