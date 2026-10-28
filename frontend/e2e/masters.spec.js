// Masters › Failure codes (S016) — in place of its manual checks: the pre-filled lists, a class's
// own modes, the label rule, deactivate / reactivate, read-only for an operator, and the lists
// on a phone.
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { apiAs, asPerson, seedIds } from "./support/people.js";
import { categorySetup, propertySetup, propertyTag } from "./support/properties.js";
import { card, causeId, moveByApi, raiseByApi, saveDialog } from "./support/tickets.js";

const PRESS_CLASS = "HP"; // Hydraulic press, from the dev seed's classes
const GENERAL_MODES = 14; // the General modes v20 (S016's seed) fills in (S016 § 4.4)

/** Masters › Failure codes, on the list `list` ("Modes", "Causes", "Actions"). */
async function openFailureCodes(page, key, list = "Modes") {
  await asPerson(page, key, "/masters");
  await page.getByRole("button", { name: "Failure codes" }).click();
  await page.getByRole("group", { name: "Failure code list" }).getByRole("button", { name: list }).click();
}

const rows = (page) => page.locator("table tbody tr");

test("engineer: the pre-filled lists are there; a press mode is added and the press filter shows it", async ({ page }, testInfo) => {
  await openFailureCodes(page, "engineer");
  const filter = page.getByLabel("Filter by class");
  await filter.selectOption({ label: "General" });
  await expect(rows(page)).toHaveCount(GENERAL_MODES);

  // A code and label of this project's own: the three projects share one database
  const suffix = testInfo.project.name.split("-").map((w) => w[0].toUpperCase()).join("");
  const code = `RAM${suffix}`;
  const label = `Ram does not return (${testInfo.project.name})`;
  await filter.selectOption({ label: PRESS_CLASS });
  await page.getByRole("button", { name: "Add mode" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByLabel("Class")).toHaveValue(/\d+/); // the filtered class is pre-picked
  await dialog.getByLabel("Code").fill(code);
  await dialog.getByLabel("Symptom").fill(label);
  await saveDialog(page, "Save");
  await expect(rows(page).filter({ hasText: label })).toContainText(PRESS_CLASS);
  // The press filter shows the press's own modes only
  await expect(rows(page).filter({ hasNotText: PRESS_CLASS })).toHaveCount(0);

  await page.getByRole("group", { name: "Failure code list" }).getByRole("button", { name: "Causes" }).click();
  await expect(rows(page).filter({ hasText: "No cause found" })).toContainText("5.1");
  await page.getByRole("group", { name: "Failure code list" }).getByRole("button", { name: "Actions" }).click();
  await expect(rows(page).first()).toBeVisible();
});

test("engineer: a press mode labelled like a General one is refused", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/masters/failure-modes", 409);
  await openFailureCodes(page, "engineer");
  await page.getByLabel("Filter by class").selectOption({ label: PRESS_CLASS });
  await page.getByRole("button", { name: "Add mode" }).click();
  const dialog = await openDialog(page);
  await dialog.getByLabel("Code").fill("XNOI");
  await dialog.getByLabel("Symptom").fill("Abnormal noise");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, /A failure mode with this label exists \(NOI, General\)/);
  await expect(dialog).toBeVisible();
});

test("engineer: a deactivated mode is hidden unless Show inactive, and comes back on reactivate", async ({ page }) => {
  await openFailureCodes(page, "engineer");
  const mode = rows(page).filter({ hasText: "Stops by itself" });
  await mode.getByTitle("Edit").click();
  await expectDialogFits(page);
  // Click inside the open dialog, and wait for the inline confirm before its Yes (S045)
  let dialog = page.locator(".modal.show .modal-dialog");
  await dialog.getByRole("button", { name: "Deactivate" }).click();
  const yes = dialog.getByRole("button", { name: "Yes", exact: true });
  await expect(yes).toBeVisible();
  await yes.click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(mode).toHaveCount(0);

  await page.getByLabel("Show inactive").check();
  await expect(mode).toContainText("Inactive");
  await mode.getByTitle("Edit").click();
  dialog = await openDialog(page);
  await dialog.getByRole("button", { name: "Reactivate" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await page.getByLabel("Show inactive").uncheck();
  await expect(mode).toContainText("Active");
});

// Add and edit of a cause and of an action (brief § 1.4); the dialogs are checked to fit each time.
for (const kind of [
  { list: "Causes", noun: "a cause", add: "Add cause", prefix: "C", needsGroup: true, labelField: "#cause-label", codeField: "#cause-code" },
  { list: "Actions", noun: "an action", add: "Add action", prefix: "A", labelField: "#action-label", codeField: "#action-code" },
]) {
  test(`engineer: ${kind.noun} is added and edited`, async ({ page }, testInfo) => {
    await openFailureCodes(page, "engineer", kind.list);
    // Code and label of this project's own: the three projects share one database
    const suffix = testInfo.project.name.split("-").map((w) => w[0].toUpperCase()).join("");
    const code = `${kind.prefix}${suffix}`;
    const label = `S024 ${kind.list} ${testInfo.project.name}`;
    const edited = `${label} edited`;

    await page.getByRole("button", { name: kind.add }).click();
    await expectDialogFits(page);
    const dialog = await openDialog(page);
    if (kind.needsGroup) await dialog.locator("#cause-group").selectOption({ label: "Operation / maintenance" }); // the list is not filtered, so no group is pre-picked
    await dialog.locator(kind.codeField).fill(code);
    await dialog.locator(kind.labelField).fill(label);
    await saveDialog(page, "Save");
    const row = rows(page).filter({ hasText: label });
    await expect(row).toContainText(code);

    await row.getByTitle("Edit").click();
    await expectDialogFits(page);
    await (await openDialog(page)).locator(kind.labelField).fill(edited);
    await saveDialog(page, "Save");
    await expect(rows(page).filter({ hasText: edited })).toHaveCount(1);
  });
}

// The Masters sections no other test opens (S024 CR1-04): each one shows its table, and its Add
// dialog fits the screen and shows the server's refusal beside the field when saved empty.
// `before` makes a row first, for a list the seed leaves empty (Categories, S063).
for (const section of [
  { button: "Units", add: "Add unit", api: "/api/masters/units", person: "it_admin" },
  {
    button: "Categories", add: "Add category", api: "/api/masters/equipment-categories", person: "engineer",
    message: "Name is required", before: (testInfo) => categorySetup(propertyTag(testInfo)),
  },
  { button: "Classes", add: "Add class", api: "/api/masters/equipment-classes", person: "engineer" },
  { button: "Types", add: "Add type", api: "/api/masters/equipment-types", person: "engineer" },
  { button: "Trades", add: "Add trade", api: "/api/masters/trades", person: "engineer", message: "Name is required" },
  { button: "Meter types", add: "Add meter type", api: "/api/masters/meter-types", person: "engineer", message: "Name is required" },
]) {
  test(`${section.person}: the ${section.button} section opens, and an empty ${section.add.toLowerCase()} is refused beside its field`, async ({ page, consoleWatch }, testInfo) => {
    consoleWatch.allowFailedRequest(section.api, 400);
    if (section.before) await section.before(testInfo);
    await asPerson(page, section.person, "/masters");
    await page.getByRole("button", { name: section.button, exact: true }).click();
    await expect(rows(page).first()).toBeVisible();
    await page.getByRole("button", { name: section.add }).click();
    await expectDialogFits(page);
    const dialog = await openDialog(page);
    await dialog.locator(".modal-footer button[type=submit]").click();
    if (section.message) await expectFieldMessage(dialog, section.message);
    else await expect(dialog.locator(".invalid-feedback").first()).toBeVisible();
    await expect(dialog).toBeVisible();
  });
}

// S064 UX-12: Masters is for its editors, so the lists are checked as the engineer (an operator,
// who read them before, has no Masters now)
test("engineer: the failure code lists fit a phone", { tag: "@device" }, async ({ page }) => {
  await openFailureCodes(page, "engineer");
  for (const list of ["Modes", "Causes", "Actions"]) {
    await page.getByRole("group", { name: "Failure code list" }).getByRole("button", { name: list }).click();
    await expect(rows(page).first()).toBeVisible();
    await expectNoSidewaysScroll(page);
  }
});

/** The open tickets at the unit `fullCode` ("SMTW.MCC1"), read through the API as admin. */
async function openTicketsAt(fullCode) {
  const api = await apiAs("admin");
  try {
    const units = await (await api.get("/api/masters/units")).json();
    const unit = units.items.find((u) => u.full_code === fullCode);
    const res = await api.get(`/api/tickets?unit_id=${unit.id}&state=open&per_page=1`);
    expect(res.ok(), `ticket list failed: ${res.status()}`).toBe(true);
    return (await res.json()).total;
  } finally {
    await api.dispose();
  }
}

test("S025: IT admin cannot deactivate a unit while it has open tickets; the refusal gives the count", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/masters/units/", 409);
  const seed = await seedIds();
  const ticket = await raiseByApi("supervisor", {
    equipment_id: seed.mcc1Mill.id, intensity: "degraded", description: "S025 test: the unit stays active",
  });
  // Other tests leave tickets open at this unit (the three projects share one database): count them all
  const open = await openTicketsAt("SMTW.MCC1");
  try {
    await asPerson(page, "it_admin", "/masters");
    await page.getByRole("button", { name: "Units", exact: true }).click();
    await rows(page).filter({ hasText: "SMTW.MCC1" }).getByTitle("Edit").click();
    await expectDialogFits(page);
    const dialog = await openDialog(page);
    await dialog.getByRole("button", { name: "Deactivate" }).click();
    await dialog.getByRole("button", { name: "Yes", exact: true }).click();
    await expectFieldMessage(dialog, `Close its tickets first (${open} open)`);
    await expect(dialog).toBeVisible();
  } finally {
    // This test's own ticket is closed again, so the unit's count is as it was
    await moveByApi("engineer", ticket.id, "not-a-fault", { cause_id: await causeId("5.1"), remark: "S025 test done" });
  }
});

/** Masters › Team as `key`, the person dialog of `name` open and checked to fit the screen. */
async function openPersonDialog(page, key, name) {
  await asPerson(page, key, "/masters");
  await page.getByRole("button", { name: "Team", exact: true }).click();
  await rows(page).filter({ hasText: name }).getByTitle("Edit").click();
  await expectDialogFits(page);
  return openDialog(page);
}

test("S032: IT admin sees the manager's email from Keycloak in the Team dialog; the engineer sees no email line", async ({ page }) => {
  // The manager loads a page first, which copies the token's email onto their Team record, so
  // the test does not depend on another test's order (BR1-04)
  await asPerson(page, "manager", "/equipment");

  const dialog = await openPersonDialog(page, "it_admin", "Arun (manager)");
  await expect(dialog.getByText("Email (from Keycloak): e2e_manager@example.test")).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();

  const asEngineer = await openPersonDialog(page, "engineer", "Arun (manager)");
  await expect(asEngineer.getByText("Has a Yantra login: yes")).toBeVisible();
  await expect(asEngineer.getByText(/Email \(from Keycloak\)/)).toHaveCount(0);
});

// Masters › Meter types (S037)
const openMeterTypes = async (page, person) => {
  await asPerson(page, person, "/masters");
  await page.getByRole("button", { name: "Meter types", exact: true }).click();
};

test("S037: engineer adds a meter type and sees it in the list", async ({ page }, testInfo) => {
  await openMeterTypes(page, "engineer");
  // The eight seed types are there (S037 § 1.3)
  await expect(rows(page).filter({ hasText: "Shift production" })).toContainText("Amount per period");
  await expect(rows(page).filter({ hasText: "Run hours" })).toContainText("Counter");

  // A name of this project's own: the three projects share one database
  const name = `S037 Pressure (${testInfo.project.name})`;
  await page.getByRole("button", { name: "Add meter type" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByLabel("Counter", { exact: true })).toBeChecked(); // the common case is preselected
  await dialog.getByLabel("Name").fill(name);
  await dialog.getByLabel("Unit").fill("bar");
  await dialog.getByLabel("Gauge", { exact: true }).check();
  await dialog.getByLabel("Decimals").selectOption("1");
  await saveDialog(page, "Save");
  const row = rows(page).filter({ hasText: name });
  await expect(row).toContainText("bar");
  await expect(row).toContainText("Gauge");
  await expect(row).toContainText("Active");
});

// S064 UX-12 (D2): Masters is for its editors, so an operator no longer reads meter types there
test("S037: an operator has no Masters, so no meter types to change", async ({ page }) => {
  await asPerson(page, "operator", "/masters");
  await expect(page).toHaveURL(/\/me(\?|$)/);
  await expect(page.getByRole("button", { name: "Add meter type" })).toHaveCount(0);
});

test("S037: a Yes / No type hides Unit and Decimals and asks for the expected answer", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/api/masters/meter-types", 400);
  await openMeterTypes(page, "engineer");
  const name = `S037 Oil level above min (${testInfo.project.name})`;
  await page.getByRole("button", { name: "Add meter type" }).click();
  const dialog = await openDialog(page);
  await expect(dialog.getByLabel("Unit")).toBeVisible();
  await dialog.getByLabel("Yes / No", { exact: true }).check();
  await expect(dialog.getByLabel("Unit")).toHaveCount(0);
  await expect(dialog.getByLabel("Decimals")).toHaveCount(0);
  await expect(dialog.getByText("The answer that means all is well.")).toBeVisible();
  await expectDialogFits(page);

  // No expected answer picked: refused beside the field
  await dialog.getByLabel("Name").fill(name);
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Expected answer is required");

  await dialog.getByLabel("Yes", { exact: true }).check();
  await saveDialog(page, "Save");
  const row = rows(page).filter({ hasText: name });
  await expect(row).toContainText("Yes / No, expects Yes");
  await expect(row.locator("td").nth(1)).toHaveText("—"); // unit
  await expect(row.locator("td").nth(3)).toHaveText("—"); // decimals
});

// Masters › Models › Meters (S038).  The test makes its own model (never SMTW-HYP-01, which
// S039's e2e set-up keeps for its machines; S039 BR3-03), named after the project: the three
// projects share one database.
async function makeModel(testInfo, tag) {
  const api = await apiAs("admin");
  try {
    const items = async (url) => (await (await api.get(url)).json()).items;
    const [makers, classes] = await Promise.all([items("/api/masters/manufacturers"), items("/api/masters/equipment-classes")]);
    const designation = `S038 ${tag} ${testInfo.project.name} ${Date.now().toString(36)}`;
    const res = await api.post("/api/masters/equipment-models", {
      data: { manufacturer_id: makers.find((m) => m.name === "Generic").id, designation,
              class_id: classes.find((c) => c.code === PRESS_CLASS).id, type_id: null },
    });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

test("S038: engineer adds Oil temperature with limits to a model", async ({ page }, testInfo) => {
  const model = await makeModel(testInfo, "model");
  await asPerson(page, "engineer", "/masters");
  await page.getByRole("button", { name: "Models", exact: true }).click();
  await page.getByRole("row", { name: new RegExp(model.designation) }).getByTitle("Meters").click();

  // The in-panel view, in place of the table
  const header = page.locator(".card-header").filter({ hasText: "· Meters" });
  await expect(header).toContainText(model.label);
  await expect(page.getByText("No meters.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Add model" })).toHaveCount(0);

  await header.getByRole("button", { name: "Add meter" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Meter type").selectOption({ label: "Oil temperature (°C, Gauge)" });
  await dialog.getByLabel("Min", { exact: true }).fill("10");
  await dialog.getByLabel("Max", { exact: true }).fill("60");
  await saveDialog(page, "Save");

  const meter = page.getByTestId("model-meter").filter({ hasText: "Oil temperature" });
  await expect(meter).toContainText("°C · Gauge");
  await expect(meter).toContainText("Limits: 10–60 °C");
  await expect(meter.getByRole("button", { name: "Set limits" })).toBeVisible();

  // "← Models" brings the table back
  await header.getByRole("button", { name: "Models" }).click();
  await expect(page.getByRole("button", { name: "Add model" })).toBeVisible();
  await expect(page.getByRole("row", { name: new RegExp(model.designation) })).toBeVisible();
});

// Equipment properties (S043 § 8.4): the master, a class's table and picker, a model's values.
const openSection = (page, name) => page.getByRole("button", { name, exact: true }).click();
const GPS_NAME = "GPS location"; // the seed of migration v34 (S061): every class, set on each machine

test("S043: engineer adds a choice property, adds two properties to a class at once and sets one on a model; the equipment page shows it", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const drain = `E2E drain ${tag}`;
  const power = `E2E power ${tag}`;
  const { cls, model, node } = await propertySetup(tag, {
    properties: [{ name: power, data_type: "number", unit: "kW" }], link: false,
  });
  await asPerson(page, "engineer", "/masters");

  await openSection(page, "Properties");
  await page.getByRole("button", { name: "Add property", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Name").fill(drain);
  await dialog.getByLabel("Data type").selectOption({ label: "Choice" });
  await expect(dialog.getByLabel("Unit")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Add option" }).click();
  await dialog.getByLabel("Option 1", { exact: true }).fill("Internal");
  await dialog.getByRole("button", { name: "Add option" }).click();
  await dialog.getByLabel("Option 2", { exact: true }).fill("External");
  // One Add option too many: the unsaved row can be taken away again (CR1-03)
  await dialog.getByRole("button", { name: "Add option" }).click();
  await dialog.getByRole("button", { name: "Remove option 3" }).click();
  await expect(dialog.getByLabel("Option 3", { exact: true })).toHaveCount(0);
  await saveDialog(page, "Save");
  await expect(rows(page).filter({ hasText: drain })).toContainText("Choice · 2 options");

  await openSection(page, "Classes");
  await rows(page).filter({ hasText: cls.code }).getByTitle("Properties").click();
  await expect(page.getByText(`Properties of ${cls.code} — ${cls.name}`)).toBeVisible();
  // S061: the seed "GPS location" is on every class, marked, with no Remove
  await expect(rows(page)).toHaveCount(1);
  await expect(rows(page).filter({ hasText: "GPS location" })).toContainText("Every class");
  await expect(rows(page).filter({ hasText: "GPS location" }).getByRole("button", { name: "Remove" })).toHaveCount(0);
  await page.getByRole("button", { name: "Add property…" }).click();
  await expectDialogFits(page);
  const picker = await openDialog(page);
  await expect(picker.locator(".modal-title")).toHaveText(`Add properties to ${cls.code}`);
  await picker.getByLabel("Search properties").fill(tag);
  await expect(picker.locator(".form-check")).toHaveCount(2);
  await picker.getByLabel(drain).check();
  // Enter in the search box (a phone's Search key) does not add what is ticked so far (CR1-01)
  await picker.getByLabel("Search properties").press("Enter");
  await expect(picker).toBeVisible();
  await expect(picker.getByLabel(drain)).toBeChecked();
  await picker.getByLabel(power).check();
  await saveDialog(page, "Add properties");
  await expect(rows(page)).toHaveCount(3);
  await expect(rows(page).filter({ hasText: drain })).toContainText("Choice");
  await expect(rows(page).filter({ hasText: power })).toContainText("kW");

  await openSection(page, "Models");
  await rows(page).filter({ hasText: model.label }).getByTitle("Properties").click();
  await expectDialogFits(page);
  const values = await openDialog(page);
  await expect(values.locator(".modal-title")).toHaveText(`Properties of ${model.label}`);
  await values.getByLabel(drain).selectOption({ label: "External" });
  await saveDialog(page, "Save values");

  await page.goto(`/equipment/${node.id}`);
  const properties = card(page, "Properties");
  await expect(properties.locator("dt")).toHaveText([drain, power, "GPS location"]);
  await expect(properties.locator("dd")).toHaveText(["External", "—", "—"]);
  await expect(properties).toContainText(`Values from model ${model.label}.`);
});

test("S043: Remove on a class's table takes the row away, and the picker lists the property again", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E removed ${tag}`;
  const { cls } = await propertySetup(tag, { properties: [{ name, data_type: "text" }] });
  await asPerson(page, "engineer", "/masters");
  await openSection(page, "Classes");
  await rows(page).filter({ hasText: cls.code }).getByTitle("Properties").click();
  await expect(rows(page).filter({ hasText: name })).toContainText("Text");
  await expect(page.getByText("Removing a property keeps the models' values. Add it again to show them.")).toBeVisible();
  await rows(page).filter({ hasText: name }).getByRole("button", { name: "Remove" }).click();
  await expect(rows(page).filter({ hasText: name })).toHaveCount(0);
  await expect(rows(page)).toHaveText([/GPS location/]); // S061: the every-class seed stays

  await page.getByRole("button", { name: "Add property…" }).click();
  const picker = await openDialog(page);
  await picker.getByLabel("Search properties").fill(tag);
  await expect(picker.getByLabel(name)).toBeVisible();
});

test("S043: a refused number shows Enter a number under its input", async ({ page, consoleWatch }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E rating ${tag}`;
  const { model } = await propertySetup(tag, { properties: [{ name, data_type: "number", unit: "kVA" }] });
  consoleWatch.allowFailedRequest(`/api/masters/equipment-models/${model.id}/properties`, 400);
  await asPerson(page, "engineer", "/masters");
  await openSection(page, "Models");
  await rows(page).filter({ hasText: model.label }).getByTitle("Properties").click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel(name).fill("abc");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Enter a number");
  await expect(dialog.getByLabel(name)).toBeFocused();
  await expect(dialog).toBeVisible();
});

test("S043: an option refused on Save leaves the list showing the property's saved name", async ({ page, consoleWatch }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E drain ${tag}`;
  const api = await apiAs("admin");
  let property;
  try {
    const res = await api.post("/api/masters/properties", { data: { name, data_type: "choice", options: ["Internal"] } });
    expect(res.status(), await res.text()).toBe(201);
    property = await res.json();
  } finally {
    await api.dispose();
  }
  consoleWatch.allowFailedRequest(`/api/masters/properties/${property.id}/options`, 409);
  await asPerson(page, "engineer", "/masters");
  await openSection(page, "Properties");
  await rows(page).filter({ hasText: name }).getByTitle("Edit").click();
  const dialog = await openDialog(page);
  await dialog.getByLabel("Name").fill(`${name} type`);
  await dialog.getByRole("button", { name: "Add option" }).click();
  await dialog.getByLabel("Option 2", { exact: true }).fill("internal");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "An option with this label exists");
  // The rename is saved; the list shows it even though the dialog is discarded (CR1-02)
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await dialog.getByRole("button", { name: "Discard" }).click();
  await expect(dialog).toBeHidden();
  await expect(rows(page).filter({ hasText: `${name} type` })).toContainText("Choice · 1 option");
});

// S061: a property on every class shows on every machine without a link; marked in a class's
// table with no Remove, and left out of the picker
test("S061: engineer makes a Yes / No property for every class; a machine of an unlinked class shows it, the class table marks it, the picker leaves it out", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const name = `E2E every class ${tag}`;
  const { cls, node } = await propertySetup(tag);
  try {
    await asPerson(page, "engineer", "/masters");
    await openSection(page, "Properties");
    await page.getByRole("button", { name: "Add property", exact: true }).click();
    await expectDialogFits(page);
    const dialog = await openDialog(page);
    await dialog.getByLabel("Name").fill(name);
    await dialog.getByLabel("Data type").selectOption({ label: "Yes / No" });
    await dialog.getByLabel("Applies to every class").check();
    await saveDialog(page, "Save");
    await expect(rows(page).filter({ hasText: name })).toContainText("Every class");
    await expect(rows(page).filter({ hasText: GPS_NAME })).toContainText("Each machine");

    await openSection(page, "Classes");
    await rows(page).filter({ hasText: cls.code }).getByTitle("Properties").click();
    const row = rows(page).filter({ hasText: name });
    await expect(row).toContainText("Every class");
    await expect(row.getByRole("button", { name: "Remove" })).toHaveCount(0);
    await page.getByRole("button", { name: "Add property…" }).click();
    await expectDialogFits(page);
    const picker = await openDialog(page);
    await picker.getByLabel("Search properties").fill(tag);
    await expect(picker.getByText("No property matches the search.")).toBeVisible();
    await picker.getByRole("button", { name: "Cancel" }).click();

    await page.goto(`/equipment/${node.id}`);
    const properties = card(page, "Properties");
    await expect(properties.locator("dt")).toHaveText([name, GPS_NAME]);
    await expect(properties.locator("dd")).toHaveText(["—", "—"]);
  } finally {
    // Off again, so the lane's later tests do not meet it on every machine
    const api = await apiAs("admin");
    try {
      const made = (await (await api.get("/api/masters/properties")).json()).items.find((p) => p.name === name);
      if (made) {
        const res = await api.put(`/api/masters/properties/${made.id}`, { data: { all_classes: false } });
        expect(res.ok(), await res.text()).toBe(true);
      }
    } finally {
      await api.dispose();
    }
  }
});

test("S063: engineer adds a category, puts a class in it, and cannot deactivate it while the class is active", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/api/masters/equipment-categories", 409);
  const tag = propertyTag(testInfo);
  const { cls } = await propertySetup(tag);
  const name = `E2E lifting ${tag}`;
  await asPerson(page, "engineer", "/masters");

  await openSection(page, "Categories");
  await page.getByRole("button", { name: "Add category" }).click();
  await expectDialogFits(page);
  await (await openDialog(page)).getByLabel("Name").fill(name);
  await saveDialog(page, "Save");
  await expect(rows(page).filter({ hasText: name }).locator("td").nth(1)).toHaveText("0");

  await openSection(page, "Classes");
  await rows(page).filter({ hasText: cls.code }).getByTitle("Edit").click();
  await expectDialogFits(page);
  await (await openDialog(page)).getByLabel("Category").selectOption({ label: name });
  await saveDialog(page, "Save");
  await expect(rows(page).filter({ hasText: cls.code }).locator("td").nth(2)).toHaveText(name);

  await openSection(page, "Categories");
  const row = rows(page).filter({ hasText: name });
  await expect(row.locator("td").nth(1)).toHaveText("1");
  await row.getByTitle("Edit").click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByRole("button", { name: "Deactivate" }).click();
  await dialog.getByRole("button", { name: "Yes" }).click();
  await expect(dialog.locator(".alert-danger")).toHaveText("1 active class is in this category. Move it to another category first.");
});

// ---------------------------------------------------------------------------
// S064: Deactivate blocked while the form has unsaved changes (UX-16); Team: Add person with sites
// (UX-14), the access lines (UX-15), the list's search and site filter (UX-18)

/** Masters › Team as `key`. */
async function openTeam(page, key) {
  await asPerson(page, key, "/masters");
  await page.getByRole("button", { name: "Team", exact: true }).click();
  await expect(rows(page).first()).toBeVisible();
}

/** A unit code of the test's own: 2–20 capital letters and digits, random. */
const ownUnitCode = () => `U${Math.random().toString(36).slice(2, 9).toUpperCase()}`;

/** The id of the seed site `code`, read as admin. */
async function siteId(code) {
  const api = await apiAs("admin");
  try {
    return (await (await api.get("/api/masters/sites")).json()).items.find((s) => s.code === code).id;
  } finally {
    await api.dispose();
  }
}

test("S064: Deactivate is disabled with its reason after a name is edited, and enabled again once the edit is undone", async ({ page }) => {
  await asPerson(page, "engineer", "/masters");
  await page.getByRole("button", { name: "Trades", exact: true }).click();
  await rows(page).filter({ has: page.locator("td", { hasText: /^Mechanical$/ }) }).getByTitle("Edit").click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  const deactivate = dialog.getByRole("button", { name: "Deactivate" });
  await expect(deactivate).toBeEnabled();
  const name = dialog.getByLabel("Name", { exact: true });
  await name.fill("Mechanical changed");
  await expect(deactivate).toBeDisabled();
  await expect(dialog.locator(".modal-footer").getByText("Save your changes first, or cancel them")).toBeVisible();
  await name.fill("Mechanical");
  await expect(deactivate).toBeEnabled();
  await expect(dialog.getByText("Save your changes first, or cancel them")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
});

test("S064: Add person with a site and role saves both in one Save; the list shows the role", async ({ page }, testInfo) => {
  const name = `E2E new technician ${propertyTag(testInfo)}`;
  await openTeam(page, "engineer");
  await page.getByRole("button", { name: "Add person" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByText(/Save the person first/)).toHaveCount(0);
  await dialog.getByLabel("Name", { exact: true }).fill(name);
  await dialog.getByLabel("Site to add").selectOption({ index: 1 });
  await dialog.getByRole("button", { name: "Add", exact: true }).click();
  await dialog.getByLabel("All units").check();
  await expectDialogFits(page);
  await saveDialog(page, "Save");
  const row = rows(page).filter({ hasText: name });
  await expect(row).toContainText("SMTW Technician");
});

test("S064: removing a site row says what the save takes away", async ({ page }, testInfo) => {
  const name = `E2E row to remove ${propertyTag(testInfo)}`;
  const api = await apiAs("admin");
  try {
    const person = await (await api.post("/api/masters/people", { data: { name, employment: "direct" } })).json();
    const res = await api.put(`/api/masters/people/${person.id}/sites/${await siteId("SMTW")}`, {
      data: { role: "maint_technician", all_units: true, unit_ids: [] },
    });
    expect(res.ok(), await res.text()).toBe(true);
  } finally {
    await api.dispose();
  }
  await openTeam(page, "engineer");
  await rows(page).filter({ hasText: name }).getByTitle("Edit").click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.locator('[data-test="access-lines"]')).toHaveCount(0);
  await dialog.getByRole("button", { name: "Remove", exact: true }).click();
  await expect(dialog.locator('[data-test="access-lines"]')).toHaveText("Saving removes access: SMTW Technician (all units).");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await dialog.getByRole("button", { name: "Discard" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
});

test("S064: the Team search and site select filter the list", async ({ page }) => {
  await openTeam(page, "it_admin");
  const search = page.getByRole("searchbox", { name: "Search people" });
  await search.fill("muthu");
  await expect(rows(page).filter({ hasText: "Muthu (operator)" })).toBeVisible();
  await expect(rows(page).filter({ hasText: "Priya (engineer)" })).toHaveCount(0);
  await search.fill("");
  await page.getByRole("combobox", { name: "Filter by site" }).selectOption({ label: "BRICKS" });
  await expect(rows(page).filter({ hasText: "Arun (manager)" })).toBeVisible();
  await expect(rows(page).filter({ hasText: "Muthu (operator)" })).toHaveCount(0);
});

test("S064 CR1-01: Add person with the row save and the list reload both failing still becomes Edit person; a second Save sends no POST", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowBrowserError("net::ERR_FAILED");
  const name = `E2E dropped ${propertyTag(testInfo)}`;
  const code = ownUnitCode();
  const api = await apiAs("admin");
  try {
    const res = await api.post("/api/masters/units", { data: { site_id: await siteId("SMTW"), code, name: `E2E unit ${propertyTag(testInfo)}` } });
    expect(res.status(), await res.text()).toBe(201);

    await openTeam(page, "engineer");
    await page.getByRole("button", { name: "Add person" }).click();
    await expectDialogFits(page);
    const dialog = await openDialog(page);
    await dialog.getByLabel("Name", { exact: true }).fill(name);
    await dialog.getByLabel("Site to add").selectOption({ index: 1 });
    await dialog.getByRole("button", { name: "Add", exact: true }).click();
    await dialog.getByLabel(code, { exact: true }).check();

    // The connection drops after the POST: the row's PUT and the list reload both fail
    let posts = 0;
    await page.route("**/api/masters/people**", (route) => {
      const req = route.request();
      if (req.method() === "POST") { posts += 1; return route.continue(); }
      return route.abort("failed");
    });
    await dialog.locator(".modal-footer button[type=submit]").click();
    await expect(dialog.locator(".modal-title")).toHaveText("Edit person");
    expect(posts).toBe(1);

    // Connection back: the retry saves the row on the same person, with no second POST
    await page.unroute("**/api/masters/people**");
    await page.route("**/api/masters/people**", (route) => {
      if (route.request().method() === "POST") posts += 1;
      return route.continue();
    });
    await dialog.locator(".modal-footer button[type=submit]").click();
    await expect(dialog).toBeHidden();
    expect(posts).toBe(1);
    await expect(rows(page).filter({ hasText: name })).toHaveCount(1);
  } finally {
    await api.dispose();
  }
});

test("S064: Add person as an engineer offers only the engineer's site; a row refused on Save leaves the dialog as Edit person with the error on the row", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/sites/", 400);
  const tag = propertyTag(testInfo);
  const name = `E2E row refused ${tag}`;
  const code = ownUnitCode();
  const api = await apiAs("admin");
  let unit;
  try {
    const res = await api.post("/api/masters/units", { data: { site_id: await siteId("SMTW"), code, name: `E2E unit ${tag}` } });
    expect(res.status(), await res.text()).toBe(201);
    unit = await res.json();

    await openTeam(page, "engineer");
    await page.getByRole("button", { name: "Add person" }).click();
    await expectDialogFits(page);
    const dialog = await openDialog(page);
    await dialog.getByLabel("Name", { exact: true }).fill(name);
    const siteToAdd = dialog.getByLabel("Site to add");
    await expect(siteToAdd.locator("option")).toHaveCount(2); // "Add a site…" and SMTW, not BRICKS
    await expect(siteToAdd.locator("option").nth(1)).toHaveText(/^SMTW — /);
    await siteToAdd.selectOption({ index: 1 });
    await dialog.getByRole("button", { name: "Add", exact: true }).click();
    await dialog.getByLabel(code, { exact: true }).check();

    // The unit goes inactive behind the dialog's back: the row's save is refused by the real server
    expect((await api.put(`/api/masters/units/${unit.id}`, { data: { active: false } })).ok()).toBe(true);
    await dialog.locator(".modal-footer button[type=submit]").click();
    await expect(dialog.locator(".modal-title")).toHaveText("Edit person");
    await expectFieldMessage(dialog, `Unit ${code} is inactive. Untick it or reactivate it.`);
    // The person was saved and is in the list behind the dialog
    await dialog.getByRole("button", { name: "Cancel" }).click();
    await expect(dialog.getByText("Discard your changes?")).toBeVisible(); // the failed row is unsaved
    await dialog.getByRole("button", { name: "Discard" }).click();
    await expect(rows(page).filter({ hasText: name })).toBeVisible();
  } finally {
    await api.dispose();
  }
});
