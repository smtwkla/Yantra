// Screenshots of a roadmap's screen mock-ups, for its slide deck (25-10-2026, by KLA).
// Every docs/roadmap/R0N-mockups/*.html becomes a PNG beside it, rendered by the Chromium that the
// browser tests already installed (frontend/node_modules/playwright); nothing new is installed.
//
//   node tooling/roadmap/render_mockups.mjs docs/roadmap/R01-mockups
//
// A mock-up chooses its size with <meta name="mockup-viewport" content="phone|desktop">: phone is
// the Pixel 7 the logic tests use (412 x 915, scale 2), desktop 1366 x 768 (the desktop project).
// A phone mock-up needs <meta name="viewport" content="width=device-width, initial-scale=1">, as the
// app has: without it a mobile browser lays the page out 980 px wide.  The whole page is shot
// (fullPage), so a long form or report shows in one picture.
// Mock-ups load Bootstrap and the app's main.css by relative path from frontend/, so they look like
// Yantra and need no network.  Exit 0 when every file rendered, 1 otherwise.
import { readdirSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const require = createRequire(path.join(ROOT, "frontend", "package.json"));
const { chromium } = require("playwright");

export const VIEWPORTS = {
  phone: { viewport: { width: 412, height: 915 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  desktop: { viewport: { width: 1366, height: 768 }, deviceScaleFactor: 1 },
};

/** The mock-up's size from its meta tag; phone when it names none or an unknown one. */
export function viewportOf(html) {
  const match = html.match(/<meta\s+name=["']mockup-viewport["']\s+content=["'](\w+)["']/i);
  return match && VIEWPORTS[match[1].toLowerCase()] ? match[1].toLowerCase() : "phone";
}

async function main(folder) {
  if (!folder) {
    console.log("Name the mock-up folder, e.g. node tooling/roadmap/render_mockups.mjs docs/roadmap/R01-mockups");
    return 1;
  }
  const dir = path.resolve(folder);
  const files = readdirSync(dir).filter((name) => name.toLowerCase().endsWith(".html")).sort();
  if (!files.length) {
    console.log(`No .html mock-ups in ${dir}.`);
    return 1;
  }
  const browser = await chromium.launch();
  let failed = 0;
  try {
    for (const name of files) {
      const file = path.join(dir, name);
      const kind = viewportOf(readFileSync(file, "utf8"));
      const context = await browser.newContext(VIEWPORTS[kind]);
      try {
        const page = await context.newPage();
        await page.goto(pathToFileURL(file).href, { waitUntil: "load" });
        const out = file.replace(/\.html$/i, ".png");
        await page.screenshot({ path: out, fullPage: true });
        console.log(`${name} -> ${path.basename(out)} (${kind})`);
      } catch (error) {
        failed += 1;
        console.log(`${name} could not be rendered: ${error.message.split("\n")[0]}`);
      } finally {
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }
  console.log(`${files.length - failed} of ${files.length} mock-ups rendered.`);
  return failed ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv[2]).then((code) => process.exit(code));
}
