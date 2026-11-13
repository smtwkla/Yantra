// PM jobs come due (S097; R03.3) — the PM list and the open job on the equipment page's PM card, in place of
// the step's manual checks. Each test makes its own machine (meterMachine, in SMTW.MCC2 so the operator's unit
// holds it) and its plans through the API as the engineer (S024: set-up by API). No daily run happens in a browser
// test: a plan saved inside its window gets its job at the save (D5). Day intervals keep the dates plain: every
// 10 days, last done 20 days ago -> due 10 days ago, grace 1 -> Overdue; last done 9 days ago -> due tomorrow,
// upcoming 1 -> Upcoming. Each test finds its own row by the machine's code (the lane's database holds other
// tests' jobs).
import { test, expect } from "./support/test.js";
import { expectNoSidewaysScroll } from "./support/dialogs.js";
import { logByApi, meterMachine } from "./support/meters.js";
import { navItem } from "./support/nav.js";
import { pmPlanByApi } from "./support/pm.js";
import { apiAs, asPerson, personId } from "./support/people.js";
import { istDay, istLocal, shownDay } from "./support/tickets.js";

const TECHNICIAN_NAME = "Kannan (technician)";

/** A press of its own in MCC2 with run hours on its model. */
const press = (testInfo, tag) => meterMachine(testInfo, `S097 ${tag}`, { unit: "SMTW.MCC2",
  modelMeters: [["Run hours", {}]] });

/** A plan on `node` through the API as the engineer (S104: a template attached to it): every 10 days, last done
 * `doneDaysAgo` days ago. */
function planByApi(node, title, { doneDaysAgo = 20, extra = {} } = {}) {
  return pmPlanByApi(node, { title, trigger_kind: "calendar", calendar_every: 10, calendar_unit: "day",
    last_done_on: istDay(-doneDaysAgo), items: [{ item_type: "check", text: "No oil leaks" }], ...extra });
}

async function runHoursId() {
  const api = await apiAs("admin");
  try {
    const types = (await (await api.get("/api/masters/meter-types")).json()).items;
    return types.find((t) => t.name === "Run hours").id;
  } finally {
    await api.dispose();
  }
}

/** The open job of `plan` on `machine`, from the PM list's API as the engineer (S098). */
async function jobOf(machine, plan) {
  const api = await apiAs("engineer");
  try {
    const items = (await (await api.get("/api/pm/jobs?tab=upcoming")).json()).items
      .concat((await (await api.get("/api/pm/jobs")).json()).items);
    return items.find((j) => j.equipment.id === machine.id && j.plan.id === plan.id);
  } finally {
    await api.dispose();
  }
}

/** The PM list's row of the job on `machine`. */
const jobRow = (page, machine) => page.locator(`.job-row[data-equipment="${machine.code}"]`);
/** The PM card's row of the plan titled `title`. */
const planRow = (page, title) => page.locator(`[data-testid="pm-card"] [data-plan="${title}"]`);
const tabLink = (page, name) => page.locator(".nav-tabs").getByRole("link", { name, exact: true });

test("S097: a plan saved past due shows its job as Overdue on the PM list", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "overdue");
  const plan = await planByApi(machine, "S097 overdue plan", { extra: { assignee_id: await personId("technician") } });
  await asPerson(page, "technician", "/me");
  await navItem(page, "PM").click();
  await expect(page).toHaveURL(/\/pm$/);
  await expect(tabLink(page, "Due")).toHaveClass(/active/);
  const row = jobRow(page, machine);
  await expect(row.locator(".badge")).toHaveText("Overdue");
  await expect(row).toContainText(/PM-\d{4}-\d{2}-\d{3}/);
  await expect(row).toContainText(`${shownDay(istDay(-10))} · 10 days ago`);
  await expect(row).toContainText(`${machine.code} — ${machine.name}`);
  await expect(row).toContainText(`${plan.template.name} · 1 item`);
  await expect(row).toContainText(`SMTW.MCC2 · ${TECHNICIAN_NAME}`);
  const job = await jobOf(machine, plan);
  await row.click();
  await expect(page).toHaveURL(new RegExp(`/pm/jobs/${job.id}$`));                   // S098: the job page
  await expect(page.getByRole("heading", { name: job.serial })).toBeVisible();
});

test("S097: a job inside its window shows under Upcoming, not under Due", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "upcoming");
  await planByApi(machine, "S097 upcoming plan", { doneDaysAgo: 9 });
  await asPerson(page, "technician", "/pm");
  await expect(tabLink(page, "Due")).toHaveClass(/active/);
  await expect(page.locator(".job-row").first().or(page.getByText("No PM jobs are due."))).toBeVisible();
  await expect(jobRow(page, machine)).toHaveCount(0);
  await tabLink(page, "Upcoming").click();
  await expect(page).toHaveURL(/tab=upcoming/);
  const row = jobRow(page, machine);
  await expect(row.locator(".badge")).toHaveText("Upcoming");
  await expect(row).toContainText(shownDay(istDay(1)));
  await expect(page.getByTestId("pm-counts")).toContainText("upcoming");
});

test("S097: the equipment page's PM card shows the open job and the next due date", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "card");
  const duePlan = await planByApi(machine, "S097 card due plan", { doneDaysAgo: 10 });
  const laterPlan = await planByApi(machine, "S097 card later plan", { doneDaysAgo: 0, extra: { calendar_every: 30 } });
  await asPerson(page, "technician", `/equipment/${machine.id}`);
  const due = planRow(page, duePlan.template.name);
  await expect(due.getByTestId("pm-open-job").locator(".badge")).toHaveText("Due");
  await expect(due.getByTestId("pm-open-job")).toContainText(new RegExp(`PM-\\d{4}-\\d{2}-\\d{3} · ${shownDay(istDay(0))}`));
  await expect(planRow(page, laterPlan.template.name).getByTestId("pm-next-due"))
    .toHaveText(`Next due ${shownDay(istDay(30))}`);
});

test("S097: deactivating the plan takes its job off the PM list", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "deactivate");
  const plan = await planByApi(machine, "S097 deactivate plan");
  await asPerson(page, "technician", "/pm");
  await expect(jobRow(page, machine)).toHaveCount(1);
  // S104: the plan stops when its template is deactivated
  await asPerson(page, "engineer", `/masters/pm-templates/${plan.template.id}`);
  await page.getByRole("button", { name: "Deactivate template" }).click();
  await page.getByRole("button", { name: "Yes", exact: true }).click();
  await expect(page.getByText("This template is inactive. Its machines get no jobs.")).toBeVisible();
  await asPerson(page, "technician", "/pm");
  await expect(page.locator(".job-row").first().or(page.getByText("No PM jobs are due."))).toBeVisible();
  await expect(jobRow(page, machine)).toHaveCount(0);
});

test("S097: a meter plan comes due when the reading passes its due value", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "meter");
  await logByApi(machine, "Run hours", "1260", istLocal(60));       // first: the save makes the job (BR1-08)
  await planByApi(machine, "S097 meter plan", { extra: {
    trigger_kind: "meter", calendar_every: null, calendar_unit: null, last_done_on: null,
    meter_equipment_id: machine.id, meter_type_id: await runHoursId(), meter_every: "250", last_done_meter: "1000",
  } });
  await asPerson(page, "technician", "/pm");
  const row = jobRow(page, machine);
  await expect(row.locator(".badge")).toHaveText("Due");
  await expect(row).toContainText("at 1,250 h");
  await expect(row).toContainText("Run hours now 1,260.0 h");
});

test("S097: Assigned to me shows only my jobs", async ({ page }, testInfo) => {
  const mine = await press(testInfo, "mine");
  const nobody = await press(testInfo, "nobody");
  await planByApi(mine, "S097 my plan", { extra: { assignee_id: await personId("technician") } });
  await planByApi(nobody, "S097 nobody's plan");
  await asPerson(page, "technician", "/pm");
  await expect(jobRow(page, nobody)).toContainText("No one yet");
  await page.getByLabel("Assigned to me").check();
  await expect(page).toHaveURL(/assigned=me/);
  await expect(jobRow(page, mine)).toBeVisible();
  await expect(jobRow(page, nobody)).toHaveCount(0);
  await page.reload();
  await expect(page).toHaveURL(/assigned=me/);
  await expect(page.getByLabel("Assigned to me")).toBeChecked();
  await expect(jobRow(page, mine)).toBeVisible();
  await expect(jobRow(page, nobody)).toHaveCount(0);
});

test("S097: IT admin reads the PM list and has no Assigned to me", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "it admin");
  await planByApi(machine, "S097 IT admin plan");
  await asPerson(page, "it_admin", "/pm");
  await expect(jobRow(page, machine).locator(".badge")).toHaveText("Overdue");
  await expect(page.getByLabel("Assigned to me")).toHaveCount(0);
});

test("S097: the PM list fits a phone with no sideways scroll", { tag: "@device" }, async ({ page }, testInfo) => {
  for (const tag of ["fit 1", "fit 2", "fit 3"]) {
    await planByApi(await press(testInfo, tag), `S097 ${tag} plan with a long title to wrap on a phone`, {
      extra: { assignee_id: await personId("technician") },
    });
  }
  await asPerson(page, "technician", "/pm");
  await expect(page.locator(".job-row").nth(2)).toBeVisible();
  await expectNoSidewaysScroll(page);
});

test("S098: a started job shows In progress on the Due tab", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "started");
  const plan = await planByApi(machine, "S098 started upcoming plan", { doneDaysAgo: 9 });
  const job = await jobOf(machine, plan);
  const api = await apiAs("technician");
  try {
    const res = await api.post(`/api/pm/jobs/${job.id}/start`,
      { data: { performed_by_id: await personId("technician"), started_at: null } });
    expect(res.status(), await res.text()).toBe(200);
  } finally {
    await api.dispose();
  }
  await asPerson(page, "technician", "/pm");
  const row = jobRow(page, machine);
  await expect(row.locator(".badge").first()).toHaveText("In progress");
  await expect(row).toContainText(`In progress · ${TECHNICIAN_NAME}`);
  await expect(page.getByTestId("pm-counts")).toContainText("in progress");
  await tabLink(page, "Upcoming").click();
  await expect(page).toHaveURL(/tab=upcoming/);
  await expect(page.locator(".job-row").first().or(page.getByText("No PM jobs are coming up."))).toBeVisible();
  await expect(jobRow(page, machine)).toHaveCount(0);
});
