// What changed (S048): the version at the bottom of the sidebar opens the change log for IT Admin
// and Admin (settings:edit); everyone else sees plain text.  The sidebar is hidden on phones, so
// these tests run on desktop only (they are layout-dependent by device: @device).
import { readFileSync } from "node:fs";
import { test, expect } from "./support/test.js";
import { asPerson } from "./support/people.js";

const DESKTOP = "desktop-chromium";
const VERSION = readFileSync(new URL("../../VERSION", import.meta.url), "utf-8").trim();

const footer = (page) => page.locator(".sidebar-footer");

for (const key of ["it_admin", "admin"]) {
  test(`S048: ${key} opens the change log from the version in the sidebar`, { tag: "@device" }, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== DESKTOP, "the sidebar is hidden on phones");
    await asPerson(page, key, "/equipment");
    const button = footer(page).getByRole("button", { name: `v${VERSION}` });
    await expect(button).toBeVisible();
    await button.click();

    const dialog = page.getByRole("dialog", { name: "What changed in Yantra" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { name: new RegExp(`^v${VERSION.replaceAll(".", "\\.")} `) })).toBeVisible();
    await expect(dialog.getByText("This version")).toBeVisible();
    const close = dialog.getByRole("button", { name: "Close" });
    await expect(close).toBeInViewport();
    await close.click();
    await expect(dialog).toBeHidden();
  });
}

test("S048: a manager sees the version as plain text, not a button", { tag: "@device" }, async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== DESKTOP, "the sidebar is hidden on phones");
  await asPerson(page, "manager", "/equipment");
  await expect(footer(page)).toHaveText(`v${VERSION}`);
  await expect(footer(page).getByRole("button")).toHaveCount(0);
});
