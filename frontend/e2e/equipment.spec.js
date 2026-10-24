// The equipment register's dialogs on the three screen sizes (S012 manufacturers and models;
// S003 add, move and lifecycle, named status before S030; S006 documents: upload and title),
// each checked with expectDialogFits.  Names carry the project's name: the three projects share one database.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, openDialog } from "./support/dialogs.js";
import { apiAs, asPerson } from "./support/people.js";
import { logByApi, meterMachine } from "./support/meters.js";
import { noModelPart, propertySetup, propertyTag } from "./support/properties.js";
import { card, istLocal, raiseByApi, saveDialog, shownTime } from "./support/tickets.js";

const MANUAL = path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", "test-manual.pdf");

test("S012: IT admin adds a manufacturer and a model of it", async ({ page }, testInfo) => {
  const maker = `E2E maker ${testInfo.project.name}`;
  await asPerson(page, "it_admin", "/masters");
  await page.getByRole("button", { name: "Manufacturers" }).click();
  await page.getByRole("button", { name: "Add manufacturer" }).click();
  await expectDialogFits(page);
  await (await openDialog(page)).getByLabel("Name").fill(maker);
  await saveDialog(page, "Save");
  await expect(page.getByRole("row", { name: new RegExp(maker) })).toBeVisible();

  await page.getByRole("button", { name: "Models" }).click();
  await page.getByRole("button", { name: "Add model" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
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
  await (await openDialog(page)).getByLabel("Site").selectOption({ label: "SMTW" });
  await expectDialogFits(page);
});

test("S026: the server's refusal of a field at the bottom of the Add equipment dialog is on screen", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/equipment", 400);
  await asPerson(page, "engineer", "/equipment");
  await page.getByRole("button", { name: "Add equipment" }).click();
  // Waits out the open animation; a fill during it can lose its text to the focus trap
  await expectDialogFits(page);
  const dialog = await openDialog(page);
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
  const dialog = await openDialog(page);
  await dialog.getByLabel("Site").selectOption({ label: "SMTW" });
  await dialog.getByLabel("Unit").selectOption({ label: "MCC1 — New extrusion and punching line, part 1" });
  await dialog.getByLabel("Model").selectOption({ label: "Atlas Copco GA37 — CMP / Screw compressor" });
  await dialog.getByLabel("Name").fill(name);
  await saveDialog(page, "Save");
  await expect(page.getByRole("heading", { name: new RegExp(` — ${name}$`) })).toBeVisible();
  await expect(page.getByText("SMTW.MCC1").first()).toBeVisible();
});

test("S003/S006: engineer moves equipment, changes its lifecycle, uploads a document and edits its title", async ({ page }, testInfo) => {
  const node = await createEquipment(`E2E moved ${testInfo.project.name}`);
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  await expect(page.getByText("SMTW.MCC1").first()).toBeVisible();

  await page.getByRole("button", { name: "Move" }).click();
  await expectDialogFits(page);
  await (await openDialog(page)).getByLabel("Move to unit").selectOption({ label: "SMTW.MCC2 — New extrusion and punching line, part 2" });
  await saveDialog(page, "Save");
  await expect(page.getByText("SMTW.MCC2").first()).toBeVisible();

  await page.getByRole("button", { name: "Change lifecycle" }).click();
  await expectDialogFits(page);
  await (await openDialog(page)).getByLabel("Lifecycle").selectOption({ label: "Standby" });
  await saveDialog(page, "Save");
  await expect(page.getByText("Standby").first()).toBeVisible();

  await page.getByRole("button", { name: "Add document" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("File").setInputFiles(MANUAL);
  await dialog.getByLabel("Title").fill("Service manual");
  await saveDialog(page, "Upload");
  const documents = page.locator(".card", { has: page.locator(".card-header", { hasText: /^\s*Documents/ }) });
  await expect(documents).toContainText("Service manual");
  await expect(documents).toContainText("test-manual.pdf");

  await documents.getByTitle("Edit title").click();
  await expectDialogFits(page);
  await (await openDialog(page)).getByLabel("Title").fill("Service manual, 2026 edition");
  await saveDialog(page, "Save");
  await expect(documents).toContainText("Service manual, 2026 edition");
});

test("S030: the lifecycle is named Lifecycle on the form, the page, the list and the history", async ({ page }, testInfo) => {
  // The word Status is reserved for the machine's maintenance status (S030 U1); the checks for it
  // are scoped to the dialogs and the list's header, since the Tickets filter rightly says "Any ticket status"
  const noStatus = /\bStatus\b/;
  await asPerson(page, "engineer", "/equipment");
  await expect(page.locator("thead th", { hasText: /^Lifecycle$/ })).toBeVisible();
  await expect(page.locator("thead")).not.toContainText(noStatus);
  await expect(page.getByRole("combobox", { name: "Lifecycle" }).locator("option").first()).toHaveText("Any lifecycle");

  await page.getByRole("button", { name: "Add equipment" }).click();
  await expectDialogFits(page);
  const addDialog = await openDialog(page);
  await expect(addDialog.getByLabel("Lifecycle").locator("option:checked")).toHaveText("In service");
  await expect(addDialog).not.toContainText(noStatus);
  await addDialog.getByRole("button", { name: "Cancel" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);

  const node = await createEquipment(`E2E lifecycle ${testInfo.project.name}`);
  await page.goto(`/equipment/${node.id}`);
  await page.getByRole("button", { name: "Change lifecycle" }).click();
  await expectDialogFits(page);
  const changeDialog = await openDialog(page);
  await expect(changeDialog.locator(".modal-title")).toHaveText(`Change lifecycle of ${node.code}`);
  await expect(changeDialog).not.toContainText(noStatus);
  await changeDialog.getByLabel("Lifecycle").selectOption({ label: "Standby" });
  await saveDialog(page, "Save");
  await expect(page.locator("h4 + .badge")).toHaveText("Standby");
  const history = page.locator(".card", { has: page.locator(".card-header", { hasText: /^\s*History\s*$/ }) });
  await expect(history).toContainText("Lifecycle: In service → Standby");
});

/** A machine at SMTW.MCC1 made through the API as admin (the test's own record). */
// S029: each test makes its own machines and judges the rows inside a search for their names
// (the three projects share one database, and other specs raise tickets on the seed machines).
async function lightMachines(testInfo, tag) {
  const prefix = `E2E light ${tag} ${testInfo.project.name}`;
  const [red, amber, green] = await Promise.all(["red", "amber", "green"].map((c) => createEquipment(`${prefix} ${c}`)));
  await raiseByApi("supervisor", { equipment_id: red.id, intensity: "critical", description: "Light test: stopped" });
  await raiseByApi("supervisor", { equipment_id: amber.id, intensity: "degraded", description: "Light test: running slow" });
  return { prefix, red, amber, green };
}

// The list rows carry role="link", so they are found by the table row itself
const rowOf = (page, machine) => page.locator("tbody tr", { hasText: machine.code });

test("S029: the equipment list shows a red, amber and green bulb with a name each", async ({ page }, testInfo) => {
  const { prefix, red, amber, green } = await lightMachines(testInfo, "bulbs");
  await asPerson(page, "engineer", `/equipment?q=${encodeURIComponent(prefix)}`);
  await expect(rowOf(page, red).getByRole("img", { name: "Down — breakdown open" })).toBeVisible();
  await expect(rowOf(page, amber).getByRole("img", { name: "Open ticket" })).toBeVisible();
  await expect(rowOf(page, green).getByRole("img", { name: "No open ticket" })).toBeVisible();
});

test("S029: Down now lists only the red row and the URL carries it; Any ticket status clears it", async ({ page }, testInfo) => {
  const { prefix, red, amber, green } = await lightMachines(testInfo, "filter");
  await asPerson(page, "engineer", `/equipment?q=${encodeURIComponent(prefix)}`);
  await expect(rowOf(page, green)).toBeVisible();
  await page.getByRole("combobox", { name: "Tickets" }).selectOption({ label: "Down now" });
  await expect(page).toHaveURL(/tickets=down/);
  await expect(rowOf(page, red)).toBeVisible();
  await expect(rowOf(page, amber)).toHaveCount(0);
  await expect(rowOf(page, green)).toHaveCount(0);
  await page.getByRole("combobox", { name: "Tickets" }).selectOption({ label: "Any ticket status" });
  await expect(page).not.toHaveURL(/tickets=/);
  await expect(rowOf(page, green)).toBeVisible();
});

test("S029: the bulb is in view without scrolling and the Tickets filter fits the screen", async ({ page }, testInfo) => {
  const { prefix, red } = await lightMachines(testInfo, "fit");
  await asPerson(page, "engineer", `/equipment?q=${encodeURIComponent(prefix)}`);
  const bulb = rowOf(page, red).getByRole("img", { name: "Down — breakdown open" });
  await expect(bulb).toBeVisible();
  const width = page.viewportSize().width;
  const box = await bulb.boundingBox();
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(width);
  const select = await page.getByRole("combobox", { name: "Tickets" }).boundingBox();
  expect(select.x + select.width).toBeLessThanOrEqual(width);
});

test("S029: a bookmarked tickets=down shows the plain list to a storekeeper, who has no ticket column", async ({ page }, testInfo) => {
  const { prefix, red, amber, green } = await lightMachines(testInfo, "bookmark");
  await asPerson(page, "storekeeper", `/equipment?tickets=down&q=${encodeURIComponent(prefix)}`);
  for (const machine of [red, amber, green]) await expect(rowOf(page, machine)).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Tickets" })).toHaveCount(0);
});

// S033: a component-unit may have no model; its class and type are then picked directly
test("S033: engineer adds a component-unit with No model; its page and the list show no model", async ({ page }, testInfo) => {
  const name = `E2E no model ${testInfo.project.name}`;
  // Its own machine: a part added under the shared seed extruder would change the label counts of labels.spec.js and screens.spec.js
  const machine = await createEquipment(`E2E no-model parent ${testInfo.project.name}`);
  await asPerson(page, "engineer", `/equipment/${machine.id}`);
  await page.getByRole("button", { name: "Add part" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByLabel("Level")).toHaveValue("component_unit");
  await dialog.getByLabel("Model").selectOption({ label: "No model" });
  await expectDialogFits(page);
  await expect(dialog.getByLabel("Class filter")).toHaveCount(0);
  await expect(dialog).toContainText("Without a model, the class sets the code prefix. A later class change keeps the code.");
  await dialog.getByLabel("Class", { exact: true }).selectOption({ label: "GBX — Gearbox" });
  await expect(dialog.getByLabel("Type", { exact: true }).locator("option:checked")).toHaveText("No type");
  await expectDialogFits(page);
  await dialog.getByLabel("Name").fill(name);
  await saveDialog(page, "Save");

  await expect(page.getByRole("heading", { name: new RegExp(` — ${name}$`) })).toBeVisible();
  const details = page.locator(".card", { has: page.locator(".card-header", { hasText: /^\s*Details\s*$/ }) });
  const model = details.locator("dt", { hasText: /^Model$/ }).locator("xpath=following-sibling::dd[1]");
  await expect(model).toHaveText("No model");
  await expect(details.locator("dt", { hasText: /^Manufacturer$/ })).toHaveCount(0);
  await expect(details.locator("dt", { hasText: /^Class$/ }).locator("xpath=following-sibling::dd[1]")).toContainText("GBX");

  await page.goto(`/equipment?level=component_unit&q=${encodeURIComponent(name)}`);
  const row = page.locator("tbody tr", { hasText: name });
  await expect(row).toHaveCount(1);
  const headers = await page.locator("thead th").allTextContents();
  await expect(row.locator("td").nth(headers.findIndex((h) => h.trim() === "Model"))).toHaveText("—");
});

test("S033: the Add equipment dialog does not offer No model", async ({ page }) => {
  await asPerson(page, "engineer", "/equipment");
  await page.getByRole("button", { name: "Add equipment" }).click();
  await expectDialogFits(page);
  const model = (await openDialog(page)).getByLabel("Model");
  await expect(model.locator("option", { hasText: "Atlas Copco GA37 — CMP / Screw compressor" })).toHaveCount(1);
  await expect(model.locator("option", { hasText: "No model" })).toHaveCount(0);
});

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

const OIL_10_60 = ["Oil temperature", { min_value: "10", max_value: "60" }];
const MIN_TOUCH_PX = 44; // a tap target on a floor screen (S039 CR1-03)
const metersCard = (page) => card(page, "Meters");
async function expectTouchTarget(locator) {
  const box = await locator.boundingBox();
  expect(box.height, "a tap target of 44 px or more").toBeGreaterThanOrEqual(MIN_TOUCH_PX);
}
const meterRow = (page, name) => metersCard(page).getByTestId("node-meter").filter({ hasText: name });

test("S038: the press page shows its model's meters and an own meter", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "list", { modelMeters: [OIL_10_60], ownMeters: [["Run hours", {}]] });
  await asPerson(page, "engineer", `/equipment/${machine.id}`);
  const oil = meterRow(page, "Oil temperature");
  await expect(oil).toContainText("From the model");
  await expect(oil).toContainText("°C · Gauge");
  await expect(oil).toContainText("Limits: 10–60 °C");
  const hours = meterRow(page, "Run hours");
  await expect(hours).toContainText("This machine only");
  await expect(hours).toContainText("h · Counter");
  await expect(hours).not.toContainText("Limits");
  await expect(hours.getByRole("button", { name: "Set limits" })).toHaveCount(0); // a counter has no limits
});

test("S038: engineer overrides a limit and the history shows it", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "override", { modelMeters: [OIL_10_60] });
  await asPerson(page, "engineer", `/equipment/${machine.id}`);
  await meterRow(page, "Oil temperature").getByRole("button", { name: "Set limits" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog).toContainText("Model default — Limits: 10–60 °C");
  await expect(dialog.getByRole("button", { name: "Use the model's limits" })).toHaveCount(0); // not overridden yet
  await dialog.getByLabel("Max", { exact: true }).fill("55");
  const listCalls = [];
  page.on("request", (req) => { if (req.method() === "GET" && req.url().endsWith(`/api/equipment/${machine.id}/meters`)) listCalls.push(req.url()); });
  await saveDialog(page, "Save");

  await expect(meterRow(page, "Oil temperature")).toContainText("Limits: 10–55 °C · set on this machine");
  // The page reloads the node after the save; the card must not fetch its list again (CR1-02)
  await expect(card(page, "History")).toContainText("Meter limits: Oil temperature: 10–60 °C → 10–55 °C");
  expect(listCalls).toHaveLength(0);

  // Use the model's limits clears the override
  await meterRow(page, "Oil temperature").getByRole("button", { name: "Set limits" }).click();
  const again = await openDialog(page);
  await again.getByRole("button", { name: "Use the model's limits" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(meterRow(page, "Oil temperature")).toContainText("Limits: 10–60 °C");
  await expect(meterRow(page, "Oil temperature")).not.toContainText("set on this machine");
  await expect(card(page, "History")).toContainText("Meter limits: Oil temperature: 10–55 °C → 10–60 °C");
});

test("S038: removing an own meter asks first", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "remove", { modelMeters: [OIL_10_60], ownMeters: [["Run hours", {}]] });
  await asPerson(page, "engineer", `/equipment/${machine.id}`);
  const hours = meterRow(page, "Run hours");
  await hours.getByRole("button", { name: "Remove" }).click();
  await expect(hours).toContainText("Remove Run hours from this machine? Readings stay in history.");
  await hours.getByRole("button", { name: "Keep" }).click();
  await expect(hours).not.toContainText("Readings stay in history");

  // A model meter has no Remove here: the card says where it is removed
  const oil = meterRow(page, "Oil temperature");
  await expect(oil.getByRole("button", { name: "Remove" })).toHaveCount(0);
  await expect(oil).toContainText("Comes from the model");
  await expect(oil).toContainText("Remove it in Masters › Models, or change this machine's model.");

  await hours.getByRole("button", { name: "Remove" }).click();
  await hours.getByRole("button", { name: "Remove" }).click();
  await expect(meterRow(page, "Run hours")).toHaveCount(0);
  await expect(meterRow(page, "Oil temperature")).toBeVisible();
  await expect(card(page, "History")).toContainText("Meter removed: Run hours");
});

test("S038: an operator sees the Meters card without edit buttons", async ({ page }, testInfo) => {
  // MCC2: the operator's unit
  const machine = await meterMachine(testInfo, "operator", {
    unit: "SMTW.MCC2", modelMeters: [OIL_10_60], ownMeters: [["Run hours", {}]],
  });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  await expect(meterRow(page, "Oil temperature")).toContainText("Limits: 10–60 °C");
  await expect(meterRow(page, "Run hours")).toBeVisible();
  // S039: the operator logs readings, but edits no meter
  for (const name of ["Add meter", "Set limits", "Remove"]) {
    await expect(metersCard(page).getByRole("button", { name })).toHaveCount(0);
  }
  await expect(metersCard(page).getByRole("button", { name: "Log reading" })).toHaveCount(2);
});

// S039 § 1.3: each meter's last reading, the tap target of its History
test("S039: the Meters card shows the last reading, and its tap opens History", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "last", { unit: "SMTW.MCC2", ownMeters: [["Run hours", {}]] });
  const at = istLocal(30);
  await logByApi(machine, "Run hours", "12345.6", at, { note: "E2E last reading" });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const last = meterRow(page, "Run hours").getByTestId("last-reading");
  await expect(last).toHaveAccessibleName(`History: 12,345.6 h · ${shownTime(at)}`);
  await expectTouchTarget(last);
  await expectTouchTarget(meterRow(page, "Run hours").getByRole("button", { name: "Log reading" }));
  await last.click();
  const dialog = await openDialog(page);
  await expect(dialog.locator(".modal-title")).toHaveText("History · Run hours");
  const row = dialog.getByTestId("reading-row");
  await expect(row).toHaveCount(1);
  await expect(row).toContainText("12,345.6 h");
  await expect(row).toContainText("E2E last reading");
  await expect(row.getByRole("button", { name: "Remove" })).toHaveCount(0); // the operator does not remove
});

// The Properties card (S043 § 7.4): the class's properties with the model's values
test("S043: a number value with its unit shows as 62.5 kVA on the card", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E generator rating ${tag}`;
  const { model, node } = await propertySetup(tag, {
    properties: [{ name, data_type: "number", unit: "kVA" }], values: { 0: "62.5" },
  });
  await asPerson(page, "technician", `/equipment/${node.id}`);
  const properties = card(page, "Properties");
  await expect(properties.locator("dt")).toHaveText([name]);
  await expect(properties.locator("dd")).toHaveText(["62.5 kVA"]);
  await expect(properties).toContainText(`Values from model ${model.label}.`);
  // A technician does not keep the masters (no equipment:edit)
  await expect(properties.getByRole("button", { name: "Edit model values" })).toHaveCount(0);
});

test("S043: Edit model values on the card opens the model dialog; after a save the card shows the new value", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E generator rating ${tag}`;
  const { model, node } = await propertySetup(tag, {
    properties: [{ name, data_type: "number", unit: "kVA" }], values: { 0: "62.5" },
  });
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  const properties = card(page, "Properties");
  await expect(properties.locator("dd")).toHaveText(["62.5 kVA"]);
  await properties.getByRole("button", { name: "Edit model values" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.locator(".modal-title")).toHaveText(`Properties of ${model.label}`);
  await expect(dialog.getByLabel(name)).toHaveValue("62.5");
  await dialog.getByLabel(name).fill("75");
  await saveDialog(page, "Save values");
  await expect(properties.locator("dd")).toHaveText(["75 kVA"]);
});

test("S043: the card is hidden when the class has no property", async ({ page }, testInfo) => {
  const { node } = await propertySetup(propertyTag(testInfo));
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  await expect(card(page, "Details")).toBeVisible();
  await expect(card(page, "Properties")).toHaveCount(0);
});

test("S043: a component-unit with No model shows its class's properties with —, no model line and no Edit model values", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E frame size ${tag}`;
  const { cls, node } = await propertySetup(tag, { properties: [{ name, data_type: "text" }] });
  const part = await noModelPart(node, cls, `E2E no-model part ${tag}`);
  // The engineer keeps the masters, so a part with a model would show the button
  await asPerson(page, "engineer", `/equipment/${part.id}`);
  await expect(card(page, "Details")).toContainText("No model");
  const properties = card(page, "Properties");
  await expect(properties.locator("dt")).toHaveText([name]);
  await expect(properties.locator("dd")).toHaveText(["—"]);
  await expect(properties).not.toContainText("Values from model");
  await expect(properties.getByRole("button", { name: "Edit model values" })).toHaveCount(0);
});
