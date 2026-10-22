// expectDialogFits(page) — the open dialog fits the screen (S024 § 1.4): its Save and Cancel
// lie inside the viewport, and the dialog is no taller than the viewport (a long one scrolls
// inside, FormModal's modal-dialog-scrollable).  Called by the flow tests on every dialog
// they open; it waits out Bootstrap's open animation.
import { expect } from "@playwright/test";

const TOLERANCE = 1; // px: sub-pixel rounding

function inside(box, viewport) {
  return box.x >= -TOLERANCE && box.y >= -TOLERANCE
    && box.x + box.width <= viewport.width + TOLERANCE && box.y + box.height <= viewport.height + TOLERANCE;
}

/**
 * The open dialog (Bootstrap's .modal.show .modal-dialog), once it is fully open (S026 A1).
 * Bootstrap adds `show` when the fade starts; at its end (shown.bs.modal) the focus trap moves
 * focus into the modal, and text typed before that is lost (seen on WebKit under load).  So wait
 * until the focus is inside the modal.  A dialog opened by a click may be typed into only after this.
 */
export async function openDialog(page) {
  const dialog = page.locator(".modal.show .modal-dialog");
  await expect(dialog).toBeVisible();
  await page.waitForFunction(() => {
    const modal = document.querySelector(".modal.show");
    return modal !== null && modal.contains(document.activeElement);
  }, undefined, { timeout: 5_000 });
  return dialog;
}

export async function expectDialogFits(page) {
  const dialog = await openDialog(page);
  const viewport = page.viewportSize();
  const save = dialog.locator(".modal-footer button[type=submit]");
  const cancel = dialog.locator(".modal-footer").getByRole("button", { name: "Cancel" });
  await expect(async () => {
    const [dialogBox, saveBox, cancelBox] = await Promise.all([dialog.boundingBox(), save.boundingBox(), cancel.boundingBox()]);
    expect(dialogBox.height, "dialog taller than the screen").toBeLessThanOrEqual(viewport.height + TOLERANCE);
    expect(inside(saveBox, viewport), `Save off screen: ${JSON.stringify(saveBox)}`).toBe(true);
    expect(inside(cancelBox, viewport), `Cancel off screen: ${JSON.stringify(cancelBox)}`).toBe(true);
  }).toPass({ timeout: 5_000 });
}

/**
 * The screen does not scroll sideways (a phone check): the page is no wider than the viewport,
 * and the scrolling main area fits its own width.  The page is measured against the viewport
 * Playwright set, not the window's clientWidth: Playwright's WebKit on Windows scales the
 * window by the display's scaling (125 % gives a 312 px window for a 390 px iPhone).
 */
export async function expectNoSidewaysScroll(page) {
  const overflow = await page.evaluate(() => {
    const main = document.querySelector("main.app-content");
    return {
      pageWidth: document.documentElement.scrollWidth,
      main: main ? main.scrollWidth - main.clientWidth : 0,
    };
  });
  expect(overflow.pageWidth, "the page scrolls sideways").toBeLessThanOrEqual(page.viewportSize().width + TOLERANCE);
  expect(overflow.main, "the screen scrolls sideways").toBeLessThanOrEqual(TOLERANCE);
}

/**
 * A refusal shown beside its field and on screen, not only in the page (S026: "A refusal is always
 * in view").  `scope`: the page or the open dialog; `text` exact, or a RegExp.  A dialog's body
 * scrolls, so a message below the fold is visible to Playwright but not on screen.
 */
export async function expectFieldMessage(scope, text) {
  const message = scope.getByText(text, { exact: typeof text === "string" });
  await expect(message).toBeInViewport();
}
