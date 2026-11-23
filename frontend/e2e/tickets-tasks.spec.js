// Tasks on a ticket: the screens (S107 § 8.1; the record and the API are S106's).  Each test raises
// its own ticket on the seed's extruder through the API (setup) and finds its tasks by data-task or
// by text, never by position or a count: other specs in the lane add tickets and tasks too (S100).
// Every dialog a test opens must fit (expectDialogFits).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { raiseFixed, TEST_PHOTO } from "./support/improvements.js";
import { apiAs, asPerson, personId, seedIds } from "./support/people.js";
import {
  actionId, cancelOpenTasksByApi, card, causeId, istDay, istLocal, markTaskDoneByApi, openAction, raiseByApi, saveDialog,
  shownDay, stateBadge, taskByApi, timeline,
} from "./support/tickets.js";

let seed;
let kannan; // the technician's Team record
let raised = []; // this test's tickets, closed after it

test.beforeAll(async () => {
  seed = await seedIds();
  kannan = await personId("technician");
});

/**
 * Close what the test left open, as admin through the API (as tickets-parts.spec.js): its open
 * tasks cancelled first (S106: an open task blocks both closes), then a ticket back in service is
 * closed, any other closed as not a fault.  The raise screen lists at most 50 open tickets of a
 * machine, so these tickets must not pile up on the extruder.
 */
test.afterEach(async () => {
  const api = await apiAs("admin");
  try {
    for (const id of raised) {
      const ticket = await (await api.get(`/api/tickets/${id}`)).json();
      if (ticket.state === "closed") continue;
      await cancelOpenTasksByApi(id);
      let body = { cause_id: await causeId("5.1"), remark: "S107 test: tidy-up" };
      let move = "not-a-fault";
      if (ticket.state === "back_in_service") {
        const modes = (await (await api.get(`/api/tickets/modes?ticket_id=${id}`)).json()).items;
        body = { cause_id: await causeId("3.4"), action_id: await actionId("1"), failure_mode_id: modes[0].id };
        move = "close";
      }
      const res = await api.post(`/api/tickets/${id}/moves/${move}`, { data: body });
      expect(res.status(), await res.text()).toBe(200);
    }
  } finally {
    raised = [];
    await api.dispose();
  }
});

/** A labour row of 30 minutes by the technician, with his trade (setup: Close needs labour). */
async function labourByApi(ticketId) {
  const api = await apiAs("technician");
  try {
    const people = (await (await api.get(`/api/tickets/people?ticket_id=${ticketId}`)).json()).items;
    const trade = people.find((p) => p.id === kannan).trades[0]?.id ?? null;
    const res = await api.post(`/api/tickets/${ticketId}/labour`, {
      data: { person_id: kannan, trade_id: trade, work_date: istDay(0), minutes: 30 },
    });
    expect(res.status(), await res.text()).toBe(201);
  } finally {
    await api.dispose();
  }
}

/**
 * A defect on the extruder that is back in service (as TK-2026-11-008), with its labour: only the
 * tasks can hold Close back.  It offers Close, never Not a fault (tickets_core.MOVES).
 */
async function fixedTicket(description) {
  const ticket = await raiseFixed(seed.extruder.id, description);
  raised.push(ticket.id);
  await labourByApi(ticket.id);
  return ticket;
}

/** A defect on the extruder raised by the operator, state Raised: it offers Not a fault, never Close. */
async function raisedDefect(description, extra = {}) {
  const ticket = await raiseByApi("operator", { equipment_id: seed.extruder.id, intensity: "degraded", description, ...extra });
  raised.push(ticket.id);
  return ticket;
}

const tasksCard = (page) => page.getByTestId("tasks");
const tasksTitle = (page) => page.getByTestId("tasks-title");
const taskRow = (page, taskId) => page.locator(`li[data-task="${taskId}"]`);
const taskRowByText = (page, text) => tasksCard(page).locator("li[data-task]").filter({ hasText: text });

/** Open *Add task* from the card, fill it and add it: the dialog must fit. */
async function addTask(page, { text, owner, pick }) {
  await tasksCard(page).getByRole("button", { name: "Add task", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.locator(".modal-title")).toHaveText("Add task");
  await dialog.getByLabel("What to do").fill(text);
  await dialog.locator(".picker-list button", { hasText: owner }).click();
  await dialog.getByRole("button", { name: pick, exact: true }).click();
  await saveDialog(page, "Add task");
}

/** Fill *Mark task done* (opened by the row's button) and save it, with the test photo when `photo`. */
async function markDone(page, row, doneText, { photo = false } = {}) {
  await row.getByRole("button", { name: "Mark done", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.locator(".modal-title")).toHaveText("Mark task done");
  await expect(dialog.getByText("The photos go to the ticket's photos.")).toBeVisible();
  await dialog.getByLabel("What did you do?").fill(doneText);
  if (photo) {
    await dialog.locator("input[type=file]").setInputFiles(TEST_PHOTO);
    await expect(dialog.locator('li[data-photo="test-photo.jpg"]')).toBeVisible();
  }
  await saveDialog(page, "Mark done");
}

const HEATER = "Check the space heater circuit diagram and find any fuse";
const SUPPLIER = "Get the VCB supplier to inspect the panel";

test("S107: the TK-2026-11-008 flow: two tasks, the technician marks his done from Me with a photo, Close waits for the other, then the ticket closes", async ({ page }) => {
  const ticket = await fixedTicket("S107 flow: HT cable termination on the VCB failed");
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  await expect(tasksCard(page)).toContainText("No tasks yet.");

  await addTask(page, { text: HEATER, owner: "Kannan (technician)", pick: "Tomorrow" });
  const heater = taskRowByText(page, HEATER);
  await expect(heater).toContainText("Owner: Kannan (technician)");
  await expect(heater).toContainText(`due ${shownDay(istDay(1))}`);
  await expect(heater.locator(".badge")).toHaveText("Open");
  await expect(tasksTitle(page)).toHaveText("Tasks (0 of 1 done)");
  const heaterId = await heater.getAttribute("data-task");

  await addTask(page, { text: SUPPLIER, owner: "Priya (engineer)", pick: "In 7 days" });
  await expect(taskRowByText(page, SUPPLIER)).toContainText(`due ${shownDay(istDay(7))}`);
  await expect(tasksTitle(page)).toHaveText("Tasks (0 of 2 done)");
  // In the action bar: a dialog fading out still holds its own "Close" (the X)
  const close = page.locator(".action-bar").getByRole("button", { name: "Close", exact: true });
  await expect(close).toBeDisabled();
  await expect(page.getByText("This ticket has 2 open tasks. Mark them done or cancel them first.")).toBeVisible();
  await expect(timeline(page).filter({ hasText: "Task added" })).toHaveCount(2);

  // The technician, on his phone: Me › Open work
  await asPerson(page, "technician", "/me");
  await expect(page.getByTestId("me-tasks")).toHaveText(/^Tasks \(\d+\)$/);
  const mine = taskRow(page, heaterId);
  await expect(mine).toContainText(ticket.serial);
  await markDone(page, mine, "Fuse F3 was blown. Fitted a new one.", { photo: true });
  await expect(mine).toHaveCount(0);

  // The engineer again
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  await expect(heater.locator(".badge")).toHaveText("Done");
  await expect(heater).toContainText("Fuse F3 was blown. Fitted a new one.");
  await expect(tasksTitle(page)).toHaveText("Tasks (1 of 2 done)");
  await expect(card(page, "Photos").locator('.photo-tile[title="test-photo"]')).toHaveCount(1);
  await expect(close).toBeDisabled();
  await expect(page.getByText("This ticket has 1 open task. Mark it done or cancel it first.")).toBeVisible();
  const doneLine = timeline(page).filter({ hasText: "Task done" });
  await expect(doneLine).toContainText(`Task: ${HEATER}`);
  await expect(doneLine).toContainText("Fuse F3 was blown. Fitted a new one.");

  // A photo sent from the ticket page itself shows in the Photos card with no navigation (CR1-01)
  await markDone(page, taskRowByText(page, SUPPLIER), "The supplier inspected the panel. No more damage.", { photo: true });
  await expect(tasksTitle(page)).toHaveText("Tasks (2 of 2 done)");
  await expect(card(page, "Photos").locator('.photo-tile[title="test-photo"]')).toHaveCount(2);
  await expect(close).toBeEnabled();
  const dialog = await openAction(page, "Close");
  await dialog.locator("#move-close-mode").selectOption({ index: 1 });
  await dialog.locator("#move-cause").selectOption({ index: 1 });
  await dialog.locator("#move-action").selectOption({ index: 1 });
  await saveDialog(page, "Close ticket");
  await expect(stateBadge(page)).toHaveText("Closed");
  await expect(tasksCard(page).locator("li[data-task] button")).toHaveCount(0);
  await expect(tasksCard(page).getByRole("button", { name: "Add task" })).toHaveCount(0);
});

test("S107: change and cancel a task; Not a fault waits for the open task", async ({ page }) => {
  const ticket = await raisedDefect("S107 change: panel heater");
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  const text = "S107 change: read the panel's heater fuse";
  await addTask(page, { text, owner: "Ramesh (operator, no phone)", pick: "Tomorrow" });
  const row = taskRowByText(page, text);
  await expect(row.getByTestId("owner-mark")).toHaveText("No login: mark it done for them.");
  const notAFault = page.locator(".action-bar").getByRole("button", { name: "Not a fault", exact: true });
  await expect(notAFault).toBeDisabled();
  await expect(page.getByText("This ticket has 1 open task. Mark it done or cancel it first.")).toBeVisible();

  await page.getByRole("button", { name: "Change task 1", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.locator(".modal-title")).toHaveText("Change task");
  await dialog.locator(".picker-list button", { hasText: "Ravi (technician)" }).click();
  await dialog.getByRole("button", { name: "In 7 days", exact: true }).click();
  await saveDialog(page, "Save task");
  await expect(row).toContainText("Owner: Ravi (technician)");
  await expect(row).toContainText(`due ${shownDay(istDay(7))}`);
  await expect(row.getByTestId("owner-mark")).toHaveCount(0);
  await expect(timeline(page).filter({ hasText: "Task changed" }))
    .toContainText("Owner: Ramesh (operator, no phone) → Ravi (technician)");

  await page.getByRole("button", { name: "Cancel task 1", exact: true }).click();
  await row.getByLabel("Why cancel it?").fill("Moved to the improvement as a countermeasure");
  await row.getByRole("button", { name: "Cancel task", exact: true }).click();
  await expect(row.locator(".badge")).toHaveText("Cancelled");
  await expect(row).toContainText("Moved to the improvement as a countermeasure");
  await expect(tasksTitle(page)).toHaveText("Tasks");
  await expect(timeline(page).filter({ hasText: "Task cancelled" }))
    .toContainText("Moved to the improvement as a countermeasure");
  await expect(notAFault).toBeEnabled();
  await expect(page.getByText(/open tasks?\. Mark/)).toHaveCount(0);
});

test("S107: the owner marks: no access, recorded by; a reader who cannot change the task sees none", async ({ page }) => {
  const ticket = await raisedDefect("S107 marks: owners who cannot act");
  const devi = "S107 marks: count the spare fuses in the store";
  await taskByApi(ticket.id, { owner: "Devi (storekeeper)", text: devi });
  const { task: rameshTask } = await taskByApi(ticket.id, { owner: "Ramesh (operator, no phone)", text: "S107 marks: tighten the gland" });
  await markTaskDoneByApi(ticket.id, rameshTask.id, "engineer", "Gland tightened.");

  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  await expect(taskRowByText(page, devi).getByTestId("owner-mark"))
    .toHaveText("May not see this ticket. Mark it done for them, or choose another owner.");
  const done = taskRow(page, rameshTask.id);
  await expect(done).toContainText("recorded by Priya (engineer)");
  await expect(done.getByTestId("owner-mark")).toHaveCount(0);

  await asPerson(page, "operator", `/tickets/${ticket.id}`);
  await expect(taskRowByText(page, devi)).toBeVisible();
  await expect(taskRowByText(page, devi).getByTestId("owner-mark")).toHaveCount(0);
});

test("S107: who sees which buttons: the owner marks done, another technician and the operator only read", async ({ page }) => {
  const ticket = await raisedDefect("S107 buttons: who may act");
  const { task } = await taskByApi(ticket.id, { owner: "Kannan (technician)", text: "S107 buttons: check the heater" });

  await asPerson(page, "technician2", `/tickets/${ticket.id}`);
  const row = taskRow(page, task.id);
  await expect(row).toContainText("S107 buttons: check the heater");
  await expect(row.getByRole("button")).toHaveCount(0);
  await expect(tasksCard(page).getByRole("button", { name: "Add task" })).toHaveCount(0);

  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  await expect(row.getByRole("button", { name: "Mark done", exact: true })).toBeVisible();
  await expect(row.getByRole("button", { name: "Change task 1" })).toHaveCount(0);
  await expect(row.getByRole("button", { name: "Cancel task 1" })).toHaveCount(0);

  await asPerson(page, "operator", `/tickets/${ticket.id}`);
  await expect(row).toBeVisible();
  await expect(tasksCard(page).getByRole("button")).toHaveCount(0);
});

test("S107: Add task refuses in field order: what to do first, then the due date", async ({ page, consoleWatch }) => {
  const ticket = await raisedDefect("S107 refusals: field order");
  consoleWatch.allowFailedRequest(`/api/tickets/${ticket.id}/tasks`, 400);
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  await tasksCard(page).getByRole("button", { name: "Add task", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  const save = dialog.locator(".modal-footer button[type=submit]");
  await save.click();
  await expectFieldMessage(dialog, "Enter what to do");

  await dialog.getByLabel("What to do").fill("S107 refusals: check the fuse");
  await dialog.locator(".picker-list button", { hasText: "Kannan (technician)" }).click();
  await save.click();
  await expectFieldMessage(dialog, "Choose the due date");
  await expect(dialog.getByText("Enter what to do")).toHaveCount(0);
});

test("S107: an overdue task shows Overdue 2 days in red", async ({ page }) => {
  const ticket = await raisedDefect("S107 overdue: three days old", { occurred_at: istLocal(3 * 24 * 60) });
  const { task } = await taskByApi(ticket.id, { text: "S107 overdue: check the heater", due: istDay(-2) });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  const badge = taskRow(page, task.id).locator(".badge");
  await expect(badge).toHaveText("Overdue 2 days");
  await expect(badge).toHaveClass(/text-bg-danger/);
});

test("S107: a cancel refused because the owner marked the task done meanwhile shows the row done, with no ask left", async ({ page, consoleWatch }) => {
  const ticket = await raisedDefect("S107 stale cancel: done meanwhile");
  const { task } = await taskByApi(ticket.id, { text: "S107 stale cancel: check the heater" });
  consoleWatch.allowFailedRequest(`/api/tickets/${ticket.id}/tasks/${task.id}/cancel`, 409);
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  const row = taskRow(page, task.id);
  await page.getByRole("button", { name: "Cancel task 1", exact: true }).click();
  await row.getByLabel("Why cancel it?").fill("Not needed");
  await markTaskDoneByApi(ticket.id, task.id, "technician"); // the owner, on another phone
  await row.getByRole("button", { name: "Cancel task", exact: true }).click();

  await expect(row.locator(".badge")).toHaveText("Done");
  await expect(row).not.toContainText("Cancel this task?");
  await expect(row.getByLabel("Why cancel it?")).toHaveCount(0);
});

test("S107: the ticket page with the Tasks card has no sideways scroll", { tag: "@device" }, async ({ page }) => {
  const ticket = await raisedDefect("S107 layout: a long task");
  await taskByApi(ticket.id, { text: "x".repeat(300) });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  const row = tasksCard(page).locator("li[data-task]").first();
  await expect(row.getByRole("button", { name: "Mark done", exact: true })).toBeVisible();
  await expect(row.getByRole("button", { name: "Change task 1", exact: true })).toBeVisible();
  await expect(row.getByRole("button", { name: "Cancel task 1", exact: true })).toBeVisible();
  await expectNoSidewaysScroll(page);
  await row.getByRole("button", { name: "Cancel task 1", exact: true }).click();
  await expect(row.getByLabel("Why cancel it?")).toBeVisible();
  await expectNoSidewaysScroll(page);
});
