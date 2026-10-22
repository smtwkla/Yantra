// The equipment register's dialogs on the three screen sizes (S012 manufacturers and models;
// S003 add, move and status; S006 documents: upload and title), each checked with
// expectDialogFits.  Names carry the project's name: the three projects share one database.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, openDialog } from "./support/dialogs.js";
import { apiAs, asPerson } from "./support/people.js";
import { saveDialog } from "./support/tickets.js";

const MANUAL = path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", "test-manual.pdf");

test("S012: IT admin adds a manufacturer and a model of it", async ({ page }, testInfo) => {
  const maker = `E2E maker ${testInfo.project.name}`;
  await asPerson(page, "it_admin", "/masters");
  await page.getByRole("button", { name: "Manufacturers" }).click();
  await page.getByRole("button", { name: "Add manufacturer" }).click();
  await expectDialogFits(page);
  await openDialog(page).getByLabel("Name").fill(maker);
  await saveDialog(page, "Save");
  await expect(page.getByRole("row", { name: new RegExp(maker) })).toBeVisible();

  await page.getByRole("button", { name: "Models" }).click();
  await page.getByRole("button", { name: "Add model" }).click();
  await expectDialogFits(page);
  const dialog = openDialog(page);
  await dialog.getByLabel("Manufacturer").selectOption({ label: maker });
  await dialog.locator("#model-class").selectOption({ index: 1 });
  await dialog.getByLabel("Designation").fill("X-100");
  await saveDialog(page, "Save");
  await expect(page.getByRole("row", { name: new RegExp(`${maker} X-100`) })).toBeVisible();
});

test("S003: the Add equipment dialog fits", async ({ page }) => {
  await asPerson(page, "engineer", "/equipment");
  await page.getByRole("button", { name: "Add equipment" }).click();
  await expectDialogFits(page);
  await openDialog(page).getByLabel("Site").selectOption({ label: "SMTW" });
  await expectDialogFits(page);
});

test("S026: the server's refusal of a field at the bottom of the Add equipment dialog is on screen", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/equipment", 400);
  await asPerson(page, "engineer", "/equipment");
  await page.getByRole("button", { name: "Add equipment" }).click();
  // Waits out the open animation; a fill during it can lose its text to the focus trap
  await expectDialogFits(page);
  const dialog = openDialog(page);
  await dialog.getByLabel("Site").selectOption({ label: "SMTW" });
  await dialog.getByLabel("Unit").selectOption({ label: "MCC1 — New extrusion and punching line, part 1" });
  await dialog.getByLabel("Model").selectOption({ label: "Atlas Copco GA37 — CMP / Screw compressor" });
  await dialog.getByLabel("Name").fill("E2E bad year");
  await dialog.getByLabel("Year").fill("1800");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expect(dialog.locator(".invalid-feedback.d-block")).toHaveCount(1);
  await expectFieldMessage(dialog, /Year must be between/);
  await expect(dialog.getByLabel("Year")).toBeFocused();
});

test("S003: engineer adds equipment from the list; its page opens", async ({ page }, testInfo) => {
  const name = `E2E added ${testInfo.project.name}`;
  await asPerson(page, "engineer", "/equipment");
  await page.getByRole("button", { name: "Add equipment" }).click();
  const dialog = openDialog(page);
  await dialog.getByLabel("Site").selectOption({ label: "SMTW" });
  await dialog.getByLabel("Unit").selectOption({ label: "MCC1 — New extrusion and punching line, part 1" });
  await dialog.getByLabel("Model").selectOption({ label: "Atlas Copco GA37 — CMP / Screw compressor" });
  await dialog.getByLabel("Name").fill(name);
  await saveDialog(page, "Save");
  await expect(page.getByRole("heading", { name: new RegExp(` — ${name}$`) })).toBeVisible();
  await expect(page.getByText("SMTW.MCC1").first()).toBeVisible();
});

test("S003/S006: engineer moves equipment, changes its status, uploads a document and edits its title", async ({ page }, testInfo) => {
  const node = await createEquipment(`E2E moved ${testInfo.project.name}`);
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  await expect(page.getByText("SMTW.MCC1").first()).toBeVisible();

  await page.getByRole("button", { name: "Move" }).click();
  await expectDialogFits(page);
  await openDialog(page).getByLabel("Move to unit").selectOption({ label: "SMTW.MCC2 — New extrusion and punching line, part 2" });
  await saveDialog(page, "Save");
  await expect(page.getByText("SMTW.MCC2").first()).toBeVisible();

  await page.getByRole("button", { name: "Change status" }).click();
  await expectDialogFits(page);
  await openDialog(page).getByLabel("Status").selectOption({ label: "Standby" });
  await saveDialog(page, "Save");
  await expect(page.getByText("Standby").first()).toBeVisible();

  await page.getByRole("button", { name: "Add document" }).click();
  await expectDialogFits(page);
  const dialog = openDialog(page);
  await dialog.getByLabel("File").setInputFiles(MANUAL);
  await dialog.getByLabel("Title").fill("Service manual");
  await saveDialog(page, "Upload");
  const documents = page.locator(".card", { has: page.locator(".card-header", { hasText: /^\s*Documents/ }) });
  await expect(documents).toContainText("Service manual");
  await expect(documents).toContainText("test-manual.pdf");

  await documents.getByTitle("Edit title").click();
  await expectDialogFits(page);
  await openDialog(page).getByLabel("Title").fill("Service manual, 2026 edition");
  await saveDialog(page, "Save");
  await expect(documents).toContainText("Service manual, 2026 edition");
});

/** A machine at SMTW.MCC1 made through the API as admin (the test's own record). */
async function createEquipment(name) {
  const api = await apiAs("admin");
  try {
    const units = await (await api.get("/api/masters/units")).json();
    const unit = units.items.find((u) => u.full_code === "SMTW.MCC1");
    const models = await (await api.get("/api/masters/equipment-models")).json();
    const model = models.items.find((m) => m.label === "Atlas Copco GA37");
    const res = await api.post("/api/equipment", { data: { level: "equipment", unit_id: unit.id, model_id: model.id, name } });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}
