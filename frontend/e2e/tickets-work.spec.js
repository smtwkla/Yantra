// Working the ticket (S018) — in place of its manual checks.  Each test raises its own ticket
// through the API (setup), then works it on the screens; every dialog opened must fit
// (openAction calls expectDialogFits).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, openDialog } from "./support/dialogs.js";
import { apiAs, asPerson, personId, seedIds } from "./support/people.js";
import {
  card, causeId, istDay, istLocal, moveByApi, openAction, raiseByApi, regradeByApi, saveDialog, setEventTime, shownDay, shownTime,
  stateBadge, thisMinute, timeline, timeValue,
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
  const labour = await openDialog(page);
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

test("S026: Add labour with no time spent scrolls the dialog to the message and puts the cursor in the hours field", { tag: "@device" }, async ({ page }, testInfo) => {
  const base = thisMinute();
  // Not on the extruder: the raise tests read its open-tickets list, which the API cuts at 50
  const ticket = await raiseByApi("supervisor", {
    equipment_id: seed.mcc1Mill.id, intensity: "critical", description: "Work test: labour refusal in view",
    occurred_at: istLocal(120, base),
  });
  await moveByApi("technician", ticket.id, "restore", { person_id: kannan, occurred_at: istLocal(30, base) });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);

  await page.locator(".action-bar").getByRole("button", { name: "Add labour" }).click();
  await expectDialogFits(page);
  const labour = await openDialog(page);
  // Click a name in the picker: Kannan has one trade, so Trade worked is filled and not refused first
  await labour.getByRole("button", { name: /Kannan \(technician\)/ }).click();
  await expect(labour.locator(".fw-semibold", { hasText: "Kannan (technician)" })).toBeVisible();
  const hours = labour.getByLabel("Hours");
  // The bug: on the iPhone 14 screen Time spent starts below the fold, so Save looked dead
  if (testInfo.project.name === "phone-webkit") await expect(hours).not.toBeInViewport();

  await labour.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(labour, "Time spent must be between 1 minute and 24 hours");
  await expect(hours).toBeFocused();
  await expect(hours).toBeInViewport();

  await hours.fill("1");
  await labour.getByLabel("Minutes").fill("15");
  await saveDialog(page, "Save");
  await expect(card(page, "Labour")).toContainText("Kannan (technician)");
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
  await setEventTime(await openDialog(page), istLocal(30, base));
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
  await (await openDialog(page)).getByRole("button", { name: /Ravi \(technician\)/ }).click();
  await saveDialog(page, "Assign");
  await expect(card(page, "Assigned")).toContainText("Ravi (technician)");

  await page.getByRole("button", { name: "Edit" }).click();
  await expectDialogFits(page);
  await page.locator("#edit-description").fill("Work test: to assign, gearbox side");
  await saveDialog(page, "Save");
  // S027: the description is the first note, on the timeline's Raised line
  await expect(timeline(page).last()).toContainText("Work test: to assign, gearbox side");

  const regrade = await openAction(page, "Change severity");
  await regrade.getByRole("button", { name: /Early signs/ }).click();
  await regrade.locator("#regrade-remark").fill("Only a small leak");
  await saveDialog(page, "Save");
  await expect(timeline(page).filter({ hasText: "Severity changed" })).toContainText("Defect → Defect · initial");

  await asPerson(page, "it_admin", `/tickets/${ticket.id}`);
  const dialog = await openAction(page, "Acknowledge");
  await expect(dialog).toContainText("Nobody will be assigned.");
});

// S025 (audit fixes) ------------------------------------------------------------------------

test("S025: Machine stopped, when someone else made it a breakdown first, shows why and reloads the ticket", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/regrade", 400);
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "S025 test: running slow",
  });
  await asPerson(page, "operator", `/tickets/${ticket.id}`);
  await page.getByRole("button", { name: "Machine stopped" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  // Meanwhile another operator taps Machine stopped first
  await regradeByApi("operator", ticket.id, { intensity: "critical" });
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Already a breakdown");
  await expect(dialog).toBeVisible();
  // The page behind was reloaded: it shows the breakdown the other operator recorded
  await expect(timeline(page).filter({ hasText: "Severity changed" })).toContainText("Defect → Breakdown");
});

test("S025: a ticket that came back as a repeat offers no Send back; Close stays", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseBreakdown(base, 90, "S025 test: came back");
  await moveByApi("technician", ticket.id, "restore", { person_id: kannan, occurred_at: istLocal(30, base) });
  const repeat = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "critical", description: "S025 test: stopped again",
    repeat_of_id: ticket.id,
  });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  await expect(page.getByText("Came back as")).toContainText(repeat.serial);
  await expect(page.getByRole("button", { name: "Close", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Send back", exact: true })).toHaveCount(0);
});

test("S025: Start, then Not a fault: the ticket closes as not a fault and shows no times", async ({ page }) => {
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "initial", description: "S025 test: looked, nothing wrong",
  });
  await moveByApi("technician", ticket.id, "start");
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  await expect(stateBadge(page)).toHaveText("In progress");
  const dialog = await openAction(page, "Not a fault");
  await dialog.locator("#move-not-a-fault-remark").fill("Nothing wrong found on arrival");
  await saveDialog(page, "Close as not a fault");
  await expect(stateBadge(page)).toHaveText("Closed");
  await expect(page.getByText("Not a fault", { exact: true }).first()).toBeVisible();
  // Out of MTBF and MTTR, as any not-a-fault ticket: no Times card
  await expect(card(page, "Times")).toHaveCount(0);
});

// S019 (deferred work) --------------------------------------------------------------------

const SLOT = "waiting for a production slot or shutdown";

test("S019: engineer schedules a defect for a date and reason, then changes the plan with a remark", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/moves/reschedule", 400);
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "S019 test: scraper worn",
  });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);

  let dialog = await openAction(page, "Defer");
  // The date opens empty: the engineer must choose one
  await expect(dialog.locator("#move-schedule-date")).toHaveValue("");
  // Other opens the remark, required
  await dialog.locator("#move-schedule-reason").selectOption("other");
  await expect(dialog.getByLabel("What does it wait for?")).toBeVisible();
  const planned = istDay(3);
  await dialog.locator("#move-schedule-date").fill(planned);
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Add a remark");
  await dialog.locator("#move-schedule-reason").selectOption("slot");
  await saveDialog(page, "Defer");

  await expect(stateBadge(page)).toHaveText("Deferred");
  await expect(page.locator(".plan-line")).toHaveText(`for ${shownDay(planned)} · ${SLOT}`);
  await expect(timeline(page).filter({ hasText: /^\s*On hold/ })).toContainText(`for ${shownDay(planned)} · ${SLOT}`);

  dialog = await openAction(page, "Change plan");
  // Opens with the current plan, the remark open and required
  await expect(dialog.locator("#move-reschedule-date")).toHaveValue(planned);
  await expect(dialog.locator("#move-reschedule-reason")).toHaveValue("slot");
  await dialog.getByLabel("Why did the plan change?").fill("Asked again");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Nothing to change");
  const later = istDay(10);
  await dialog.locator("#move-reschedule-date").fill(later);
  await dialog.getByLabel("Why did the plan change?").fill("Shutdown moved");
  await saveDialog(page, "Change plan");

  await expect(page.locator(".plan-line")).toHaveText(`for ${shownDay(later)} · ${SLOT}`);
  const changed = timeline(page).filter({ hasText: "Plan changed" });
  await expect(changed).toContainText(`for ${shownDay(later)} · ${SLOT} (was ${shownDay(planned)} · ${SLOT})`);
  await expect(changed).toContainText("Shutdown moved");
});

test("S019: technician starts a scheduled defect with the machine stopped; the times card shows the planned stop", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "S019 test: liner change",
    occurred_at: istLocal(120, base),
  });
  await moveByApi("engineer", ticket.id, "schedule", {
    planned_date: istDay(0), waiting_reason: "slot", occurred_at: istLocal(110, base),
  });
  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  await expect(stateBadge(page)).toHaveText("Deferred");
  // Change plan is the engineer's
  await expect(page.getByRole("button", { name: "Change plan" })).toHaveCount(0);

  let dialog = await openAction(page, "Start work");
  await expect(dialog.getByText("Is the machine stopped for this work?")).toBeVisible();
  await setEventTime(dialog, istLocal(90, base));
  await dialog.getByRole("button", { name: "Yes, machine stopped" }).click();
  await saveDialog(page, "Start work");
  await expect(stateBadge(page)).toHaveText("In progress");
  await expect(page.locator(".plan-line")).toHaveCount(0);
  await expect(timeline(page).filter({ hasText: "Work started" })).toContainText("Machine stopped for this work");

  dialog = await openAction(page, "Fixed");
  await setEventTime(dialog, istLocal(30, base));
  await saveDialog(page, "Fixed");
  await expect(timeValue(page, "Planned stop")).toHaveText("1 h");
  await expect(timeValue(page, "Downtime")).toHaveText("0 min");
});

test("S019: technician schedules a breakdown in progress for parts; the times card splits the waiting", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseBreakdown(base, 180, "S019 test: cylinder at the maker");
  await moveByApi("technician", ticket.id, "start", { occurred_at: istLocal(170, base) });
  await asPerson(page, "technician", `/tickets/${ticket.id}`);

  // U1: work stops, waiting for parts — the technician records it from in progress
  let dialog = await openAction(page, "Put on hold");
  const expected = istDay(2);
  await dialog.locator("#move-schedule-date").fill(expected);
  await dialog.locator("#move-schedule-reason").selectOption("parts");
  await setEventTime(dialog, istLocal(150, base));
  await saveDialog(page, "Put on hold");
  await expect(stateBadge(page)).toHaveText("Waiting");
  await expect(page.locator(".plan-line")).toHaveText(`check by ${shownDay(expected)} · waiting for parts`);

  // On a breakdown the stopped question is not asked: the machine is already down
  dialog = await openAction(page, "Start work");
  await expect(dialog.getByText("Is the machine stopped for this work?")).toHaveCount(0);
  await setEventTime(dialog, istLocal(90, base));
  await saveDialog(page, "Start work");
  dialog = await openAction(page, "Back in service");
  await setEventTime(dialog, istLocal(60, base));
  await saveDialog(page, "Back in service");

  await expect(timeValue(page, "Downtime")).toHaveText("2 h");
  await expect(timeValue(page, "Repair (hands on)")).toHaveText("50 min");
  await expect(timeValue(page, "of which waiting")).toHaveText("1 h");
  await expect(timeValue(page, "Waiting for parts")).toHaveText("1 h");
  await expect(timeValue(page, "Logistic delay")).toHaveText("1 h");
});

test("S019: the Overdue filter shows a ticket planned in the past, with the red badge", async ({ page }) => {
  // The seed wrote "yesterday" when the e2e database was built; a run after midnight sees an older
  // day.  Expect the date the API holds, not a date computed now (S045).
  const api = await apiAs("engineer");
  let planned;
  try {
    const res = await api.get("/api/tickets", { params: { state: "overdue", q: "E2E seed: overdue for parts" } });
    expect(res.ok(), await res.text()).toBe(true);
    const found = (await res.json()).items.filter((t) => t.description === "E2E seed: overdue for parts");
    expect(found).toHaveLength(1);
    planned = found[0].planned_date;
  } finally {
    await api.dispose();
  }
  expect(planned < istDay(0), `the seeded ticket is planned in the past (${planned})`).toBe(true); // ISO dates compare as text
  await asPerson(page, "engineer", "/tickets");
  await page.getByLabel("State").selectOption("overdue");
  await expect(page).toHaveURL(/state=overdue/);
  const row = page.locator(".list-group-item").filter({ hasText: "E2E seed: overdue for parts" });
  await expect(row).toHaveCount(1);
  const badge = row.locator(".badge.text-bg-danger");
  await expect(badge).toHaveText(`Overdue since ${shownDay(planned).slice(0, 5)}`);
  await expect(row).toContainText(`Overdue · check by ${shownDay(planned)} · waiting for parts`);
});

test("S019: a technician gets no Defer button on an acknowledged ticket", async ({ page }) => {
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "S019 test: not yet started",
  });
  await moveByApi("technician", ticket.id, "acknowledge");
  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  await expect(stateBadge(page)).toHaveText("Acknowledged");
  await expect(page.getByRole("button", { name: "Start work" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Defer" })).toHaveCount(0);
});

// S034 (defer, hold and follow-up date) ---------------------------------------------------

test("S034: a defect reads Defer; the badge reads Deferred and the timeline On hold; the engineer sees Defer too", async ({ page }) => {
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "S034 test: guard loose",
  });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  await expect(page.getByRole("button", { name: "Defer" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Schedule" })).toHaveCount(0);
  const dialog = await openAction(page, "Defer");
  await dialog.locator("#move-schedule-reason").selectOption("slot");
  await dialog.locator("#move-schedule-date").fill(istDay(4));
  await saveDialog(page, "Defer");
  await expect(stateBadge(page)).toHaveText("Deferred");
  await expect(timeline(page).filter({ hasText: /^\s*On hold/ })).toHaveCount(1);
});

test("S034: a breakdown reads Put on hold; waiting for parts asks Check again by, with help, and the header says check by", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseBreakdown(base, 60, "S034 test: gearbox oil seal");
  await moveByApi("technician", ticket.id, "start", { occurred_at: istLocal(50, base) });
  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  const dialog = await openAction(page, "Put on hold");
  await expect(dialog.locator("label[for=move-schedule-date]")).toHaveText("Date");
  await dialog.locator("#move-schedule-reason").selectOption("parts");
  await expect(dialog.locator("label[for=move-schedule-date]")).toHaveText("Check again by");
  await expect(dialog.getByText("When should someone follow this up? If the supplier gave a date, use it.")).toBeVisible();
  const picked = istDay(5);
  await dialog.locator("#move-schedule-date").fill(picked);
  await setEventTime(dialog, istLocal(40, base));
  await saveDialog(page, "Put on hold");
  await expect(stateBadge(page)).toHaveText("Waiting");
  await expect(page.locator(".plan-line")).toHaveText(`check by ${shownDay(picked)} · waiting for parts`);
});

test("S034: a production slot labels the date Planned for, without the help; the reason is above the date", { tag: "@device" }, async ({ page }) => {
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "S034 test: slot label",
  });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  const dialog = await openAction(page, "Defer");
  await dialog.locator("#move-schedule-reason").selectOption("slot");
  await expect(dialog.locator("label[for=move-schedule-date]")).toHaveText("Planned for");
  await expect(dialog.getByText("When should someone follow this up?")).toHaveCount(0);
  const reasonBox = await dialog.locator("#move-schedule-reason").boundingBox();
  const dateBox = await dialog.locator("#move-schedule-date").boundingBox();
  expect(reasonBox.y).toBeLessThan(dateBox.y);
});

test("S034: In 14 days fills the date (the input's min plus 14 days) and the save succeeds; the list filter reads Deferred / Waiting", async ({ page }) => {
  const ticket = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "S034 test: quick pick",
  });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  const dialog = await openAction(page, "Defer");
  await dialog.locator("#move-schedule-reason").selectOption("vendor");
  // Empty until a pick: the date is still a choice
  await expect(dialog.locator("#move-schedule-date")).toHaveValue("");
  const min = await dialog.locator("#move-schedule-date").getAttribute("min");
  const [y, m, d] = min.split("-").map(Number);
  const expected = new Date(y, m - 1, d + 14);
  const pad = (n) => String(n).padStart(2, "0");
  const expectedValue = `${expected.getFullYear()}-${pad(expected.getMonth() + 1)}-${pad(expected.getDate())}`;
  await dialog.getByRole("button", { name: "In 14 days" }).click();
  await expect(dialog.locator("#move-schedule-date")).toHaveValue(expectedValue);
  await saveDialog(page, "Defer");
  await expect(stateBadge(page)).toHaveText("Deferred");

  // q keeps other tests' tickets off the page; the row is found by serial, which is unique
  // (a second project's run leaves another deferred "S034 test: quick pick" ticket)
  await page.goto("/tickets?q=S034 test: quick pick");
  const filter = page.getByLabel("State");
  await expect(filter.locator("option", { hasText: "Deferred / Waiting" })).toHaveCount(1);
  await filter.selectOption("scheduled");
  await expect(page).toHaveURL(/state=scheduled/);
  await expect(page.locator(".list-group-item").filter({ hasText: ticket.serial })).toHaveCount(1);
});

test("S036: open tickets are tinted by intensity (pink, yellow); a closed ticket and its page are plain", async ({ page }) => {
  const breakdown = await raiseBreakdown(thisMinute(), 5, "S036 tint: breakdown");
  const defect = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "S036 tint: defect",
  });
  const closed = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "critical", description: "S036 tint: closed",
  });
  await moveByApi("engineer", closed.id, "not-a-fault", { cause_id: await causeId("5.1"), remark: "S036 test: nothing wrong" });

  await asPerson(page, "engineer", "/tickets?state=all&q=S036 tint");
  // by serial, which is unique; q keeps other tests' tickets (and a second project's run) off the page
  const rowOf = (ticket) => page.locator(".list-group-item").filter({ hasText: ticket.serial });
  await expect(rowOf(breakdown)).toHaveCSS("background-color", "rgb(248, 215, 218)");
  await expect(rowOf(defect)).toHaveCSS("background-color", "rgb(255, 243, 205)");
  await expect(rowOf(closed)).toHaveCSS("background-color", "rgb(255, 255, 255)");

  const titleOf = () => page.getByTestId("ticket-title");
  await page.goto(`/tickets/${breakdown.id}`);
  await expect(titleOf()).toHaveCSS("background-color", "rgb(248, 215, 218)");
  await page.goto(`/tickets/${closed.id}`);
  await expect(stateBadge(page)).toHaveText("Closed");
  await expect(titleOf()).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
});

test("S051: a move dialog shows the time with Now ticked; a back-dated time typed after unticking is saved", async ({ page }) => {
  const base = thisMinute();
  const ticket = await raiseBreakdown(base, 120, "S051 test: extruder stopped");
  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  const dialog = await openAction(page, "Acknowledge");
  await expect(dialog.getByRole("checkbox", { name: "Now", exact: true })).toBeChecked();
  await expect(dialog.locator("input[type=datetime-local]")).toHaveAttribute("readonly", "");
  await expect(dialog.locator("input[type=datetime-local]")).not.toHaveValue("");
  await setEventTime(dialog, istLocal(100, base)); // unticks Now, then types the time
  await expect(dialog.locator("input[type=datetime-local]")).not.toHaveAttribute("readonly", "");
  await saveDialog(page, "Acknowledge");
  await expect(timeline(page).filter({ hasText: "Acknowledged" })).toContainText(shownTime(istLocal(100, base)));
});

