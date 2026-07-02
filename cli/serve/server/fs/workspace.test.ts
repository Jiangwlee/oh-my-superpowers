import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { isVisibleEntry, listDirectory } from "./workspace.ts";

test("visible entries include underscore-prefixed names", () => {
  assert.equal(isVisibleEntry("_candidates"), true);
  assert.equal(isVisibleEntry(".hidden"), false);
  assert.equal(isVisibleEntry("node_modules"), false);
});

test("file tree lists underscore-prefixed directories", () => {
  const root = mkdtempSync(join(tmpdir(), "omp-serve-tree-"));
  mkdirSync(join(root, "_candidates"));
  writeFileSync(join(root, "_candidates", "draft.md"), "# draft\n");
  mkdirSync(join(root, ".hidden"));
  mkdirSync(join(root, "node_modules"));

  const nodes = listDirectory(root, "");
  assert.ok(nodes.some((node) => node.type === "directory" && node.name === "_candidates"));
  assert.ok(!nodes.some((node) => node.name === ".hidden"));
  assert.ok(!nodes.some((node) => node.name === "node_modules"));
});
