import type { ServerResponse } from "node:http";
import type { ProjectContext } from "../config.js";
import { sendJson } from "../sse.js";

export function handleMeta(res: ServerResponse, ctx: ProjectContext): void {
  sendJson(res, {
    workspace: ctx.workspace,
    model: ctx.model,
    sessionMode: "page-local",
  });
}
