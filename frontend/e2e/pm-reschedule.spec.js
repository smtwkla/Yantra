// Reschedule and skip a PM job (S101; R03.9) — the engineer's moves in place of the step's manual checks.
// Each test makes its own machine (meterMachine, in SMTW.MCC2) and its plan through the API as the engineer (S024:
// set-up by API): a check, every 10 days, last done 20 days ago, so the save makes the job at once (S099's jobFor).
// Each test finds its own job by its machine (the lane's database holds other tests' jobs).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, openDialog } from "./support/dialogs.js";
import { meterMachine } from "./support/meters.js";
import { pmPlanByApi } from "./support/pm.js";
import { apiAs, asPerson, personId } from "./support/people.js";
import { card, istDay, saveDialog, shownDay } from "./support/tickets.js";

const ITEMS = [{ item_type: "check", text: "No oil leaks at the cylinder seals" }];
const MOVE = "Planned shutdown next week";
const SKIP = "Machine idle all month";

const press = (testInfo, tag) => meterMachine(testInfo, `S101 ${tag}`, { unit: "SMTW.MCC2" });

/** A plan on `machine` as the engineer, saved past due (its job made at the save) -> its open job (the list item). */
async function jobFor(machine, title) {
  // S104: a template of the work, attached to the machine (support/pm.js)
  await pmPlanByApi(machine, { title, trigger_kind: "calendar", calendar_every: 10, calendar_unit: "day",
    last_done_on: istDay(-20), assignee_id: await personId("technician"), items: ITEMS });
  const api = await apiAs("engineer");
  try {
    const items = (await (await api.get("/api/pm/jobs?tab=due")).json()).items;
    const job = items.find((j) => j.equipment.id === machine.id);
    expect(job, `no job of ${machine.code}`).toBeTruthy();
    return job;
  } finally {
    await api.dispose();
  }
}

const row = (page, machine) => page.locator(`.job-row[data-equipment="${machine.code}"]`);
const history = (page) => card(page, "History").locator(".list-group-item .fw-semibold");

test("S101: an engineer reschedules a due job, and the page and the list show the move",
  async ({ page, consoleWatch }, testInfo) => {
    consoleWatch.allowFailedRequest("/reschedule", 400);
    const machine = await press(testInfo, "reschedule");
    const job = await jobFor(machine, "S101 reschedule plan");
    await asPerson(page, "engineer", `/pm/jobs/${job.id}`);
    const move = page.getByTestId("pm-move");
    await move.getByRole("button", { name: "Reschedule job" }).click();
    await expectDialogFits(page);
    const dialog = await openDialog(page);
    await dialog.getByLabel("New due date").fill(istDay(5));
    await dialog.locator(".modal-footer button[type=submit]").click();
    await expectFieldMessage(dialog, "Say why the job is moved.");
    await dialog.getByLabel("Why is the job moved?").fill(MOVE);
    await saveDialog(page, "Reschedule job");
    await expect(page.getByTestId("pm-moved-from")).toHaveText(`Moved from ${shownDay(job.due_on)}.`);
    await expect(page.locator(".badge", { hasText: /^Rescheduled$/ })).toBeVisible();
    await expect(history(page).filter({ hasText: /^Rescheduled to / })).toHaveText(`Rescheduled to ${shownDay(istDay(5))}`);
    await expect(card(page, "History")).toContainText(MOVE);
    await page.goto("/pm?tab=upcoming");                                  // due in 5 days: not yet due
    await expect(row(page, machine)).toContainText("Rescheduled");
    await expect(row(page, machine)).toContainText(shownDay(istDay(5)));
  });

test("S101: an engineer skips a due job, and it shows as Skipped on the Done tab", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "skip");
  const job = await jobFor(machine, "S101 skip plan");
  await asPerson(page, "engineer", `/pm/jobs/${job.id}`);
  await page.getByTestId("pm-move").getByRole("button", { name: "Skip job" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByTestId("pm-skip-consequence")).toHaveText(
    "The job is closed as skipped and counts as not done. The next job counts from today. You cannot undo this.");
  await dialog.getByLabel("Why is the job skipped?").fill(SKIP);
  await saveDialog(page, "Skip job");
  await expect(page.locator(".badge", { hasText: /^Skipped$/ })).toBeVisible();
  await expect(page.getByTestId("pm-skipped")).toContainText(SKIP);
  await expect(page.getByTestId("pm-move")).toHaveCount(0);
  await expect(history(page).filter({ hasText: /^Skipped$/ })).toHaveCount(1);
  await page.goto("/pm?tab=done");
  await expect(row(page, machine)).toContainText("Skipped");
  await expect(row(page, machine)).toContainText(job.serial);
  await expect(page.getByTestId("pm-counts")).toContainText(/\b[1-9]\d* skipped\b/);
});

test("S101: the technician sees no Reschedule job or Skip job", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "technician");
  const job = await jobFor(machine, "S101 technician plan");
  await asPerson(page, "technician", `/pm/jobs/${job.id}`);
  await expect(page.getByRole("heading", { name: job.serial })).toBeVisible();
  await expect(page.getByTestId("pm-start").getByRole("button", { name: "Start job" })).toBeVisible();
  await expect(page.getByTestId("pm-move")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Reschedule job" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Skip job" })).toHaveCount(0);
});
