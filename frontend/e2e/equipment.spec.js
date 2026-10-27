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

test("S003: the Add equipment dialog fits", { tag: "@device" }, async ({ page }) => {
  await asPerson(page, "engineer", "/equipment");
  await page.getByRole("button", { name: "Add equipment" }).click();
  await expectDialogFits(page);
  await (await openDialog(page)).getByLabel("Site").selectOption({ label: "SMTW" });
  await expectDialogFits(page);
});

test("S026: the server's refusal of a field at the bottom of the Add equipment dialog is on screen", { tag: "@device" }, async ({ page, consoleWatch }) => {
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

test("S029: the bulb is in view without scrolling and the Tickets filter fits the screen", { tag: "@device" }, async ({ page }, testInfo) => {
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
  // "GPS location" (S061 seed, every class) is on every top-level machine, last by name
  await expect(properties.locator("dt")).toHaveText([name, "GPS location"]);
  await expect(properties.locator("dd")).toHaveText(["62.5 kVA", "—"]);
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
  await expect(properties.locator("dd")).toHaveText(["62.5 kVA", "—"]);
  await properties.getByRole("button", { name: "Edit model values" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.locator(".modal-title")).toHaveText(`Properties of ${model.label}`);
  await expect(dialog.getByLabel(name)).toHaveValue("62.5");
  await dialog.getByLabel(name).fill("75");
  await saveDialog(page, "Save values");
  await expect(properties.locator("dd")).toHaveText(["75 kVA", "—"]);
});

// S061: a top-level machine always has "GPS location", so a component-unit of a class with no
// links shows the hidden card (no Location on parts, D5)
test("S043: the card is hidden when the class has no property", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const { cls, node } = await propertySetup(tag);
  const part = await noModelPart(node, cls, `E2E bare part ${tag}`);
  await asPerson(page, "engineer", `/equipment/${part.id}`);
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

// This machine's values (S044 § 1.2–1.5, § 8.4): an item's own value of a property, over its model's
async function setItemValues(node, values) {
  const api = await apiAs("admin");
  try {
    const res = await api.put(`/api/equipment/${node.id}/properties`, { data: { values } });
    expect(res.ok(), await res.text()).toBe(true);
  } finally {
    await api.dispose();
  }
}

async function adminPutNode(node, data) {
  const api = await apiAs("admin");
  try {
    const res = await api.put(`/api/equipment/${node.id}`, { data });
    expect(res.ok(), await res.text()).toBe(true);
  } finally {
    await api.dispose();
  }
}

const RATED_POWER = (name) => ({ properties: [{ name, data_type: "number", unit: "kW" }], values: { 0: "7.5" } });

test("S044: engineer sets this machine's rated power; the card marks it and the history shows the model's value before", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E rated power ${tag}`;
  const { model, node } = await propertySetup(tag, RATED_POWER(name));
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  const properties = card(page, "Properties");
  await expect(properties.locator("dd")).toHaveText(["7.5 kW", "—"]);
  // This machine's button first, the model's second (BR2-07)
  await expect(properties.getByRole("button")).toHaveText(["Edit this machine's values", "Edit model values"]);
  await properties.getByRole("button", { name: "Edit this machine's values" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.locator(".modal-title")).toHaveText(`This machine's values — ${node.code}`);
  await expect(dialog.getByLabel(name)).toHaveValue("");
  await expect(dialog).toContainText("Model: 7.5 kW");
  await dialog.getByLabel(name).fill("5.5");
  await saveDialog(page, "Save values");

  await expect(properties.locator("dd")).toHaveText(["5.5 kW · this machine", "—"]);
  await expect(properties).toContainText(`Values from model ${model.label}, except those marked this machine.`);
  await expect(card(page, "History")).toContainText(`Property: ${name}: 7.5 kW (model) → 5.5 kW`);
});

test("S044: engineer clears this machine's value; the card shows the model's again with no mark", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E rated power ${tag}`;
  const { model, node, properties: [power] } = await propertySetup(tag, RATED_POWER(name));
  await setItemValues(node, { [power.id]: "5.5" });
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  const properties = card(page, "Properties");
  await expect(properties.locator("dd")).toHaveText(["5.5 kW · this machine", "—"]);
  await properties.getByRole("button", { name: "Edit this machine's values" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByLabel(name)).toHaveValue("5.5");
  await dialog.getByLabel(name).fill("");
  await saveDialog(page, "Save values");

  await expect(properties.locator("dd")).toHaveText(["7.5 kW", "—"]);
  await expect(properties).toContainText(`Values from model ${model.label}.`);
  await expect(properties).not.toContainText("this machine.");
  await expect(card(page, "History")).toContainText(`Property: ${name}: 5.5 kW → 7.5 kW (model)`);
});

test("S044: a component-unit with No model has only Edit this machine's values; its value shows with no mark", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E frame size ${tag}`;
  const { cls, node } = await propertySetup(tag, { properties: [{ name, data_type: "text" }] });
  const part = await noModelPart(node, cls, `E2E no-model part ${tag}`);
  await asPerson(page, "engineer", `/equipment/${part.id}`);
  const properties = card(page, "Properties");
  await expect(properties.getByRole("button")).toHaveText(["Edit this machine's values"]);
  await properties.getByRole("button", { name: "Edit this machine's values" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog).not.toContainText("Model:");
  await dialog.getByLabel(name).fill("132M");
  await saveDialog(page, "Save values");

  await expect(properties.locator("dd")).toHaveText(["132M"]); // no "· this machine"
  await expect(properties).not.toContainText("Values from model");
  await expect(card(page, "History")).toContainText(`Property: ${name}: no value → 132M`);
});

test("S044: the operator sees no Edit this machine's values, nor does anyone on a scrapped machine", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const { node } = await propertySetup(tag, RATED_POWER(`E2E rated power ${tag}`));
  const api = await apiAs("admin");
  let mcc2;
  try {
    mcc2 = (await (await api.get("/api/masters/units")).json()).items.find((u) => u.full_code === "SMTW.MCC2");
  } finally {
    await api.dispose();
  }
  await adminPutNode(node, { unit_id: mcc2.id }); // MCC2: the operator's unit
  await asPerson(page, "operator", `/equipment/${node.id}`);
  const properties = card(page, "Properties");
  await expect(properties.locator("dd")).toHaveText(["7.5 kW", "—"]);
  await expect(properties.getByRole("button")).toHaveCount(0);

  await adminPutNode(node, { lifecycle: "scrapped" });
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  await expect(page.getByText("Scrapped — this record is read-only.")).toBeVisible();
  await expect(card(page, "Properties").getByRole("button", { name: "Edit this machine's values" })).toHaveCount(0);
});

test("S044: a number with five decimals is refused under its input", async ({ page, consoleWatch }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E rated power ${tag}`;
  const { node } = await propertySetup(tag, RATED_POWER(name));
  consoleWatch.allowFailedRequest(`/api/equipment/${node.id}/properties`, 400);
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  await card(page, "Properties").getByRole("button", { name: "Edit this machine's values" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel(name).fill("5.12345");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Use up to 4 decimals");
  // Beside its field: the input marked, the dialog still open with what was typed
  await expect(dialog.getByLabel(name)).toHaveClass(/is-invalid/);
  await expect(dialog.getByLabel(name)).toHaveValue("5.12345");
});

// S061: the GPS location (seed, every class, set on each machine) and the hint on a machine that moves
const GPS = "GPS location";
const GENSET = { latitude: 11.016823, longitude: 76.955812, accuracy: 12 };
const GENSET_MAP = "https://www.google.com/maps/search/?api=1&query=11.016823,76.955812";

async function gpsId() {
  const api = await apiAs("admin");
  try {
    const items = (await (await api.get("/api/masters/properties")).json()).items;
    return items.find((p) => p.name === GPS).id;
  } finally {
    await api.dispose();
  }
}

async function openMachineValues(page) {
  await card(page, "Properties").getByRole("button", { name: "Edit this machine's values" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByLabel(GPS)).toBeVisible();
  return dialog;
}

test("S061: engineer taps Use my current location; the card shows the location with Open in Maps, and the history the line", async ({ page }, testInfo) => {
  const { node } = await propertySetup(propertyTag(testInfo));
  await page.context().grantPermissions(["geolocation"]);
  await page.context().setGeolocation(GENSET);
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  const dialog = await openMachineValues(page);
  await expect(dialog).not.toContainText("Model:"); // a per-machine property has no model value
  await dialog.getByRole("button", { name: "Use my current location" }).click();
  await expect(dialog.getByLabel(GPS)).toHaveValue("11.016823, 76.955812");
  await expect(dialog).toContainText("About 12 m accurate");
  await saveDialog(page, "Save values");

  const properties = card(page, "Properties");
  await expect(properties.locator("dt")).toHaveText([GPS]);
  await expect(properties.locator("dd")).toContainText("11.016823, 76.955812");
  await expect(properties.locator("dd")).not.toContainText("this machine");
  await expect(properties.getByRole("link", { name: "Open in Maps" })).toHaveAttribute("href", GENSET_MAP);
  await expect(card(page, "History")).toContainText(`Property: ${GPS}: no value → 11.016823, 76.955812`);
});

test("S061: a pasted location with many decimals saves as 6 decimals", async ({ page }, testInfo) => {
  const { node } = await propertySetup(propertyTag(testInfo));
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  const dialog = await openMachineValues(page);
  await dialog.getByLabel(GPS).fill("11.0168234567, 76.9558123");
  await saveDialog(page, "Save values");
  await expect(card(page, "Properties").locator("dd")).toContainText("11.016823, 76.955812");
});

test("S061: a latitude of 95 is refused under its input", async ({ page, consoleWatch }, testInfo) => {
  const { node } = await propertySetup(propertyTag(testInfo));
  consoleWatch.allowFailedRequest(`/api/equipment/${node.id}/properties`, 400);
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  const dialog = await openMachineValues(page);
  await dialog.getByLabel(GPS).fill("95, 76");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "The latitude must be between -90 and 90");
  await expect(dialog.getByLabel(GPS)).toHaveClass(/is-invalid/);
});

test("S061: a blocked location permission shows the blocked message under the input", async ({ page }, testInfo) => {
  const { node } = await propertySetup(propertyTag(testInfo));
  await page.context().clearPermissions();
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  const dialog = await openMachineValues(page);
  await dialog.getByRole("button", { name: "Use my current location" }).click();
  await expect(dialog).toContainText(
    "Location is blocked for Yantra in this browser. Allow it in the browser's settings, or type the location"
  );
  await expect(dialog.getByLabel(GPS)).toHaveValue("");
});

test("S061: a machine whose card has only GPS location shows no model line and no Edit model values", async ({ page }, testInfo) => {
  const { node } = await propertySetup(propertyTag(testInfo));
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  const properties = card(page, "Properties");
  await expect(properties.locator("dt")).toHaveText([GPS]);
  await expect(properties.locator("dd")).toHaveText(["—"]);
  await expect(properties).not.toContainText("Values from model");
  await expect(properties.getByRole("button")).toHaveText(["Edit this machine's values"]);
});

test("S061: a property set on each machine is not in Edit model values", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const power = `E2E rated power ${tag}`;
  const place = `E2E bay ${tag}`;
  const { node } = await propertySetup(tag, {
    properties: [{ name: power, data_type: "number", unit: "kW" }, { name: place, data_type: "text", per_item_only: true }],
    values: { 0: "7.5" },
  });
  await asPerson(page, "engineer", `/equipment/${node.id}`);
  const properties = card(page, "Properties");
  await expect(properties.locator("dt")).toHaveText([place, power, GPS]);
  await properties.getByRole("button", { name: "Edit model values" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByLabel(power)).toHaveValue("7.5");
  await expect(dialog.getByLabel(place)).toHaveCount(0);
  await expect(dialog.getByLabel(GPS)).toHaveCount(0);
});

test("S061: a Portable machine with a GPS location shows the hint under it", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const { node, properties: [mobility] } = await propertySetup(tag, {
    properties: [{ name: "Mobility", data_type: "choice", options: ["Fixed", "Mobile", "Portable"] }],
  });
  try {
    const portable = mobility.options.find((o) => o.label === "Portable").id;
    await setItemValues(node, { [await gpsId()]: "11.016823, 76.955812", [mobility.id]: portable });
    await asPerson(page, "engineer", `/equipment/${node.id}`);
    const properties = card(page, "Properties");
    await expect(properties.locator("dt")).toHaveText([GPS, "Mobility"]);
    await expect(properties.locator("dd").first()).toContainText("This machine moves. The location may be out of date.");
  } finally {
    // A property name is unique, and the projects share the lane's database
    const api = await apiAs("admin");
    try {
      const res = await api.put(`/api/masters/properties/${mobility.id}`, { data: { name: `E2E mobility ${tag}` } });
      expect(res.ok(), await res.text()).toBe(true);
    } finally {
      await api.dispose();
    }
  }
});

// S062: Filter by property — lines of property, operator and value; All / Any; props in the URL
const filterButton = (page) => page.getByRole("button", { name: /^(Filter by property|Properties \(\d+\))$/ });

/** Another machine of `model` in the unit of `node`, made as admin. */
async function machineLike(node, model, name) {
  const api = await apiAs("admin");
  try {
    const res = await api.post("/api/equipment", { data: { level: "equipment", unit_id: node.unit_id, model_id: model.id, name } });
    expect(res.ok(), await res.text()).toBe(true);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

async function openPropertyFilter(page, opener = filterButton(page)) {
  await opener.click();
  await expectDialogFits(page);
  return openDialog(page);
}

/** One condition: line `n` (1-based), its property by the option's text, the operator, a value. */
async function setCondition(dialog, n, propertyText, operator, value) {
  await dialog.getByLabel(`Property ${n}`, { exact: true }).selectOption({ label: propertyText });
  await dialog.getByLabel(`Operator ${n}`, { exact: true }).selectOption({ label: operator });
  if (value !== undefined) await dialog.getByLabel(`Value ${n}`, { exact: true }).fill(value);
}

const propsQuery = (rules, match = "all") => encodeURIComponent(JSON.stringify({ match, rules }));

test("S062: engineer filters the default list by a part's rated power; the level widens and Clear brings the full list back", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E rated power ${tag}`;
  const { cls, node, properties: [power] } = await propertySetup(tag, { properties: [{ name, data_type: "number", unit: "kW" }] });
  const motor = await noModelPart(node, cls, `E2E filter motor ${tag}`);
  await setItemValues(motor, { [power.id]: "15" });

  await asPerson(page, "engineer", "/equipment");
  await expect(page.getByRole("combobox", { name: "Level" })).toHaveValue("equipment");
  const dialog = await openPropertyFilter(page);
  await setCondition(dialog, 1, `${name} (kW)`, "more than", "10");
  await saveDialog(page, "Apply filter");

  await expect(page).toHaveURL(/props=/);
  await expect(page).toHaveURL(/level=all/);
  await expect(page.getByRole("combobox", { name: "Level" })).toHaveValue("all");
  await expect(rowOf(page, motor)).toBeVisible();
  // The motor's Path names its machine, so the machine is looked for by its own code link
  await expect(page.getByRole("link", { name: node.code, exact: true })).toHaveCount(0);
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.getByRole("button", { name: `Properties: ${name} more than 10 kW` })).toBeVisible();
  await expect(filterButton(page)).toHaveText("Properties (1)");

  await page.getByRole("button", { name: "Clear property filter" }).click();
  await expect(page).not.toHaveURL(/props=/);
  await expect(page.getByRole("button", { name: /^Properties:/ })).toHaveCount(0);
  await expect(filterButton(page)).toHaveText("Filter by property");
  await expect.poll(() => page.locator("tbody tr").count()).toBeGreaterThan(1);
});

test("S062: a hand-broken props shows the line cannot be read and one message, and Clear brings the list back", async ({ page }) => {
  await asPerson(page, "engineer", "/equipment?props=%7Bcut");
  await expect(page.getByRole("button", { name: "Properties: cannot be read" })).toBeVisible();
  await expect(page.getByText("The property filter cannot be read. Clear it and make it again.")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Retry" })).toHaveCount(0);
  await expect(page.locator("table")).toHaveCount(0);
  // A tap on the line opens the dialog with one empty line
  const dialog = await openPropertyFilter(page, page.getByRole("button", { name: "Properties: cannot be read" }));
  await expect(dialog.locator("[data-test=condition]")).toHaveCount(1);
  await expect(dialog.getByLabel("Property 1", { exact: true }).locator("option:checked")).toHaveText("Choose a property");
  await dialog.locator(".modal-footer").getByRole("button", { name: "Cancel" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);

  await page.getByRole("button", { name: "Clear property filter" }).click();
  await expect(page).not.toHaveURL(/props=/);
  await expect(page.getByText("The property filter cannot be read.")).toHaveCount(0);
  await expect(page.locator("tbody tr").first()).toBeVisible();
});

test("S062: two lines with Any condition list both machines; with All conditions none", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const power = `E2E rated power ${tag}`;
  const frame = `E2E frame size ${tag}`;
  const { model, node, properties: [powerProp, frameProp] } = await propertySetup(tag, {
    properties: [{ name: power, data_type: "number", unit: "kW" }, { name: frame, data_type: "text" }],
  });
  const other = await machineLike(node, model, `E2E frame machine ${tag}`);
  await setItemValues(node, { [powerProp.id]: "15" });
  await setItemValues(other, { [frameProp.id]: "IE3 132M" });

  await asPerson(page, "engineer", "/equipment");
  let dialog = await openPropertyFilter(page);
  await setCondition(dialog, 1, `${power} (kW)`, "more than", "10");
  await expect(dialog.getByText("Match", { exact: true })).toHaveCount(0); // shown from two lines
  await dialog.getByRole("button", { name: "Add condition" }).click();
  await setCondition(dialog, 2, frame, "contains", "IE3");
  await dialog.getByLabel("Any condition").check();
  await saveDialog(page, "Apply filter");
  await expect(rowOf(page, node)).toBeVisible();
  await expect(rowOf(page, other)).toBeVisible();
  await expect(page.getByRole("button", { name: `Properties (any of): ${power} more than 10 kW · ${frame} contains "IE3"` })).toBeVisible();
  await expect(filterButton(page)).toHaveText("Properties (2)");

  dialog = await openPropertyFilter(page, page.getByRole("button", { name: /^Properties \(any of\)/ }));
  await expect(dialog.getByLabel("Any condition")).toBeChecked();
  await dialog.getByLabel("All conditions").check();
  await saveDialog(page, "Apply filter");
  await expect(page.getByText("No equipment matches these filters.")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Properties \(all of\)/ })).toBeVisible();
});

test("S062: a value 7,5 is refused under its line and the dialog stays open", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/api/equipment", 400);
  const tag = propertyTag(testInfo);
  const name = `E2E rated power ${tag}`;
  await propertySetup(tag, { properties: [{ name, data_type: "number", unit: "kW" }] });
  await asPerson(page, "engineer", "/equipment");
  const dialog = await openPropertyFilter(page);
  await setCondition(dialog, 1, `${name} (kW)`, "more than", "7,5");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Enter a number");
  await expect(dialog.getByLabel("Value 1", { exact: true })).toHaveClass(/is-invalid/);
  await expect(dialog.getByLabel("Value 1", { exact: true })).toHaveValue("7,5");
  await expect(page.locator(".modal.show")).toHaveCount(1);
  await expect(page).not.toHaveURL(/props=/);
});

test("S062: a choice line with is not says machines with no value are not included", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E mount ${tag}`;
  await propertySetup(tag, { properties: [{ name, data_type: "choice", options: ["Fixed", "Mobile"] }] });
  await asPerson(page, "engineer", "/equipment");
  const dialog = await openPropertyFilter(page);
  await dialog.getByLabel("Property 1", { exact: true }).selectOption({ label: name });
  await expect(dialog.getByLabel("Operator 1", { exact: true })).toHaveValue("in");
  await expect(dialog.getByText("Machines with no value are not included.")).toHaveCount(0);
  await dialog.getByLabel("Operator 1", { exact: true }).selectOption({ label: "is not" });
  await expect(dialog.getByText("Machines with no value are not included.")).toBeVisible();
  await dialog.getByLabel("Fixed").check();
  await saveDialog(page, "Apply filter");
  await expect(page.getByRole("button", { name: `Properties: ${name} is not Fixed` })).toBeVisible();
});

test("S062: a reload keeps the filter, and Back after Clear property filter brings it back", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E rated power ${tag}`;
  const { node, properties: [power] } = await propertySetup(tag, { properties: [{ name, data_type: "number", unit: "kW" }], values: { 0: "15" } });
  const line = `Properties: ${name} more than 10 kW`;
  await asPerson(page, "engineer", `/equipment?level=all&props=${propsQuery([{ property_id: power.id, op: "gt", value: "10" }])}`);
  await expect(rowOf(page, node)).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(1);

  await page.reload();
  await expect(page.getByRole("button", { name: line })).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(1);

  await page.getByRole("button", { name: "Clear property filter" }).click();
  await expect(page.getByRole("button", { name: line })).toHaveCount(0);
  await page.goBack();
  await expect(page.getByRole("button", { name: line })).toBeVisible();
  await expect(page).toHaveURL(/props=/);
  await expect(rowOf(page, node)).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(1);
});

test("S062: the Filter by property dialog with three lines fits the screen, its buttons in view", { tag: "@device" }, async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const power = `E2E rated power ${tag}`;
  const mount = `E2E mount ${tag}`;
  const frame = `E2E frame size ${tag}`;
  await propertySetup(tag, {
    properties: [
      { name: power, data_type: "number", unit: "kW" },
      { name: mount, data_type: "choice", options: ["Fixed", "Mobile", "Portable"] },
      { name: frame, data_type: "text" },
    ],
  });
  await asPerson(page, "engineer", "/equipment");
  const dialog = await openPropertyFilter(page);
  await setCondition(dialog, 1, `${power} (kW)`, "between");
  await dialog.getByRole("button", { name: "Add condition" }).click();
  await setCondition(dialog, 2, mount, "is");
  await dialog.getByRole("button", { name: "Add condition" }).click();
  await setCondition(dialog, 3, frame, "contains", "IE3");
  await expect(dialog.locator("[data-test=condition]")).toHaveCount(3);
  await expectDialogFits(page);
});
