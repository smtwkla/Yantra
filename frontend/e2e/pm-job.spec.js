// Doing a PM job on the phone (S098; R03.4) — the job page in place of the step's manual checks. Each test makes
// its own machine (meterMachine, in SMTW.MCC2 so the operator's unit holds it, with run hours and an oil
// temperature gauge 20–80 °C on its model) and its plan through the API as the engineer (S024: set-up by API):
// three items (a check, a task, a free reading 30–60 °C), every 10 days, last done 20 days ago, so the save makes
// the job at once and it reads Overdue (due 10 days ago, grace 1); the technician is the assignee. Each test finds
// its own job by the machine (the lane's database holds other tests' jobs).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { logByApi, meterMachine } from "./support/meters.js";
import { changeTemplateByApi, pmPlanByApi } from "./support/pm.js";
import { apiAs, asPerson, personId } from "./support/people.js";
import { card, istDay, istLocal, saveDialog, setEventTime, shownTime } from "./support/tickets.js";

const CHECK = "No oil leaks at the cylinder seals";
const TASK = "Grease the main bearing";
const READING = "Power-pack oil temperature";
const ITEMS = [
  { item_type: "check", text: CHECK },
  { item_type: "task", text: TASK },
  { item_type: "reading", text: READING, unit: "°C", min_value: "30", max_value: "60" },
];

const press = (testInfo, tag) => meterMachine(testInfo, `S098 ${tag}`, { unit: "SMTW.MCC2",
  modelMeters: [["Run hours", {}], ["Oil temperature", { min_value: "20", max_value: "80" }]] });

async function withApi(key, work) {
  const api = await apiAs(key);
  try {
    return await work(api);
  } finally {
    await api.dispose();
  }
}

/** A plan on `machine` as the engineer (S104: a template attached to it), past due (its job made at the save) ->
 * the plan. */
async function planByApi(machine, title, { items = ITEMS, extra = {} } = {}) {
  const assigneeId = await personId("technician");
  return pmPlanByApi(machine, { title, trigger_kind: "calendar", calendar_every: 10, calendar_unit: "day",
    last_done_on: istDay(-20), assignee_id: assigneeId, items, ...extra });
}

/** The open (or done) job of `machine`, from the PM list's API -> the list item. */
function jobOf(machine, tab = "due") {
  return withApi("engineer", async (api) => {
    const items = (await (await api.get(`/api/pm/jobs?tab=${tab}`)).json()).items;
    const job = items.find((j) => j.equipment.id === machine.id);
    expect(job, `no job of ${machine.code}`).toBeTruthy();
    return job;
  });
}

/** Start the job through the API as the technician, now, performed by himself -> the job page's answer. */
function startByApi(job) {
  return withApi("technician", async (api) => {
    const res = await api.post(`/api/pm/jobs/${job.id}/start`,
      { data: { performed_by_id: await personId("technician"), started_at: null } });
    expect(res.status(), await res.text()).toBe(200);
    return await res.json();
  });
}

function meterTypeId(name) {
  return withApi("admin", async (api) => (await (await api.get("/api/masters/meter-types")).json()).items
    .find((t) => t.name === name).id);
}

const itemRow = (page, text) => page.locator(`.pm-item[data-item="${text}"]`);
const filled = (page) => page.getByTestId("pm-filled");
const answer = (page, text, name) => itemRow(page, text).getByRole("button", { name, exact: true });

/** Tap `name` on the item and wait for its save. */
async function tap(page, text, name) {
  await answer(page, text, name).click();
  await expect(answer(page, text, name)).toHaveAttribute("aria-pressed", "true");
}

async function typeReading(page, text, value) {
  const row = itemRow(page, text);
  await row.getByRole("textbox", { name: text }).fill(value);
  await row.getByRole("button", { name: "Save", exact: true }).click();
}

test("S098: a technician starts a due job, fills each item and marks it done", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "flow");
  await planByApi(machine, "S098 flow plan");
  const job = await jobOf(machine);
  await asPerson(page, "technician", "/pm");
  await page.locator(`.job-row[data-equipment="${machine.code}"]`).click();
  await expect(page).toHaveURL(new RegExp(`/pm/jobs/${job.id}$`));
  await expect(page.getByRole("heading", { name: job.serial })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start job" })).toBeVisible();
  await expect(page.getByText("These are the plan's items now. Start the job to fill them.")).toBeVisible();
  await expect(page.locator(".pm-item")).toHaveCount(3);
  await expect(answer(page, CHECK, "OK")).toHaveCount(0);               // read-only before Start
  await expect(page.getByLabel("Performed by")).toHaveValue(String(await personId("technician")));
  await expect(page.getByRole("checkbox", { name: "Now", exact: true })).toBeChecked();
  await page.getByRole("button", { name: "Start job" }).click();
  await expect(filled(page)).toHaveText("0 of 3 filled");
  await tap(page, CHECK, "OK");
  await tap(page, TASK, "Done");
  await typeReading(page, READING, "48.5");
  await expect(filled(page)).toHaveText("3 of 3 filled");
  await page.getByRole("button", { name: "Mark job done" }).click();
  await expectDialogFits(page);
  await saveDialog(page, "Mark job done");
  await expect(page.locator(".badge", { hasText: /^Done$/ }).first()).toBeVisible();
  await expect(page.locator(".badge", { hasText: /^Late$/ })).toBeVisible();
  const history = card(page, "History");
  await expect(history).toContainText("Started");
  await expect(history).toContainText("Done");
  await expect(page.getByRole("button", { name: "Mark job done" })).toHaveCount(0);
  await page.goto("/pm?tab=to_verify"); // S099: its plan needs verification, so the job waits on To verify
  await expect(page.locator(`.job-row[data-equipment="${machine.code}"]`)).toContainText(job.serial);
});

test("S098: each item is saved as it is filled; a reload keeps them", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "reload");
  await planByApi(machine, "S098 reload plan");
  const job = await startByApi(await jobOf(machine));
  await asPerson(page, "technician", `/pm/jobs/${job.id}`);
  await tap(page, CHECK, "OK");
  await answer(page, TASK, "Not done").click();                          // opens the remark field
  await itemRow(page, TASK).getByLabel("Why was it not done?").fill("No grease in the store");
  await itemRow(page, TASK).getByRole("button", { name: "Save", exact: true }).click();
  await expect(filled(page)).toHaveText("2 of 3 filled");
  await page.reload();
  await expect(answer(page, CHECK, "OK")).toHaveAttribute("aria-pressed", "true");
  await expect(answer(page, TASK, "Not done")).toHaveAttribute("aria-pressed", "true");
  await expect(filled(page)).toHaveText("2 of 3 filled");
  await expect(page.getByRole("button", { name: "Mark job done" })).toBeDisabled();
  await expect(page.getByText("Fill all 3 items first. Your entries are saved as you go.")).toBeVisible();
});

test("S098: a reading out of its limits shows High as it is typed", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "limits");
  await planByApi(machine, "S098 limits plan");
  const job = await startByApi(await jobOf(machine));
  await asPerson(page, "technician", `/pm/jobs/${job.id}`);
  const row = itemRow(page, READING);
  await row.getByRole("textbox", { name: READING }).fill("62");
  await expect(row.getByTestId("limit-flag")).toHaveText("High");          // before Save
  await row.getByRole("button", { name: "Save", exact: true }).click();
  await expect(row.getByText("Saved")).toBeVisible();
  await expect(row.getByTestId("limit-flag")).toHaveText("High");
  await expect(row).toHaveClass(/list-group-item-danger/);
  await row.getByRole("textbox", { name: READING }).fill("45");
  await expect(row.getByTestId("limit-flag")).toHaveCount(0);
  await row.getByRole("button", { name: "Save", exact: true }).click();
  await expect(row.getByText("Saved")).toBeVisible();
  await expect(row.getByTestId("limit-flag")).toHaveCount(0);
});

test("S098: Not OK needs a remark and shows on a red row", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/results/", 400);
  const machine = await press(testInfo, "not ok");
  await planByApi(machine, "S098 not ok plan");
  const job = await startByApi(await jobOf(machine));
  await asPerson(page, "technician", `/pm/jobs/${job.id}`);
  const row = itemRow(page, CHECK);
  await answer(page, CHECK, "Not OK").click();
  await row.getByRole("button", { name: "Save", exact: true }).click();
  await expectFieldMessage(page, "Say what is wrong.");
  await row.getByLabel("What is wrong?").fill("Oil seeping at the left rod seal");
  await row.getByRole("button", { name: "Save", exact: true }).click();
  await expect(answer(page, CHECK, "Not OK")).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(itemRow(page, CHECK)).toContainText("Oil seeping at the left rod seal");
  await expect(itemRow(page, CHECK)).toHaveClass(/list-group-item-danger/);
});

test("S098: a reading that logs a meter is refused on the item when the counter is lower",
  async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/results/", 400);
  const machine = await press(testInfo, "counter");
  await logByApi(machine, "Run hours", "1260", istLocal(60));
  await planByApi(machine, "S098 counter plan", { items: [{ item_type: "reading", text: "Run hours",
    meter_equipment_id: machine.id, meter_type_id: await meterTypeId("Run hours") }] });
  const job = await startByApi(await jobOf(machine));
  await asPerson(page, "technician", `/pm/jobs/${job.id}`);
  const row = itemRow(page, "Run hours");
  await typeReading(page, "Run hours", "1200");
  await expect(row).toContainText("Lower than the reading of");
  await expect(row.getByLabel("Meter reset")).toBeVisible();
  await expect(filled(page)).toHaveText("0 of 1 filled");
  await expect(row).not.toContainText("Also logged");
  await typeReading(page, "Run hours", "1270");
  await expect(row.getByText("Saved")).toBeVisible();
  await expect(row).toContainText(`Also logged as a Run hours reading of ${machine.code}.`);
  await expect(filled(page)).toHaveText("1 of 1 filled");
  await page.goto(`/equipment/${machine.id}`);
  await expect(card(page, "Meters").getByTestId("node-meter").filter({ hasText: "Run hours" })).toContainText("1,270");
});

test("S098: recorded on behalf: another person and a start two days back", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/done", 400);
  const machine = await press(testInfo, "on behalf");
  await planByApi(machine, "S098 on behalf plan", { items: [ITEMS[0]] });
  const job = await jobOf(machine);
  const started = istLocal(2 * 24 * 60);
  await asPerson(page, "technician", `/pm/jobs/${job.id}`);
  const performer = page.getByLabel("Performed by");
  const ramesh = performer.locator("option", { hasText: "Ramesh" });
  await performer.selectOption(await ramesh.getAttribute("value"));
  await setEventTime(page.getByTestId("pm-start"), started);
  await page.getByRole("button", { name: "Start job" }).click();
  const work = page.getByTestId("pm-work");
  await expect(work.getByLabel("Performed by").locator("option:checked")).toContainText("Ramesh");
  await expect(work).toContainText(`Started ${shownTime(started)}`);
  await tap(page, CHECK, "OK");
  await page.getByRole("button", { name: "Mark job done" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await setEventTime(dialog, istLocal(2 * 24 * 60 + 30));
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, /Done must be at or after Started/);
});

test("S098: a started job keeps its items when the plan changes", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "keeps");
  const plan = await planByApi(machine, "S098 keeps plan");
  const job = await startByApi(await jobOf(machine));
  const other = await press(testInfo, "follows");
  const otherPlan = await planByApi(other, "S098 follows plan");
  const otherJob = await jobOf(other);
  // S104: the work is the template's, so the item is added there (a template PUT)
  const added = (p) => ({ items: [...p.items.map((i) => ({ id: i.id, item_type: i.item_type, text: i.text,
    help_text: i.help_text, photo: i.photo, reading_kind: i.reading_kind, unit: i.unit, min_value: i.min_value,
    max_value: i.max_value, meter_type_id: i.meter_type?.id ?? null })),
  { item_type: "task", text: "Check the return filter" }] });
  for (const p of [plan, otherPlan]) await changeTemplateByApi(p, added(p));
  await asPerson(page, "technician", `/pm/jobs/${job.id}`);
  await expect(filled(page)).toHaveText("0 of 3 filled");
  await expect(itemRow(page, "Check the return filter")).toHaveCount(0);
  await page.goto(`/pm/jobs/${otherJob.id}`);
  await expect(page.locator(".pm-item")).toHaveCount(4);
  await expect(itemRow(page, "Check the return filter")).toBeVisible();
});

test("S098: a save during a network drop says Not saved and keeps the tap; it saves on the next tap",
  async ({ page, consoleWatch }, testInfo) => {
    consoleWatch.allowBrowserError("ERR_INTERNET_DISCONNECTED");
    const machine = await press(testInfo, "offline");
    await planByApi(machine, "S098 offline plan");
    const job = await startByApi(await jobOf(machine));
    await asPerson(page, "technician", `/pm/jobs/${job.id}`);
    await tap(page, CHECK, "OK");
    await page.context().setOffline(true);
    // a failed change of Performed by shows the saved person again (CR2-03), so a pick of the other can be retried
    const performer = page.getByTestId("pm-work").getByLabel("Performed by");
    const saved = await performer.inputValue();
    const other = performer.locator(`option:not([value="${saved}"])`).first();
    await performer.selectOption(await other.getAttribute("value"));
    await expect(page.getByTestId("pm-work")).toContainText("Not saved. No connection.");
    await expect(performer).toHaveValue(saved);
    await answer(page, TASK, "Done").click();
    await expect(itemRow(page, TASK)).toContainText("Not saved. No connection.");
    await expect(answer(page, TASK, "Done")).toHaveAttribute("aria-pressed", "false");
    await expect(filled(page)).toHaveText("1 of 3 filled");
    await page.context().setOffline(false);
    await answer(page, TASK, "Done").click();
    await expect(itemRow(page, TASK).getByText("Saved")).toBeVisible();
    await expect(filled(page)).toHaveText("2 of 3 filled");
    await page.reload();
    await expect(answer(page, CHECK, "OK")).toHaveAttribute("aria-pressed", "true");
    await expect(answer(page, TASK, "Done")).toHaveAttribute("aria-pressed", "true");
  });

test("S098: IT admin and the operator read the job and have no Start job", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "readers");
  await planByApi(machine, "S098 readers plan");
  const job = await jobOf(machine);
  for (const key of ["it_admin", "operator"]) {
    await asPerson(page, key, `/pm/jobs/${job.id}`);
    await expect(page.getByRole("heading", { name: job.serial })).toBeVisible();
    await expect(itemRow(page, CHECK)).toBeVisible();
    await expect(page.getByText("These are the plan's items now.", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Start job" })).toHaveCount(0);
  }
});

test("S098: the job page fits a phone with large item buttons", { tag: "@device" }, async ({ page }, testInfo) => {
  const machine = await press(testInfo, "fit");
  await planByApi(machine, "S098 fit plan with a long title to wrap on a phone screen");
  const job = await startByApi(await jobOf(machine));
  await asPerson(page, "technician", `/pm/jobs/${job.id}`);
  await expect(answer(page, CHECK, "OK")).toBeVisible();
  await expectNoSidewaysScroll(page);
  const boxes = await Promise.all(["OK", "Not OK", "NA"].map((name) => answer(page, CHECK, name).boundingBox()));
  for (const box of boxes) expect(box.height).toBeGreaterThanOrEqual(44);
  expect(new Set(boxes.map((box) => Math.round(box.y))).size, "the three buttons are not on one row").toBe(1);
});
