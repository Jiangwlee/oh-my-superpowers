// GET /api/browse?path=<abs> -> immediate subdirectories of a directory, for
// the "+ add project" picker. The browse root is $HOME; any path outside it is
// rejected. Only directories are returned (you pick a directory to make it a
// project).
import type { ServerResponse } from "node:http";
import { homedir } from "node:os";
import { dirname, resolve } from "node:path";
import { sendJson, sendErrorJson } from "../sse.js";
import { isSafe, listSubdirectories } from "../fs/workspace.js";

export function handleBrowse(res: ServerResponse, rawPath: string): void {
  const home = homedir();
  const target = rawPath ? resolve(rawPath) : home;
  if (!isSafe(home, target)) {
    sendErrorJson(res, 400, "path is outside the home sandbox");
    return;
  }
  let entries: { name: string; path: string }[];
  try {
    entries = listSubdirectories(home, target);
  } catch (exc) {
    sendErrorJson(res, 400, String((exc as Error)?.message || exc));
    return;
  }
  // Parent is null at the sandbox root so the picker cannot navigate above $HOME.
  const parent = isSafe(home, target) && target !== home ? dirname(target) : null;
  sendJson(res, { path: target, parent, home, entries });
}
