// The Mermaid diagrams of a Markdown file render (the architecture doc; 11-11-2026, by KLA).
// Each ```mermaid block is drawn by the browser tests' Chromium (frontend/node_modules/playwright),
// so a syntax error is found before a reader sees an error box instead of a picture.
//
//   node tooling/architecture/check_diagrams.mjs docs/Architecture.md
//
// The Mermaid library: frontend/node_modules/mermaid when the app has it; else the cached copy in
// scratch/mermaid/; else the pinned package is fetched once from the npm registry, its SHA-512 is
// checked against the integrity npm publishes for that version, and dist/mermaid.min.js is cached.
// Exit 0: every diagram rendered; 1: a diagram failed, or the file has none; 2: the check could
// not run (no Playwright, the library could not be fetched).
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { gunzipSync } from "node:zlib";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const require = createRequire(path.join(ROOT, "frontend", "package.json"));

export const MERMAID_VERSION = "11.4.1";
// npm's dist.integrity for mermaid@11.4.1 (registry.npmjs.org/mermaid/11.4.1).
export const MERMAID_INTEGRITY =
  "sha512-Mb01JT/x6CKDWaxigwfZYuYmDZ6xtrNwNlidKZwkSrDaY9n90tdrJTV5Umk+wP1fZscGptmKFXHsXMDEVZ+Q6A==";
const TARBALL = `https://registry.npmjs.org/mermaid/-/mermaid-${MERMAID_VERSION}.tgz`;
const LIB_IN_TAR = "package/dist/mermaid.min.js";

/** Every ```mermaid block of a Markdown text: its first line number (1-based) and its source. */
export function mermaidBlocks(text) {
  const blocks = [];
  let open = null;
  text.split(/\r?\n/).forEach((line, index) => {
    if (open === null && /^\s*```+\s*mermaid\s*$/i.test(line)) {
      open = { line: index + 1, lines: [] };
    } else if (open !== null && /^\s*```+\s*$/.test(line)) {
      blocks.push({ line: open.line, source: open.lines.join("\n") });
      open = null;
    } else if (open !== null) {
      open.lines.push(line);
    }
  });
  return blocks;
}

/** One file's bytes from an uncompressed tar archive (ustar headers), or null. */
export function fileFromTar(tar, wanted) {
  let offset = 0;
  while (offset + 512 <= tar.length) {
    const header = tar.subarray(offset, offset + 512);
    if (header.every((byte) => byte === 0)) break;
    const field = (start, length) => header.subarray(start, start + length).toString("utf8").replace(/\0.*$/s, "");
    const prefix = field(345, 155);
    const name = prefix ? `${prefix}/${field(0, 100)}` : field(0, 100);
    const size = parseInt(field(124, 12).trim() || "0", 8);
    if (name === wanted) return tar.subarray(offset + 512, offset + 512 + size);
    offset += 512 + Math.ceil(size / 512) * 512;
  }
  return null;
}

async function mermaidLibrary(request) {
  const own = path.join(ROOT, "frontend", "node_modules", "mermaid", "dist", "mermaid.min.js");
  if (existsSync(own)) return own;
  const cached = path.join(ROOT, "scratch", "mermaid", `mermaid-${MERMAID_VERSION}.min.js`);
  if (existsSync(cached)) return cached;
  const context = await request.newContext();
  try {
    const response = await context.get(TARBALL);
    if (!response.ok()) throw new Error(`${TARBALL} answered ${response.status()}`);
    const tgz = await response.body();
    const integrity = `sha512-${createHash("sha512").update(tgz).digest("base64")}`;
    if (integrity !== MERMAID_INTEGRITY) throw new Error(`${TARBALL} does not match its published SHA-512`);
    const lib = fileFromTar(gunzipSync(tgz), LIB_IN_TAR);
    if (!lib) throw new Error(`${LIB_IN_TAR} is not in ${TARBALL}`);
    mkdirSync(path.dirname(cached), { recursive: true });
    writeFileSync(cached, lib);
    return cached;
  } finally {
    await context.dispose();
  }
}

async function main(file) {
  if (!file) {
    console.log("Name the Markdown file, e.g. node tooling/architecture/check_diagrams.mjs docs/Architecture.md");
    return 2;
  }
  const blocks = mermaidBlocks(readFileSync(path.resolve(file), "utf8"));
  if (!blocks.length) {
    console.log(`${file} has no mermaid diagram.`);
    return 1;
  }
  let playwright;
  try {
    playwright = require("playwright");
  } catch (err) {
    if (err.code !== "MODULE_NOT_FOUND" && err.code !== "ERR_MODULE_NOT_FOUND") throw err;
    console.log("Playwright is not installed in frontend/. The diagram check needs the browser tests' Playwright.");
    return 2;
  }
  let lib;
  try {
    lib = await mermaidLibrary(playwright.request);
  } catch (err) {
    console.log(`The Mermaid library could not be loaded: ${err.message.split("\n")[0]}`);
    return 2;
  }
  const browser = await playwright.chromium.launch();
  try {
    const page = await browser.newPage();
    await page.addScriptTag({ path: lib });
    const results = await page.evaluate(async (sources) => {
      window.mermaid.initialize({ startOnLoad: false });
      const out = [];
      for (const [index, source] of sources.entries()) {
        try {
          await window.mermaid.parse(source);
          await window.mermaid.render(`diagram${index}`, source);
          out.push(null);
        } catch (error) {
          out.push(String(error && error.message ? error.message : error).split("\n").slice(0, 3).join(" | "));
        }
      }
      return out;
    }, blocks.map((block) => block.source));
    let failed = 0;
    results.forEach((error, index) => {
      if (error) failed += 1;
      console.log(`line ${blocks[index].line}: ${error ? `FAILED: ${error}` : "ok"}`);
    });
    console.log(`${blocks.length - failed} of ${blocks.length} diagrams rendered (Mermaid ${MERMAID_VERSION}).`);
    return failed ? 1 : 0;
  } finally {
    await browser.close();
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv[2]).then((code) => process.exit(code));
}
