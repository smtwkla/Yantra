// The Documents and photos page of help/ (S103 § 1): upload through the real dialogs with a small
// PDF and a photo made by tooling/help/make_photo.py, so the shots show real rows. Runs in order:
// the model's document first, so the machine's card shows its group "From model …".
import path from "node:path";
import { devices, expect, test } from "@playwright/test";
import { asPerson, closeDialog, DATA, dialogOpen, OUT, shot, shotOf } from "./shot.js";

const FILES = path.join(OUT, "files");
const REPORT = path.join(FILES, "compressor-test-report.pdf");
const OLD_REPORT = path.join(FILES, "old-test-report.pdf");
const PHOTO = path.join(FILES, "compressor-nameplate.jpg");
const MANUAL = path.join(FILES, "ga37-manual.pdf");
const BASE_URL = "http://127.0.0.1:5189";

const card = (page, title) => page.locator(".card").filter({ has: page.locator(".card-header", { hasText: title }) }).first();

/** Choose a file in the open upload dialog and set its title. */
async function fillUpload(page, file, title) {
  const dialog = await dialogOpen(page);
  await dialog.locator("#doc-file").setInputFiles(file);
  await dialog.locator("#doc-title").fill(title);
  return dialog;
}

async function upload(page, file, title) {
  const dialog = await fillUpload(page, file, title);
  await dialog.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
}

test("documents: the model's documents (desktop)", async ({ browser }) => {
  const context = await browser.newContext({
    ...devices["Desktop Chrome"], viewport: { width: 1366, height: 768 }, deviceScaleFactor: 1.5,
    baseURL: BASE_URL, timezoneId: "Asia/Kolkata", locale: "en-IN", serviceWorkers: "block",
  });
  const page = await context.newPage();
  await asPerson(page, "engineer", "/masters");
  await page.getByRole("button", { name: "Models", exact: true }).filter({ visible: true }).first().click();
  const row = page.locator("tr").filter({ hasText: "GA37" }).first();
  await shot(page, "doc-01-models-documents-button-desktop");
  await row.getByRole("button", { name: "Documents" }).click();
  await page.getByRole("button", { name: "Add document" }).click();
  const dialog = await fillUpload(page, MANUAL, "GA37 instruction manual");
  await shotOf(page, dialog, "doc-02-model-add-document-dialog-desktop");
  await dialog.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(page.getByText("GA37 instruction manual")).toBeVisible();
  await shot(page, "doc-03-model-documents-desktop");
  await context.close();
});

test("documents: a machine's documents and photos (phone)", async ({ page }) => {
  await asPerson(page, "engineer", `/equipment/${DATA.ids["Screw compressor 1"]}`);
  await card(page, "Documents").scrollIntoViewIfNeeded();
  await shotOf(page, card(page, "Documents"), "doc-04-machine-documents-empty-phone");

  await page.getByRole("button", { name: "Add document" }).click();
  const dialog = await fillUpload(page, REPORT, "Compressor 1 test report");
  await shot(page, "doc-05-add-document-dialog-phone");
  await dialog.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(page.getByText("Compressor 1 test report")).toBeVisible();
  await upload_second(page);
  await card(page, "Documents").scrollIntoViewIfNeeded();
  await shotOf(page, card(page, "Documents"), "doc-06-machine-documents-phone");

  const reportRow = page.locator(".list-group-item").filter({ hasText: "Compressor 1 test report" });
  await reportRow.getByRole("button", { name: "More actions" }).click();
  await shotOf(page, card(page, "Documents"), "doc-07-document-more-actions-phone");
  await page.keyboard.press("Escape");
  const oldRow = page.locator(".list-group-item").filter({ hasText: "Old test report" });
  await oldRow.getByRole("button", { name: "More actions" }).click();
  await oldRow.getByRole("button", { name: "Remove" }).click();
  await expect(page.getByText("Remove this document?")).toBeVisible();
  await shotOf(page, card(page, "Documents"), "doc-08-remove-document-confirm-phone");
  await oldRow.getByRole("button", { name: "Yes" }).click();
  await expect(oldRow).toHaveCount(0);

  await page.getByRole("button", { name: "Add photo" }).click();
  const photoDialog = await fillUpload(page, PHOTO, "Nameplate");
  await shot(page, "doc-09-add-photo-dialog-phone");
  await photoDialog.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(card(page, "Photos").locator("img")).toBeVisible();
  await card(page, "Photos").scrollIntoViewIfNeeded();
  await shotOf(page, card(page, "Photos"), "doc-10-machine-photos-phone");
  await closeDialog(page);
});

async function upload_second(page) {
  await page.getByRole("button", { name: "Add document" }).click();
  await upload(page, OLD_REPORT, "Old test report");
  await expect(page.getByText("Old test report")).toBeVisible();
}

test("documents: removed documents (desktop)", async ({ browser }) => {
  const context = await browser.newContext({
    ...devices["Desktop Chrome"], viewport: { width: 1366, height: 768 }, deviceScaleFactor: 1.5,
    baseURL: BASE_URL, timezoneId: "Asia/Kolkata", locale: "en-IN", serviceWorkers: "block",
  });
  const page = await context.newPage();
  await asPerson(page, "it_admin", "/settings");
  const removed = card(page, "Removed documents");
  await expect(removed.getByText("Old test report")).toBeVisible();
  await removed.scrollIntoViewIfNeeded();
  await shotOf(page, removed, "doc-11-removed-documents-desktop");
  await removed.getByRole("button", { name: "Delete for good" }).first().click();
  await expect(removed.getByText("Delete for good? The file cannot be recovered.")).toBeVisible();
  await shotOf(page, removed, "doc-12-removed-delete-confirm-desktop");
  await context.close();
});
