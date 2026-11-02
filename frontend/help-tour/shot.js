import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import { expect } from "@playwright/test";
export { asPerson, apiAs, personId } from "../e2e/support/people.js";
export { openDialog } from "../e2e/support/dialogs.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
// Everything the tour writes is under scratch/help-shots/ (S103 D4)
export const OUT = path.join(HERE, "..", "..", "scratch", "help-shots");
export const SHOTS = path.join(OUT, "shots");
export const DATA = JSON.parse(fs.readFileSync(path.join(OUT, "data.json"), "utf-8"));

/** Wait until the page has settled: no spinner, no request in flight, fonts loaded. */
export async function settle(page) {
  await page.waitForLoadState("networkidle").catch(() => {});
  await expect(page.locator(".spinner-border:visible")).toHaveCount(0, { timeout: 15_000 }).catch(() => {});
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
}

/** Screenshot to scratch/help-shots/shots/<name>.png; `full` takes the full page up to `maxHeight` CSS px. */
export async function shot(page, name, { full = false, maxHeight = 1200, scrollTop = true } = {}) {
  await settle(page);
  const file = path.join(SHOTS, `${name}.png`);
  if (full) {
    const height = await page.evaluate(() => {
      const main = document.querySelector("main.app-content");
      return Math.max(document.documentElement.scrollHeight, main ? main.scrollHeight + main.getBoundingClientRect().top : 0);
    });
    const vp = page.viewportSize();
    const h = Math.min(height, maxHeight);
    if (h > vp.height) {
      await page.setViewportSize({ width: vp.width, height: h });
      await settle(page);
      await page.screenshot({ path: file });
      await page.setViewportSize(vp);
      return;
    }
  }
  await page.screenshot({ path: file });
}

/** The open dialog once it is fully shown. */
export async function dialogOpen(page) {
  const d = page.locator(".modal.show .modal-dialog");
  await expect(d).toBeVisible();
  await page.waitForTimeout(600);
  return d;
}

/** Try an action; on a failure the tour goes on (the shot is still taken) and the test fails at its end,
 *  naming the label, so a wrong shot is never published silently (S103 CR1-04). */
export async function tryDo(label, fn) {
  try {
    await fn();
  } catch (e) {
    console.log(`TRY FAILED ${label}: ${e.message.split("\n")[0]}`);
    expect.soft(false, `tour action failed: ${label}`).toBe(true);
  }
}

export async function closeDialog(page) {
  const d = page.locator(".modal.show");
  if (!(await d.count())) return;
  await d.locator(".modal-footer").getByRole("button", { name: "Cancel" }).click({ timeout: 3000 }).catch(() => {});
  const discard = d.getByRole("button", { name: "Discard", exact: true });
  if (await discard.isVisible().catch(() => false)) await discard.click().catch(() => {});
  await expect(page.locator(".modal.show")).toHaveCount(0, { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(300);
}

/** Screenshot of one element (a card, a dialog) to scratch/help-shots/shots/<name>.png. */
export async function shotOf(page, locator, name) {
  await settle(page);
  await locator.screenshot({ path: path.join(SHOTS, `${name}.png`) });
}
