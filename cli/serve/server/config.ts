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

export interface Config {
  host: string;
  port: number;
  model: string;
  workspace: string;
  sessionDir: string;
  sessionsDir: string;
}

function argValue(name: string, fallback: string): string {
  const flag = `--${name}`;
  const idx = process.argv.indexOf(flag);
  if (idx !== -1 && idx + 1 < process.argv.length) return process.argv[idx + 1];
  return fallback;
}

export function loadConfig(): Config {
  const workspace = resolve(argValue("workspace", process.cwd()));
  const host = argValue("host", "0.0.0.0");
  const port = Number(argValue("port", "8765"));
  const model = argValue(
    "model",
    process.env.OMP_DEFAULT_MODEL_PI || "openai-codex/gpt-5.4-mini",
  );
  const sessionDir = join(workspace, ".omp", "serve");
  const sessionsDir = join(sessionDir, "sessions");
  return { host, port, model, workspace, sessionDir, sessionsDir };
}
