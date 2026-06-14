// Project registry: the source of truth for which directories `omp serve` can
// serve. Persisted to ~/.omp/serve/projects.json (user-level, intentionally
// outside the install dir and outside any single workspace). The frontend keeps
// a localStorage mirror for fast restore but reconciles against this on boot —
// this file wins.
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync, renameSync, unlinkSync, statSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { basename, join, resolve } from "node:path";
import type { Config, ProjectContext } from "../config.js";
import { contextFor } from "../config.js";
import { isSafe } from "../fs/workspace.js";

export interface Project {
  id: string;
  name: string;
  path: string;
  addedAt: string;
}

interface RegistryFile {
  projects: Project[];
}

const REGISTRY_DIR = join(homedir(), ".omp", "serve");
const REGISTRY_PATH = join(REGISTRY_DIR, "projects.json");

// Stable id from the canonical absolute path, so re-adding the same directory
// (even via a different relative spelling) maps to the same project.
function projectId(absPath: string): string {
  return createHash("sha1").update(absPath).digest("hex").slice(0, 12);
}

function isDir(p: string): boolean {
  try {
    return statSync(p).isDirectory();
  } catch {
    return false;
  }
}

function readRegistry(): RegistryFile {
  try {
    const data = JSON.parse(readFileSync(REGISTRY_PATH, "utf-8")) as RegistryFile;
    if (Array.isArray(data?.projects)) return { projects: data.projects };
  } catch {
    /* missing or corrupt: start empty */
  }
  return { projects: [] };
}

// Atomic write: a reader sharing ~/.omp/serve/projects.json across processes
// never observes a half-truncated file. (Cross-process lost-update on a manual
// add is still possible but rare and non-corrupting.)
function writeRegistry(reg: RegistryFile): void {
  mkdirSync(REGISTRY_DIR, { recursive: true });
  const tmp = `${REGISTRY_PATH}.${process.pid}.tmp`;
  writeFileSync(tmp, JSON.stringify(reg, null, 2), "utf-8");
  try {
    renameSync(tmp, REGISTRY_PATH);
  } catch (exc) {
    try {
      unlinkSync(tmp); // don't leave a stale temp file behind
    } catch {
      /* best effort */
    }
    throw exc;
  }
}

// Canonical real path: a stored project root must contain no symlink component,
// so it cannot be retargeted outside the sandbox after registration.
function realCanonical(p: string): string {
  return realpathSync(resolve(p));
}

export function listProjects(): Project[] {
  return readRegistry().projects;
}

export function getProject(id: string): Project | undefined {
  return readRegistry().projects.find((p) => p.id === id);
}

// Register an absolute directory as a project. The path must be a real
// directory inside $HOME (the browse/add sandbox). Idempotent: re-adding an
// existing path returns the existing entry. Returns the project; throws on a
// path that escapes the sandbox or is not a directory.
export function addProject(absPath: string, addedAt: string): Project {
  const lexical = resolve(absPath);
  const home = homedir();
  if (!isDir(lexical)) throw new Error("not a directory");
  // Store the fully-resolved real path (no symlink components) so a symlink
  // that is safe at add time cannot be retargeted outside $HOME afterwards.
  const target = realCanonical(lexical);
  if (!isSafe(home, target)) throw new Error("path is outside the home sandbox");
  const reg = readRegistry();
  const id = projectId(target);
  const existing = reg.projects.find((p) => p.id === id);
  if (existing) return existing;
  const project: Project = { id, name: basename(target) || target, path: target, addedAt };
  reg.projects.push(project);
  writeRegistry(reg);
  return project;
}

export type RemoveResult = "ok" | "not_found" | "last";

// Unregister a project. This only removes the registry entry — project files
// are never touched (the directory belongs to the user, not to omp serve).
// Refuses to remove the last project so the registry never empties (authoritative
// even if a second tab bypasses the frontend's own guard).
export function removeProject(id: string): RemoveResult {
  const reg = readRegistry();
  if (!reg.projects.some((p) => p.id === id)) return "not_found";
  if (reg.projects.length <= 1) return "last";
  writeRegistry({ projects: reg.projects.filter((p) => p.id !== id) });
  return "ok";
}

// Ensure the CLI --workspace is registered so the page always has at least one
// project on first run. Called once at server start.
export function ensureBootstrap(workspace: string): Project {
  const target = realCanonical(workspace);
  const reg = readRegistry();
  const id = projectId(target);
  const existing = reg.projects.find((p) => p.id === id);
  if (existing) return existing;
  const project: Project = {
    id,
    name: basename(target) || target,
    path: target,
    addedAt: new Date().toISOString(),
  };
  reg.projects.push(project);
  writeRegistry(reg);
  return project;
}

// Resolve the project-scoped context for a request. An explicit projectId must
// exist in the registry; an empty projectId (only requests issued before the
// page loads the project list) resolves to the first registered project so a
// removed/unregistered directory is never served — the registry stays the SoT.
// Throws on unknown project, empty registry, vanished path, or a path that has
// since escaped the $HOME sandbox.
export function resolveContext(cfg: Config, projectId: string): ProjectContext {
  let workspace: string;
  if (projectId) {
    const project = getProject(projectId);
    if (!project) throw new Error("unknown project");
    workspace = project.path;
  } else {
    const first = readRegistry().projects[0];
    if (!first) throw new Error("no project registered");
    workspace = first.path;
  }
  if (!isDir(workspace)) throw new Error("project path not found");
  // Re-canonicalize and re-check the sandbox on every request: a stored path
  // whose target was retargeted outside $HOME after registration is rejected.
  const real = realCanonical(workspace);
  if (!isSafe(homedir(), real)) throw new Error("project path escaped sandbox");
  return contextFor(real, cfg.model);
}
