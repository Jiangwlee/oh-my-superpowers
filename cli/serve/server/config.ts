// Server configuration: port/host/model/workspace and derived paths.
// Paths resolve relative to the tool dir (this file's location), not cwd.
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";

// At runtime this module is bundled into server/dist/index.js, so the tool
// dir (cli/serve/) is two levels up from the bundle's directory.
const TOOL_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
// extensions/render_ui.ts lives next to the tool dir (cli/serve/extensions/).
export const RENDER_UI_EXTENSION_PATH = join(TOOL_DIR, "extensions", "render_ui.ts");
// pty_helper.py lives in the tool dir.
export const PTY_HELPER_PATH = join(TOOL_DIR, "pty_helper.py");
// Static web bundle output.
export const WEB_DIST_DIR = join(TOOL_DIR, "web", "dist");

// Server-level config: fixed for the lifetime of the process. The workspace a
// request operates on is no longer global — it is resolved per request from the
// `project` query param (see resolveContext in projects/registry.ts). The CLI
// `--workspace` becomes the bootstrap project that is auto-registered on start.
export interface Config {
  host: string;
  port: number;
  model: string;
  bootstrapWorkspace: string;
}

// Per-request, project-scoped view. Every file/tree/diff/chat/terminal handler
// takes one of these instead of the global Config so a single server can serve
// many projects concurrently (multi-tab safe).
export interface ProjectContext {
  workspace: string;
  sessionDir: string;
  sessionsDir: string;
  model: string;
}

function argValue(name: string, fallback: string): string {
  const flag = `--${name}`;
  const idx = process.argv.indexOf(flag);
  if (idx !== -1 && idx + 1 < process.argv.length) return process.argv[idx + 1];
  return fallback;
}

export function loadConfig(): Config {
  const bootstrapWorkspace = resolve(argValue("workspace", process.cwd()));
  const host = argValue("host", "0.0.0.0");
  const port = Number(argValue("port", "8765"));
  const model = argValue(
    "model",
    process.env.OMP_DEFAULT_MODEL_PI || "openai-codex/gpt-5.4-mini",
  );
  return { host, port, model, bootstrapWorkspace };
}

// Derive the project-scoped session dirs for a given workspace.
export function contextFor(workspace: string, model: string): ProjectContext {
  const sessionDir = join(workspace, ".omp", "serve");
  return { workspace, sessionDir, sessionsDir: join(sessionDir, "sessions"), model };
}
