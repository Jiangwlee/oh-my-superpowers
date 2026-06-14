#!/usr/bin/env node
// esbuild prebuild: bundles the node server and the browser web app, copies static assets.
import { build } from "esbuild";
import { mkdir, copyFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const r = (...p) => resolve(root, ...p);

async function run() {
  await mkdir(r("server/dist"), { recursive: true });
  await mkdir(r("web/dist"), { recursive: true });

  // Server: node ESM bundle. node builtins stay external.
  await build({
    entryPoints: [r("server/index.ts")],
    outfile: r("server/dist/index.js"),
    platform: "node",
    format: "esm",
    target: "node22",
    bundle: true,
    sourcemap: true,
    packages: "external",
  });

  // Web: browser bundle (IIFE, no module loader needed in the page).
  await build({
    entryPoints: [r("web/main.ts")],
    outfile: r("web/dist/bundle.js"),
    platform: "browser",
    format: "iife",
    target: "es2022",
    bundle: true,
    sourcemap: true,
  });

  // Static assets copied alongside the web bundle.
  await copyFile(r("web/index.html"), r("web/dist/index.html"));
  await copyFile(r("web/styles.css"), r("web/dist/styles.css"));

  console.log("build complete");
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
