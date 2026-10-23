// Masters › Failure codes (S016) — in place of its manual checks: the pre-filled lists, a class's
// own modes, the label rule, deactivate / reactivate, read-only for an operator, and the lists
// on a phone.
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { apiAs, asPerson, seedIds } from "./support/people.js";
import { causeId, moveByApi, raiseByApi, saveDialog } from "./support/tickets.js";

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
  await page.getByRole("button", { name: "Deactivate" }).click();
  await page.locator(".modal.show").getByRole("button", { name: "Yes", exact: true }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(mode).toHaveCount(0);

  await page.getByLabel("Show inactive").check();
  await expect(mode).toContainText("Inactive");
  await mode.getByTitle("Edit").click();
  await page.getByRole("button", { name: "Reactivate" }).click();
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
for (const section of [
  { button: "Units", add: "Add unit", api: "/api/masters/units", person: "it_admin" },
  { button: "Equip Class", add: "Add class", api: "/api/masters/equipment-classes", person: "engineer" },
  { button: "Equip Type", add: "Add type", api: "/api/masters/equipment-types", person: "engineer" },
  { button: "Trades", add: "Add trade", api: "/api/masters/trades", person: "engineer", message: "Name is required" },
]) {
  test(`${section.person}: the ${section.button} section opens, and an empty ${section.add.toLowerCase()} is refused beside its field`, async ({ page, consoleWatch }) => {
    consoleWatch.allowFailedRequest(section.api, 400);
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

test("operator: the failure codes are read-only, and the lists fit a phone", async ({ page }) => {
  await openFailureCodes(page, "operator");
  for (const list of ["Modes", "Causes", "Actions"]) {
    await page.getByRole("group", { name: "Failure code list" }).getByRole("button", { name: list }).click();
    await expect(rows(page).first()).toBeVisible();
    await expect(page.getByRole("button", { name: /^Add / })).toHaveCount(0);
    await expect(page.getByTitle("Edit")).toHaveCount(0);
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
