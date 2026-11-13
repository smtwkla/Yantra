// PM plans on a machine (S104; R03.18; S096 before it) — the PM card on the equipment page, *Attach PM template*,
// the plan page and *Remove from this machine*, in place of the step's manual checks. Each test makes its own
// machine (meterMachine, in SMTW.MCC2 so the operator's unit holds it) and its templates through the API as the
// engineer (S024: set-up by API; support/pm.js), so no seed machine gains a PM card row. A template name is unique in
// the lane's database, so each carries the machine's code. Every dialog a flow opens must fit (expectDialogFits).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { linkMeterByApi, meterMachine } from "./support/meters.js";
import { pmPlanByApi } from "./support/pm.js";
import { apiAs, asPerson, personId } from "./support/people.js";
import { noModelPart } from "./support/properties.js";
import { istDay, saveDialog } from "./support/tickets.js";

const PRESS_METERS = [["Run hours", {}], ["Oil temperature", {}]];
// The seed technician as the assignee select and the card name him: the name, then the role
const TECHNICIAN = "Kannan (technician) (Technician)";

/** A press of its own in MCC2 with run hours and oil temperature on its model. */
const press = (testInfo, tag, modelMeters = PRESS_METERS) => meterMachine(testInfo, `S104 ${tag}`,
  { unit: "SMTW.MCC2", modelMeters });

async function meterTypeId(name) {
  const api = await apiAs("admin");
  try {
    return (await (await api.get("/api/masters/meter-types")).json()).items.find((t) => t.name === name).id;
  } finally {
    await api.dispose();
  }
}

/** A template as the engineer, not attached -> the template. */
async function templateByApi(name, fields = {}) {
  const api = await apiAs("engineer");
  try {
    const res = await api.post("/api/pm/templates", { data: { name, trigger_kind: "calendar", calendar_every: 1,
      calendar_unit: "month", items: [{ item_type: "check", text: "No oil leaks" }], ...fields } });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/** The PM card's row of the plan whose template is `name`. */
const planRow = (page, name) => page.locator(`[data-testid="pm-card"] [data-plan="${name}"]`);

/** Attach `template` to the machine whose page is open, through the dialog. */
async function attachInDialog(page, template) {
  await page.getByRole("button", { name: "Attach PM template", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("PM template").selectOption({ label: `${template.name} — ${template.trigger_text}` });
  await expect(dialog.getByTestId("pm-attach-preview")).not.toContainText("Loading");
  return dialog;
}

test("S104: on a press, Attach PM template puts it on the card with This machine and its next due; the plan page "
  + "names the press's own Run hours", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "attach");
  const template = await templateByApi(`S104 attach · ${machine.code}`, {
    trigger_kind: "both", meter_type_id: await meterTypeId("Run hours"), meter_every: "250" });
  await asPerson(page, "engineer", `/equipment/${machine.id}`);
  const dialog = await attachInDialog(page, template);
  await expect(dialog.getByTestId("pm-attach-preview")).toContainText(`Uses ${machine.code}'s own Run hours`);
  await saveDialog(page, "Attach template");
  const row = planRow(page, template.name);
  await expect(row).toContainText(`This machine · Every month or 250 h, whichever comes first`);
  await expect(row.getByTestId("pm-next-due")).toContainText("Next due");
  await expect(page.getByTestId("pm-card")).toContainText("PM plans (1)");
  await row.click();
  await expect(page.getByRole("heading", { name: template.name })).toBeVisible();
  await expect(page.getByTestId("pm-plan-source")).toHaveText("Attached to this machine");
  await expect(page.getByTestId("pm-plan-meters")).toContainText(`${machine.code}'s own Run hours`);
  await expect(page.getByRole("link", { name: "Open template" })).toBeVisible();
});

test("S104: a template needing a meter the machine lacks says Does not apply in the dialog and on the card",
  async ({ page }, testInfo) => {
    const machine = await press(testInfo, "lacks", [["Oil temperature", {}]]);
    const template = await templateByApi(`S104 lacks · ${machine.code}`, { trigger_kind: "meter", calendar_every: null,
      calendar_unit: null, meter_type_id: await meterTypeId("Run hours"), meter_every: "250" });
    await asPerson(page, "engineer", `/equipment/${machine.id}`);
    const dialog = await attachInDialog(page, template);
    await expect(dialog.getByTestId("pm-attach-preview")).toContainText(
      `Does not apply here: no Run hours meter on ${machine.code}. You can attach it; it makes no job until the meter is added.`);
    await saveDialog(page, "Attach template");
    await expect(planRow(page, template.name).getByTestId("pm-stop-remark")).toHaveText(
      `Does not apply: no Run hours meter on ${machine.code}.`);
    await planRow(page, template.name).click();
    await expect(page.getByTestId("pm-plan-meters")).toContainText(
      `Does not apply: no Run hours meter on ${machine.code}`);
  });

test("S104: Remove from this machine moves the plan to Not in use; attaching again brings it back with its assignee",
  async ({ page }, testInfo) => {
    const machine = await press(testInfo, "remove");
    const plan = await pmPlanByApi(machine, { title: "S104 remove plan", trigger_kind: "calendar", calendar_every: 1,
      calendar_unit: "month", items: [{ item_type: "check", text: "No oil leaks" }],
      assignee_id: await personId("technician") });
    await asPerson(page, "engineer", `/equipment/pm/${plan.id}`);
    await page.getByRole("button", { name: "Remove from this machine" }).click();
    await expect(page.getByRole("alert")).toContainText(
      `Remove this template from ${machine.code}? Its job that has not started is cancelled.`);
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await expect(page.getByTestId("pm-stop-remark")).toContainText("The template was removed from this machine.");

    await page.goto(`/equipment/${machine.id}`);
    const card = page.getByTestId("pm-card");
    await expect(card).toContainText("PM plans (0)");
    await expect(planRow(page, plan.template.name)).toHaveCount(0);
    await card.getByRole("button", { name: "Not in use (1)" }).click();
    await expect(planRow(page, plan.template.name)).toContainText("Removed from this machine");

    const dialog = await attachInDialog(page, { name: plan.template.name, trigger_text: "Every month" });
    await expect(dialog.getByTestId("pm-attach-preview")).toContainText("Uses no meter.");
    await saveDialog(page, "Attach template");
    await expect(card).toContainText("PM plans (1)");
    await expect(planRow(page, plan.template.name)).toContainText(TECHNICIAN);
  });

test("S104: the engineer sets the machine's assignee and Last done on the plan page", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "settings");
  const plan = await pmPlanByApi(machine, { title: "S104 settings plan", trigger_kind: "calendar",
    calendar_every: 1, calendar_unit: "month", items: [{ item_type: "check", text: "No oil leaks" }] });
  await asPerson(page, "engineer", `/equipment/pm/${plan.id}`);
  await page.getByLabel("Assign jobs to").selectOption({ label: TECHNICIAN });
  await page.getByLabel("Last done (before Yantra)").fill(istDay(-5));
  await page.getByRole("button", { name: "Save plan", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/equipment/${machine.id}$`));
  await expect(planRow(page, plan.template.name)).toContainText(`1 item · ${TECHNICIAN}`);
});

test("S104: the technician and IT admin read the plan but cannot change it", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "read");
  const plan = await pmPlanByApi(machine, { title: "S104 read plan", trigger_kind: "calendar", calendar_every: 1,
    calendar_unit: "month", items: [{ item_type: "check", text: "S104 read: no oil leaks" }] });
  for (const key of ["technician", "it_admin"]) {
    await asPerson(page, key, `/equipment/${machine.id}`);
    await expect(planRow(page, plan.template.name)).toContainText("Every month");
    await expect(page.getByRole("button", { name: "Attach PM template" })).toHaveCount(0);
    await planRow(page, plan.template.name).click();
    await expect(page.getByTestId("pm-plan-items")).toContainText("S104 read: no oil leaks");
    await expect(page.getByRole("button", { name: "Save plan" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Remove from this machine" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Back to the equipment" })).toBeVisible();
  }
});

test("S104: a plan on a part counts on the linked meter: Does not apply before the link, the press's Run hours after",
  async ({ page }, testInfo) => {
    // S104 A1.9: a part uses its machine's meter only through a link on its Meters card
    const machine = await press(testInfo, "part");
    const part = await noModelPart(machine, { id: machine.class_id }, `S104 gearbox ${testInfo.project.name}`);
    const plan = await pmPlanByApi(part, { title: "Gearbox oil change", trigger_kind: "both", calendar_every: 6,
      calendar_unit: "month", meter_every: "5000", meter_type_id: await meterTypeId("Run hours"),
      items: [{ item_type: "task", text: "Change the gearbox oil" }] });
    await asPerson(page, "engineer", `/equipment/${part.id}`);
    await expect(planRow(page, plan.template.name).getByTestId("pm-stop-remark")).toHaveText(
      `Does not apply: no Run hours meter on ${part.code}.`);
    await linkMeterByApi(part, machine, "Run hours");
    await page.goto(`/equipment/${machine.id}`);
    const row = planRow(page, plan.template.name);
    await expect(row).toContainText(`${part.code} · ${plan.template.name}`);
    await expect(row.getByTestId("pm-next-due")).toContainText("Next due");
    await row.click();
    await expect(page.getByTestId("pm-plan-meters")).toContainText(`${machine.code}'s Run hours (linked meter)`);
  });

test("S104: after the link goes and the part gets its own meter, the Last done meter value is empty and no note shows",
  async ({ page }, testInfo) => {
    // S104 A1.6.3: the value entered for the press's meter stays stored, hidden and unused
    const machine = await press(testInfo, "seed");
    const part = await noModelPart(machine, { id: machine.class_id }, `S104 seed gearbox ${testInfo.project.name}`);
    const hours = await meterTypeId("Run hours");
    const plan = await pmPlanByApi(part, { title: "S104 seed plan", trigger_kind: "meter", meter_every: "5000",
      meter_type_id: hours, meter_equipment_id: machine.id, last_done_meter: "1000",
      items: [{ item_type: "task", text: "Change the gearbox oil" }] });
    await asPerson(page, "engineer", `/equipment/pm/${plan.id}`);
    await expect(page.getByLabel("Meter reading then")).toHaveValue("1000");
    const api = await apiAs("engineer");
    try {
      let res = await api.delete(`/api/equipment/${part.id}/meter-links/${hours}`);
      expect(res.status(), await res.text()).toBe(200);
      res = await api.post(`/api/equipment/${part.id}/meters`, { data: { meter_type_id: hours } });
      expect(res.status(), await res.text()).toBe(201);
    } finally {
      await api.dispose();
    }
    await page.reload();
    await expect(page.getByTestId("pm-plan-meters")).toContainText(`${part.code}'s own Run hours`);
    await expect(page.getByLabel("Meter reading then")).toHaveValue("");
    await expect(page.getByTestId("pm-seed-note")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Clear old meter value" })).toHaveCount(0);
    await expect(page.getByTestId("pm-last-hint")).toHaveText(
      "When was this work last done on this machine, before Yantra? Leave it empty if you do not know.");
  });

test("S104: the plan page fits a phone with no sideways scroll", { tag: "@device" }, async ({ page }, testInfo) => {
  const machine = await press(testInfo, "fit");
  const plan = await pmPlanByApi(machine, { title: "S104 fit: a plan with a long title to wrap on a phone screen",
    trigger_kind: "calendar", calendar_every: 1, calendar_unit: "month", items: [
      { item_type: "check", text: "S104 fit: oil level in the sight glass is above the minimum mark" },
      { item_type: "reading", text: "S104 fit: main pressure at full load", unit: "bar", min_value: "180",
        max_value: "210" }] });
  await asPerson(page, "engineer", `/equipment/pm/${plan.id}`);
  await expect(page.getByTestId("pm-plan-items")).toContainText("Measurement · 180–210 bar");
  await expectNoSidewaysScroll(page);
});

test("S104: a scrapped machine shows no Attach PM template", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "scrapped");
  const api = await apiAs("admin");
  try {
    const res = await api.put(`/api/equipment/${machine.id}`, { data: { lifecycle: "scrapped" } });
    expect(res.status(), await res.text()).toBe(200);
  } finally {
    await api.dispose();
  }
  await asPerson(page, "engineer", `/equipment/${machine.id}`);
  await expect(page.getByRole("button", { name: "Attach PM template" })).toHaveCount(0);
});
