// S064 floor UX: dialogs full screen on a phone (UX-01), the top bar's name and Sign out (UX-02),
// Masters in the nav for its editors only (UX-12), the bottom bar by keyboard (UX-22), and a
// dropped connection's plain message (UX-06).
import { test, expect } from "./support/test.js";
import { openDialog } from "./support/dialogs.js";
import { asPerson } from "./support/people.js";
import { navItem } from "./support/nav.js";

const SM = 576; // Bootstrap's sm: below it a dialog is the whole screen

/** The open dialog is the whole screen, and its body is the part that scrolls. */
async function expectFullScreenDialog(page) {
  const dialog = await openDialog(page);
  const box = await dialog.boundingBox();
  const viewport = page.viewportSize();
  expect(Math.abs(box.width - viewport.width), "the dialog is narrower than the screen").toBeLessThanOrEqual(1);
  expect(Math.abs(box.height - viewport.height), "the dialog is shorter than the screen").toBeLessThanOrEqual(1);
  const overflow = await dialog.locator(".modal-body").evaluate((el) => getComputedStyle(el).overflowY);
  expect(overflow).toBe("auto");
  await dialog.locator(".modal-footer").getByRole("button", { name: "Cancel" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
}

test("S064: on a phone the Equipment and Team dialogs are full screen and their body scrolls", { tag: "@device" }, async ({ page }) => {
  test.skip(page.viewportSize().width >= SM, "a dialog is full screen below sm only");
  await asPerson(page, "engineer", "/equipment");
  await page.getByRole("button", { name: "Add equipment" }).click();
  await expectFullScreenDialog(page);

  await page.goto("/masters");
  await page.getByRole("button", { name: "Team", exact: true }).click();
  await page.getByRole("button", { name: "Add person" }).click();
  await expectFullScreenDialog(page);
});

test("S064: the top bar shows the name and a Sign out button with its word, at least 44 px high", { tag: "@device" }, async ({ page }) => {
  const me = await asPerson(page, "operator", "/me");
  const bar = page.locator(".topbar").filter({ visible: true });
  await expect(bar.locator('[data-test="user-name"]')).toHaveText(me.name);
  const signOut = bar.getByRole("button", { name: "Sign out" });
  await expect(signOut).toHaveText("Sign out");
  await expect(signOut).toBeInViewport({ ratio: 1 });
  const box = await signOut.boundingBox();
  expect(box.height, "Sign out is lower than 44 px").toBeGreaterThanOrEqual(44);
});

test("S064: an operator's nav has no Masters and /masters lands on Me; an engineer's nav has Masters", async ({ page }) => {
  await asPerson(page, "operator", "/me");
  await expect(navItem(page, "Me")).toBeVisible();
  await expect(navItem(page, "Masters")).toHaveCount(0);
  await page.goto("/masters");
  await expect(page).toHaveURL(/\/me(\?|$)/);

  await asPerson(page, "engineer", "/me");
  await expect(navItem(page, "Masters")).toBeVisible();
  await navItem(page, "Masters").click();
  await expect(page).toHaveURL(/\/masters$/);
});

test("S064: a dropped connection shows the plain no-connection text", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/equipment", "ERR_FAILED");
  await page.route("**/api/equipment?**", (route) => route.abort("failed"));
  await asPerson(page, "operator", "/equipment");
  await expect(page.getByText("No connection. Check Wi-Fi or mobile data and try again.")).toBeVisible();
  await expect(page.getByText("Failed to fetch")).toHaveCount(0);
});

// The bottom bar is a phone's (hidden on a desktop); this runs on the logic device, phone-chromium
test("S064: the bottom bar is reached by Tab and opens with Enter", async ({ page }) => {
  await asPerson(page, "operator", "/me");
  const bar = page.locator(".app-bottom-nav");
  test.skip(!(await bar.isVisible()), "the bottom bar is a phone's");
  const MAX_TABS = 30;
  let reached = false;
  for (let i = 0; i < MAX_TABS && !reached; i += 1) {
    await page.keyboard.press("Tab");
    reached = await page.evaluate(() => document.activeElement?.closest(".app-bottom-nav") !== null
      && document.activeElement.textContent.trim() === "Tickets");
  }
  expect(reached, "Tab never reached the bottom bar's Tickets item").toBe(true);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/tickets(\?|$)/);
});
