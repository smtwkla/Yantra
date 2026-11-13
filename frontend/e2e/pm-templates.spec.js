// PM templates (S104; R03.18) — Masters › PM templates, the template page and the item dialog with its two reading
// kinds, in place of the step's manual checks. The engineer writes the work once; a change reaches every machine
// the template is on. Template names are unique in the lane's database, so each carries the test's machine code or
// project name. Set-up by API (S024; support/pm.js); every dialog a flow opens must fit (expectDialogFits).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { meterMachine } from "./support/meters.js";
import { pmPlanByApi } from "./support/pm.js";
import { asPerson } from "./support/people.js";
import { istDay, saveDialog, shownDay } from "./support/tickets.js";

/** The visible row of the item whose text is `text` (a table from md, a list below it). */
const itemRow = (page, text) => page.getByTestId("pm-items").locator("li, tr").filter({ hasText: text, visible: true });

async function addItem(page, { type = "Check", text, kind = null }) {
  await page.getByRole("button", { name: "Add item", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.locator("label.btn", { hasText: type }).click();
  await dialog.getByLabel("What to do or check").fill(text);
  if (kind) await dialog.getByLabel(kind, { exact: true }).check();
  return dialog;
}

test("S104: an engineer adds a template with a Check, a Measurement and a Meter reading, and sees it in "
  + "Masters › PM templates with its trigger in words", async ({ page }, testInfo) => {
  const name = `S104 write ${testInfo.project.name}`;
  await asPerson(page, "engineer", "/masters?section=pm_templates");
  await page.getByRole("link", { name: "Add PM template" }).click();
  await expect(page.getByRole("heading", { name: "New PM template" })).toBeVisible();
  await page.getByLabel("Name").fill(name);
  await page.getByLabel("By calendar: every").check();
  await page.getByLabel("Calendar interval").fill("1");
  await page.getByLabel("Calendar unit").selectOption("month");
  await page.getByLabel("By meter: every").check();
  await page.getByLabel("Meter interval").fill("250");
  await page.getByLabel("Meter type", { exact: true }).selectOption({ label: "Run hours" });
  // S104 A1: no parent tick on the template page; its note names the link on the part's Meters card
  await expect(page.getByText("use the meter from a parent node")).toHaveCount(0);
  await expect(page.getByTestId("pm-meter-note")).toContainText("or the meter of a node above that its Meters card links");

  await addItem(page, { type: "Check", text: "Oil level in the sight glass is above min" });
  await saveDialog(page, "Save item");
  let dialog = await addItem(page, { type: "Reading", text: "Main pressure at full load", kind: "Measurement" });
  await dialog.getByLabel("Unit").fill("bar");
  await dialog.getByLabel("Min", { exact: true }).fill("180");
  await dialog.getByLabel("Max", { exact: true }).fill("200");
  await saveDialog(page, "Save item");
  dialog = await addItem(page, { type: "Reading", text: "Power-pack oil temperature", kind: "Meter reading" });
  await expect(dialog).toContainText("Unit and limits come from each machine's meter.");
  await expect(dialog.getByRole("checkbox")).toHaveCount(0);   // S104 A1: no parent tick in the item dialog
  await dialog.getByLabel("Meter type").selectOption({ label: "Oil temperature (°C)" });
  await saveDialog(page, "Save item");
  await expect(itemRow(page, "Main pressure at full load")).toContainText("Measurement · 180–200 bar");
  await expect(itemRow(page, "Power-pack oil temperature")).toContainText("Meter reading · Oil temperature");

  await page.getByRole("button", { name: "Save template", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Saved.");
  await expect(page.getByRole("heading", { name })).toBeVisible();
  await page.getByRole("link", { name: "PM templates" }).click();
  const row = page.locator(`[data-template="${name}"]`);
  await expect(row).toContainText("Every month or 250 h, whichever comes first · 3 items · 0 machines");
});

test("S104: a Reading item without a kind, or a Meter reading without a meter type, is refused in the dialog", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/pm/template-item-check", 400);
  await asPerson(page, "engineer", "/masters/pm-templates/new");
  const dialog = await addItem(page, { type: "Reading", text: "Main pressure at full load" });
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Choose Measurement or Meter reading.");
  await dialog.getByLabel("Meter reading", { exact: true }).check();
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Choose a counter or gauge meter type.");
  await expect(page.locator(".modal.show")).toHaveCount(1);
});

test("S104: the template page refuses an empty save beside the fields", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/pm/templates", 400);
  await asPerson(page, "engineer", "/masters/pm-templates/new");
  const save = page.getByRole("button", { name: "Save template", exact: true });
  await save.click();
  await expectFieldMessage(page, "Enter a name.");
  await page.getByLabel("Name").fill("S104 empty save");
  await save.click();
  await expectFieldMessage(page, "Tick By calendar or By meter, or both.");
  await page.getByLabel("By calendar: every").check();
  await save.click();
  await expectFieldMessage(page, "Add at least one item.");
  await expect(page).toHaveURL(/\/pm-templates\/new$/);
});

test("S104: a change of the template's interval moves the machine's next due on the card", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "S104 interval", { unit: "SMTW.MCC2" });
  const plan = await pmPlanByApi(machine, { title: "S104 interval plan", trigger_kind: "calendar", calendar_every: 30,
    calendar_unit: "day", last_done_on: istDay(0), items: [{ item_type: "check", text: "No oil leaks" }] });
  await asPerson(page, "engineer", `/equipment/${machine.id}`);
  const nextDue = page.locator(`[data-plan="${plan.template.name}"]`).getByTestId("pm-next-due");
  await expect(nextDue).toHaveText(`Next due ${shownDay(istDay(30))}`);
  await page.goto(`/masters/pm-templates/${plan.template.id}`);
  await page.getByLabel("Calendar interval").fill("40");
  await page.getByRole("button", { name: "Save template", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Saved.");
  await page.goto(`/equipment/${machine.id}`);
  await expect(nextDue).toHaveText(`Next due ${shownDay(istDay(40))}`);
});

test("S104: a technician opens the template page read-only from the plan page", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "S104 read", { unit: "SMTW.MCC2" });
  const plan = await pmPlanByApi(machine, { title: "S104 read template", trigger_kind: "calendar",
    calendar_every: 1, calendar_unit: "month", items: [{ item_type: "check", text: "S104 read: no oil leaks" }] });
  await asPerson(page, "technician", `/equipment/pm/${plan.id}`);
  await page.getByRole("link", { name: "Open template" }).click();
  await expect(page.getByRole("heading", { name: plan.template.name })).toBeVisible();
  await expect(page.getByTestId("pm-used-on")).toHaveText("Used on 1 machine");
  await expect(page.getByTestId("pm-trigger")).toHaveText("Every month");
  await expect(page.getByTestId("pm-items")).toContainText("S104 read: no oil leaks");
  await expect(page.getByRole("button", { name: "Save template" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Add item" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Deactivate template" })).toHaveCount(0);
});

test("S104: the template page fits a phone: a list of items below 768 px, a table above", { tag: "@device" },
  async ({ page }, testInfo) => {
    const machine = await meterMachine(testInfo, "S104 fit", { unit: "SMTW.MCC2" });
    const plan = await pmPlanByApi(machine, { title: "S104 fit: a template with a long name to wrap on a phone",
      trigger_kind: "calendar", calendar_every: 1, calendar_unit: "month", items: [
        { item_type: "check", text: "S104 fit: oil level in the sight glass is above the minimum mark" },
        { item_type: "task", text: "S104 fit: grease the main bearing" }] });
    await asPerson(page, "engineer", `/masters/pm-templates/${plan.template.id}`);
    await expect(page.getByTestId("pm-items")).toContainText("Items (2)");
    await expectNoSidewaysScroll(page);
    const list = page.getByTestId("pm-item-list");
    const table = page.getByTestId("pm-items").locator("table");
    if (page.viewportSize().width < 768) {
      await expect(list).toBeVisible();
      await expect(table).toBeHidden();
    } else {
      await expect(table).toBeVisible();
      await expect(list).toBeHidden();
    }
  });
