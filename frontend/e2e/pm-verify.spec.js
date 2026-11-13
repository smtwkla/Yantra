// Verify and send back a PM job (S099; R03.5) — the engineer's sign-off in place of the step's manual checks.
// Each test makes its own machine (meterMachine, in SMTW.MCC2) and its plan through the API as the engineer (S024:
// set-up by API): a check and a task, every 10 days, last done 20 days ago, so the save makes the job at once; the
// technician is the assignee.  The job is started, filled (the check Not OK with a remark) and marked done by API.
// Each test finds its own job by its machine and serial (the lane's database holds other tests' jobs).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { meterMachine } from "./support/meters.js";
import { pmPlanByApi } from "./support/pm.js";
import { apiAs, asPerson, personId } from "./support/people.js";
import { card, istDay, saveDialog } from "./support/tickets.js";

// S099 CR2-01: the tab-fit test answers the jobs list with page.route.  WebKit does not route a request while
// the app's service worker (S021) controls the page, so none is started (as me.spec.js and readings.spec.js).
test.use({ serviceWorkers: "block" });

const CHECK = "No oil leaks at the cylinder seals";
const TASK = "Grease the main bearing";
const ITEMS = [{ item_type: "check", text: CHECK }, { item_type: "task", text: TASK }];
const LEAK = "Oil seeping at the left rod seal";
const REWORK = "Re-tighten the left rod seal";

const press = (testInfo, tag) => meterMachine(testInfo, `S099 ${tag}`, { unit: "SMTW.MCC2" });

async function withApi(key, work) {
  const api = await apiAs(key);
  try {
    return await work(api);
  } finally {
    await api.dispose();
  }
}

/** A plan on `machine` as the engineer, saved past due (its job made at the save) -> its open job (the list item). */
async function jobFor(machine, title, extra = {}) {
  // S104: a template of the work, attached to the machine (support/pm.js)
  await pmPlanByApi(machine, { title, trigger_kind: "calendar", calendar_every: 10, calendar_unit: "day",
    last_done_on: istDay(-20), assignee_id: await personId("technician"), items: ITEMS, ...extra });
  return withApi("engineer", async (api) => {
    const items = (await (await api.get("/api/pm/jobs?tab=due")).json()).items;
    const job = items.find((j) => j.equipment.id === machine.id);
    expect(job, `no job of ${machine.code}`).toBeTruthy();
    return job;
  });
}

/** Start the job as `key` for `performer`, answer the check Not OK (with a remark) and the task Done, mark it done. */
function doneByApi(job, key = "technician", performer = "technician") {
  return withApi(key, async (api) => {
    const ok = async (res) => {
      expect(res.status(), await res.text()).toBe(200);
      return res.json();
    };
    const started = await ok(await api.post(`/api/pm/jobs/${job.id}/start`,
      { data: { performed_by_id: await personId(performer), started_at: null } }));
    const answers = { check: { outcome: "not_ok", remark: LEAK }, task: { outcome: "done" } };
    for (const item of started.items) {
      await ok(await api.put(`/api/pm/jobs/${job.id}/results/${item.id}`, { data: answers[item.item_type] }));
    }
    return ok(await api.post(`/api/pm/jobs/${job.id}/done`, { data: {} }));
  });
}

const row = (page, machine) => page.locator(`.job-row[data-equipment="${machine.code}"]`);
const toVerifyTab = (page) => page.locator(".nav-tabs").getByRole("link", { name: /^To verify/ });
const history = (page) => card(page, "History").locator(".list-group-item .fw-semibold");

test("S099: an engineer verifies a done job from the To verify tab", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "verify");
  const job = await jobFor(machine, "S099 verify plan");
  await doneByApi(job);
  await asPerson(page, "engineer", "/pm");
  await toVerifyTab(page).click();
  await expect(row(page, machine)).toContainText(job.serial);
  await expect(row(page, machine)).toContainText("1 Not OK");
  await row(page, machine).click();
  await expect(page.getByRole("heading", { name: job.serial })).toBeVisible();
  await page.getByRole("button", { name: "Verify job" }).click();
  await expectDialogFits(page);
  await saveDialog(page, "Verify job");
  await expect(page.locator(".badge", { hasText: /^Verified$/ })).toBeVisible();
  await expect(page.getByTestId("pm-verified")).toContainText("Verified by");
  await expect(history(page).filter({ hasText: /^Verified$/ })).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Verify job" })).toHaveCount(0);
  await page.goto("/pm?tab=to_verify");
  await expect(toVerifyTab(page)).toHaveAttribute("aria-current", "page");
  await expect(row(page, machine)).toHaveCount(0);
  await page.goto("/pm?tab=done");
  await expect(row(page, machine)).toContainText("Verified");
});

test("S099: send back needs a remark, and the technician sees it and marks the job done again",
  async ({ page, consoleWatch }, testInfo) => {
    consoleWatch.allowFailedRequest("/send-back", 400);
    const machine = await press(testInfo, "send back");
    const job = await jobFor(machine, "S099 send back plan");
    await doneByApi(job);
    await asPerson(page, "engineer", `/pm/jobs/${job.id}`);
    await page.getByRole("button", { name: "Send back", exact: true }).click();
    await expectDialogFits(page);
    const dialog = await openDialog(page);
    await dialog.locator(".modal-footer button[type=submit]").click();
    await expectFieldMessage(dialog, "Say what must be done again.");
    await dialog.getByLabel("What must be done again?").fill(REWORK);
    await saveDialog(page, "Send back job");
    await expect(page.locator(".badge", { hasText: /^In progress$/ })).toBeVisible();
    await expect(page.getByTestId("pm-sent-back")).toContainText("Sent back by");
    await expect(page.getByTestId("pm-sent-back")).toContainText(REWORK);

    await asPerson(page, "technician", "/me");
    await expect(row(page, machine)).toContainText("Sent back");
    await row(page, machine).click();
    await expect(page.getByTestId("pm-sent-back")).toContainText(REWORK);
    const ok = page.locator(`.pm-item[data-item="${CHECK}"]`).getByRole("button", { name: "OK", exact: true });
    await ok.click();
    await expect(ok).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: "Mark job done" }).click();
    await expectDialogFits(page);
    await saveDialog(page, "Mark job done");
    await expect(page.locator(".badge", { hasText: /^To verify$/ })).toBeVisible();

    await asPerson(page, "engineer", "/pm?tab=to_verify");
    await expect(row(page, machine)).toContainText(job.serial);
    await row(page, machine).click();
    await expect(page.getByRole("button", { name: "Verify job" })).toBeVisible();
    const lines = (await history(page).allTextContents()).map((text) => text.trim())
      .filter((text) => ["Done", "Sent back"].includes(text));
    expect(lines).toEqual(["Done", "Sent back", "Done"]);
  });

test("S099: a job whose plan needs no verification ends at Done", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "final");
  const job = await jobFor(machine, "S099 final plan", { needs_verification: false });
  await doneByApi(job);
  await asPerson(page, "engineer", "/pm?tab=to_verify");
  await expect(toVerifyTab(page)).toHaveAttribute("aria-current", "page");
  await expect(row(page, machine)).toHaveCount(0);
  await page.goto("/pm?tab=done");
  await expect(row(page, machine).locator(".badge", { hasText: /^Done$/ })).toBeVisible();
  await page.goto(`/pm/jobs/${job.id}`);
  await expect(page.getByRole("heading", { name: job.serial })).toBeVisible();
  await expect(page.getByRole("button", { name: "Verify job" })).toHaveCount(0);
});

test("S099: an engineer verifying his own job is recorded", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "self");
  const job = await jobFor(machine, "S099 self plan");
  await doneByApi(job, "engineer", "engineer");
  await asPerson(page, "engineer", `/pm/jobs/${job.id}`);
  await page.getByRole("button", { name: "Verify job" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog).toContainText("You did this job. The record will say you verified your own work.");
  await saveDialog(page, "Verify job");
  await expect(page.getByTestId("pm-verified")).toContainText("the person who did the work");
  await expect(card(page, "History")).toContainText("the person who did the work");
});

test("S099: the technician and IT admin see no Verify job", async ({ page }, testInfo) => {
  const machine = await press(testInfo, "readers");
  const job = await jobFor(machine, "S099 readers plan");
  await doneByApi(job);
  for (const key of ["technician", "it_admin"]) {
    await asPerson(page, key, `/pm/jobs/${job.id}`);
    await expect(page.getByText("Waiting for an engineer to verify.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Verify job" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Send back", exact: true })).toHaveCount(0);
  }
});

test("S099: the four PM tabs fit the phone width on one row", { tag: "@device" }, async ({ page }, testInfo) => {
  // A phone is checked at 360 px, the narrowest the plant uses (BR1-05); the desktop at its own width
  if (testInfo.project.use.isMobile) await page.setViewportSize({ width: 360, height: 780 });
  // The real answer with the count set to two digits ("To verify (12)", the widest label BR1-05 names)
  await page.route(/\/api\/pm\/jobs(\?|$)/, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({ response, json: { ...body, counts: { ...body.counts, to_verify: 12 } } });
  });
  await asPerson(page, "engineer", "/pm");
  const tabs = page.locator(".nav-tabs .nav-link");
  await expect(tabs).toHaveCount(4);
  await expect(tabs.nth(2)).toHaveText("To verify (12)");
  const boxes = await Promise.all([0, 1, 2, 3].map((index) => tabs.nth(index).boundingBox()));
  expect(new Set(boxes.map((box) => Math.round(box.y))).size, "the four tabs are not on one row").toBe(1);
  expect(new Set(boxes.map((box) => Math.round(box.height))).size, "a tab label wraps").toBe(1);
  await expectNoSidewaysScroll(page);
});
