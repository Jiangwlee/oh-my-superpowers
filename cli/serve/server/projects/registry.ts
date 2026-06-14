// Project registry: the source of truth for which directories `omp serve` can
// serve. Persisted to ~/.omp/serve/projects.json (user-level, intentionally
// outside the install dir and outside any single workspace). The frontend keeps
// a localStorage mirror for fast restore but reconciles against this on boot —
// this file wins.
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
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

function writeRegistry(reg: RegistryFile): void {
  mkdirSync(REGISTRY_DIR, { recursive: true });
  writeFileSync(REGISTRY_PATH, JSON.stringify(reg, null, 2), "utf-8");
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
  const target = resolve(absPath);
  const home = homedir();
  if (!isSafe(home, target)) throw new Error("path is outside the home sandbox");
  if (!isDir(target)) throw new Error("not a directory");
  const reg = readRegistry();
  const id = projectId(target);
  const existing = reg.projects.find((p) => p.id === id);
  if (existing) return existing;
  const project: Project = { id, name: basename(target) || target, path: target, addedAt };
  reg.projects.push(project);
  writeRegistry(reg);
  return project;
}

// Unregister a project. This only removes the registry entry — project files
// are never touched (the directory belongs to the user, not to omp serve).
export function removeProject(id: string): boolean {
  const reg = readRegistry();
  const next = reg.projects.filter((p) => p.id !== id);
  if (next.length === reg.projects.length) return false;
  writeRegistry({ projects: next });
  return true;
}

// Ensure the CLI --workspace is registered so the page always has at least one
// project on first run. Called once at server start.
export function ensureBootstrap(workspace: string): Project {
  const target = resolve(workspace);
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

// Resolve the project-scoped context for a request. Empty projectId falls back
// to the bootstrap workspace (back-compat for requests issued before the page
// has loaded the project list). Throws on an unknown or vanished project so the
// route returns a clean error instead of silently serving the wrong tree.
export function resolveContext(cfg: Config, projectId: string): ProjectContext {
  let workspace = cfg.bootstrapWorkspace;
  if (projectId) {
    const project = getProject(projectId);
    if (!project) throw new Error("unknown project");
    workspace = project.path;
  }
  if (!isDir(workspace)) throw new Error("project path not found");
  return contextFor(workspace, cfg.model);
}
