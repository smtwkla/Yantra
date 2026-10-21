// Working the ticket (S018) — in place of its manual checks.  Each test raises its own ticket
// through the API (setup), then works it on the screens; every dialog opened must fit
// (openAction calls expectDialogFits).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage } from "./support/dialogs.js";
import { asPerson, personId, seedIds } from "./support/people.js";
import {
  card, istLocal, moveByApi, openAction, raiseByApi, saveDialog, setEventTime, shownTime, stateBadge, thisMinute,
  timeline, timeValue,
} from "./support/tickets.js";

let seed;
let kannan; // the technician's Team record

test.beforeAll(async () => {
  seed = await seedIds();
  kannan = await personId("technician");
});

/** A breakdown on the extruder, raised by the operator `minutesAgo` minutes before `base`. */
function raiseBreakdown(base, minutesAgo, description) {
  return raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "critical", description, occurred_at: istLocal(minutesAgo, base),
  });
}

test("technician: acknowledge, start, back in service; the times card shows response, repair and downtime", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseBreakdown(base, 120, "Work test: extruder stopped");
  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  await expect(stateBadge(page)).toHaveText("Raised");

  let dialog = await openAction(page, "Acknowledge");
  await expect(dialog).toContainText("Recording as Kannan (technician)");
  await setEventTime(dialog, istLocal(100, base));
  await saveDialog(page, "Acknowledge");
  await expect(stateBadge(page)).toHaveText("Acknowledged");

  dialog = await openAction(page, "Start work");
  await setEventTime(dialog, istLocal(90, base));
  await saveDialog(page, "Start work");
  await expect(stateBadge(page)).toHaveText("In progress");

  dialog = await openAction(page, "Back in service");
  // Who did the work: pre-filled with his own person
  await expect(dialog.locator(".fw-semibold", { hasText: "Kannan (technician)" })).toBeVisible();
  await setEventTime(dialog, istLocal(30, base));
  await saveDialog(page, "Back in service");
  await expect(stateBadge(page)).toHaveText("Back in service");

  await expect(timeValue(page, "Response")).toHaveText("20 min");
  await expect(timeValue(page, "Repair (hands on)")).toHaveText("1 h");
  await expect(timeValue(page, "Downtime")).toHaveText("1 h 30 min");
});

test("supervisor: back in service on an acknowledged ticket, the technician found by typing, with a start time", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseBreakdown(base, 120, "Work test: cutter jammed");
  await moveByApi("technician2", ticket.id, "acknowledge", { occurred_at: istLocal(100, base) });
  await asPerson(page, "supervisor", `/tickets/${ticket.id}`);
  await expect(stateBadge(page)).toHaveText("Acknowledged");

  const dialog = await openAction(page, "Back in service");
  await setEventTime(dialog, istLocal(20, base));
  await dialog.getByPlaceholder("Type a name to filter").fill("Kann");
  await dialog.getByRole("button", { name: /Kannan \(technician\)/ }).click();
  await expect(dialog.locator(".fw-semibold", { hasText: "Kannan (technician)" })).toBeVisible();
  const started = istLocal(60, base);
  await dialog.getByLabel("Start date").fill(started.slice(0, 10));
  await dialog.locator("#move-restore-started-time").fill(started.slice(11));
  await saveDialog(page, "Back in service");

  await expect(stateBadge(page)).toHaveText("Back in service");
  const workStarted = timeline(page).filter({ hasText: "Work started" });
  await expect(workStarted).toContainText(shownTime(started));
  const backInService = timeline(page).filter({ hasText: "Back in service" });
  await expect(backInService).toContainText(shownTime(istLocal(20, base)));
  await expect(backInService).toContainText("Kannan (technician)");
});

test("engineer: Close waits for the labour; Add labour, then close with cause and action; the ticket is read-only", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseBreakdown(base, 120, "Work test: motor tripped");
  await moveByApi("technician", ticket.id, "restore", { person_id: kannan, occurred_at: istLocal(30, base) });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);

  await expect(page.getByRole("button", { name: "Close", exact: true })).toBeDisabled();
  await expect(page.getByText("Add the labour first")).toBeVisible();
  // The action buttons come first, above the times, assignees and labour
  const actionsTop = (await page.locator(".action-bar").boundingBox()).y;
  expect(actionsTop).toBeLessThan((await card(page, "Times").boundingBox()).y);
  // Add labour beside the disabled Close (the first of the two Add labour buttons)
  await page.locator(".action-bar").getByRole("button", { name: "Add labour" }).click();
  await expectDialogFits(page);
  const labour = page.locator(".modal.show");
  await expect(labour.locator(".modal-title")).toHaveText("Add labour");
  await expect(labour.locator(".fw-semibold", { hasText: "Priya (engineer)" })).toBeVisible();
  await expect(labour.getByLabel("Date")).toHaveValue(istLocal(0).slice(0, 10));
  await labour.getByLabel("Hours").fill("1");
  await labour.getByLabel("Minutes").fill("15");
  await saveDialog(page, "Save");
  await expect(card(page, "Labour")).toContainText("Priya (engineer)");

  // Remove asks first
  await page.getByTitle("Remove").click();
  await expect(page.getByText("Remove?")).toBeVisible();
  await page.getByRole("button", { name: "No", exact: true }).click();

  const dialog = await openAction(page, "Close");
  await dialog.locator("#move-close-mode").selectOption({ index: 1 });
  await dialog.locator("#move-cause").selectOption({ index: 1 });
  await dialog.locator("#move-action").selectOption({ index: 1 });
  await expect(dialog).toContainText(`${ticket.serial} becomes read-only.`);
  await saveDialog(page, "Close ticket");

  await expect(stateBadge(page)).toHaveText("Closed");
  await expect(timeline(page).filter({ hasText: /^Closed/ })).toHaveCount(1);
  for (const name of ["Close", "Add labour", "Edit", "Assign", "Send back"]) {
    await expect(page.getByRole("button", { name, exact: true })).toHaveCount(0);
  }
});

test("Not fixed — raise again: the new ticket links to the old one, and the old one lists it", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseBreakdown(base, 90, "Work test: came back");
  await moveByApi("technician", ticket.id, "restore", { person_id: kannan, occurred_at: istLocal(30, base) });
  await asPerson(page, "operator", `/tickets/${ticket.id}`);

  await page.getByRole("link", { name: "Not fixed — raise again" }).click();
  await expect(page.getByText(`Repeat of ${ticket.serial}`)).toBeVisible();
  // Pre-filled with the earlier ticket's intensity
  await expect(page.getByRole("button", { name: /Stopped/ })).toHaveAttribute("aria-pressed", "true");
  await page.getByLabel(/What is wrong\?/).fill("Work test: stopped again");
  await page.locator("form button[type=submit]").click();
  const serial = (await page.locator(".alert-success strong").textContent()).trim();
  await page.getByRole("button", { name: "Done" }).click();

  await expect(page.getByRole("heading", { name: serial })).toBeVisible();
  await expect(page.getByText("Repeat of")).toContainText(ticket.serial);
  await page.getByRole("link", { name: ticket.serial }).click();
  await expect(page.getByRole("heading", { name: ticket.serial })).toBeVisible();
  await expect(page.getByText("Came back as")).toContainText(serial);
});

test("send back with the machine down: the remark is required, and downtime runs again", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseBreakdown(base, 120, "Work test: not accepted");
  await moveByApi("technician", ticket.id, "restore", { person_id: kannan, occurred_at: istLocal(100, base) });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  await expect(timeValue(page, "Downtime")).toHaveText("20 min");

  const dialog = await openAction(page, "Send back");
  await dialog.getByRole("button", { name: /Yes — downtime runs again/ }).click();
  await setEventTime(dialog, istLocal(50, base));
  // The remark is open, and Save without it is refused on the field
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expect(dialog.locator("#move-send-back-remark")).toHaveClass(/is-invalid/);
  await expectFieldMessage(dialog, "Add a remark");
  await dialog.locator("#move-send-back-remark").fill("Guard not refitted");
  await saveDialog(page, "Send back");

  await expect(stateBadge(page)).toHaveText("In progress");
  await expect(timeline(page).filter({ hasText: "Sent back" })).toContainText("Guard not refitted");
  // 20 min before the restore, then again from the send back (50 min ago): it grows
  await expect(timeValue(page, "Downtime")).toHaveText(/^1 h 1[01] min$/);
});

test("operator: Machine stopped on a defect starts the downtime at that time", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "Work test: running slow",
    occurred_at: istLocal(60, base),
  });
  await asPerson(page, "operator", `/tickets/${ticket.id}`);
  await page.getByRole("button", { name: "Machine stopped" }).click();
  await expectDialogFits(page);
  await setEventTime(page.locator(".modal.show"), istLocal(30, base));
  await saveDialog(page, "Machine stopped");

  await expect(page.getByText("Breakdown", { exact: true }).first()).toBeVisible();
  await expect(timeline(page).filter({ hasText: "Severity changed" })).toContainText("Defect → Breakdown");
  await expect(timeValue(page, "Downtime")).toHaveText(/^3[01] min$/);
});

test("not a fault: the remark is open and required; the ticket closes as not a fault", async ({ page }) => {
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "initial", description: "Work test: strange smell",
  });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  const dialog = await openAction(page, "Not a fault");
  // 5.1 No cause found is suggested
  await expect(dialog.locator("#move-cause option:checked")).toHaveText(/^5\.1 /);
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Add a remark");
  await dialog.locator("#move-not-a-fault-remark").fill("Smell from the next line's dryer");
  await saveDialog(page, "Close as not a fault");
  await expect(stateBadge(page)).toHaveText("Closed");
  await expect(page.getByText("Not a fault", { exact: true }).first()).toBeVisible();
});

test("engineer: assign, edit and change severity; IT admin with no Team record acknowledges as nobody", async ({ page }) => {
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "Work test: to assign",
  });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);

  await page.getByRole("button", { name: "Assign" }).click();
  await expectDialogFits(page);
  await page.locator(".modal.show").getByRole("button", { name: /Ravi \(technician\)/ }).click();
  await saveDialog(page, "Assign");
  await expect(card(page, "Assigned")).toContainText("Ravi (technician)");

  await page.getByRole("button", { name: "Edit" }).click();
  await expectDialogFits(page);
  await page.locator("#edit-description").fill("Work test: to assign, gearbox side");
  await saveDialog(page, "Save");
  await expect(card(page, "Description")).toContainText("Work test: to assign, gearbox side");

  const regrade = await openAction(page, "Change severity");
  await regrade.getByRole("button", { name: /Early signs/ }).click();
  await regrade.locator("#regrade-remark").fill("Only a small leak");
  await saveDialog(page, "Save");
  await expect(timeline(page).filter({ hasText: "Severity changed" })).toContainText("Defect → Defect · initial");

  await asPerson(page, "it_admin", `/tickets/${ticket.id}`);
  const dialog = await openAction(page, "Acknowledge");
  await expect(dialog).toContainText("Nobody will be assigned.");
});
