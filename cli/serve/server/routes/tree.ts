import type { ServerResponse } from "node:http";
import type { ProjectContext } from "../config.js";
import { sendJson } from "../sse.js";
import { listDirectory } from "../fs/workspace.js";

export function handleTree(res: ServerResponse, ctx: ProjectContext, rel: string): void {
  const nodes = listDirectory(ctx.workspace, rel);
  sendJson(res, { path: rel, nodes, count: nodes.length });
}
