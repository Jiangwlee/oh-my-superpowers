import type { ServerResponse } from "node:http";
import { lstatSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import type { ProjectContext } from "../config.js";
import { DEFAULT_IGNORES, isSafe } from "../fs/workspace.js";
import { sendJson } from "../sse.js";

const MAX_DEPTH = 8;
const MAX_RESULTS = 50;

interface Match {
  path: string;
  name: string;
  score: number;
}

function visible(name: string): boolean {
  return !name.startsWith(".") && !DEFAULT_IGNORES.has(name);
}

function fuzzyScore(text: string, query: string): number {
  let score = 0;
  let pos = -1;
  let streak = 0;
  for (const ch of query) {
    const idx = text.indexOf(ch, pos + 1);
    if (idx === -1) return 0;
    streak = idx === pos + 1 ? streak + 1 : 1;
    score += 8 + streak * 4;
    if (idx === 0 || "/_- .".includes(text[idx - 1] ?? "")) score += 6;
    pos = idx;
  }
  return score - Math.min(text.length - query.length, 80) * 0.2;
}

function score(rel: string, query: string): number {
  const lower = rel.toLowerCase();
  const name = rel.split("/").pop()?.toLowerCase() ?? lower;
  if (!query) return 1;
  if (name === query) return 100;
  if (name.startsWith(query)) return 80;
  if (lower.startsWith(query)) return 70;
  if (name.includes(query)) return 50;
  if (lower.includes(query)) return 30;
  const nameScore = fuzzyScore(name, query);
  const pathScore = fuzzyScore(lower, query);
  return Math.max(nameScore ? 20 + nameScore : 0, pathScore ? 10 + pathScore : 0);
}

function walk(workspace: string, dir: string, relDir: string, query: string, out: Match[], depth: number): void {
  if (out.length >= MAX_RESULTS * 4 || depth > MAX_DEPTH) return;
  let names: string[];
  try {
    names = readdirSync(dir);
  } catch {
    return;
  }
  for (const name of names) {
    if (!visible(name)) continue;
    const abs = join(dir, name);
    if (!isSafe(workspace, abs)) continue;
    let lst;
    try {
      lst = lstatSync(abs);
    } catch {
      continue;
    }
    const rel = relDir ? `${relDir}/${name}` : name;
    if (lst.isSymbolicLink()) {
      let st;
      try {
        st = statSync(abs);
      } catch {
        continue;
      }
      if (st.isDirectory()) walk(workspace, abs, rel, query, out, depth + 1);
      else if (st.isFile()) {
        const s = score(rel, query);
        if (s > 0) out.push({ path: rel, name, score: s });
      }
      continue;
    }
    if (lst.isDirectory()) walk(workspace, abs, rel, query, out, depth + 1);
    else if (lst.isFile()) {
      const s = score(rel, query);
      if (s > 0) out.push({ path: rel, name, score: s });
    }
  }
}

export function handleFileSearch(res: ServerResponse, ctx: ProjectContext, query: string): void {
  const q = query.trim().toLowerCase();
  const matches: Match[] = [];
  walk(ctx.workspace, ctx.workspace, "", q, matches, 0);
  matches.sort((a, b) => b.score - a.score || a.path.localeCompare(b.path));
  sendJson(res, { files: matches.slice(0, MAX_RESULTS).map(({ path, name }) => ({ path, name })) });
}
