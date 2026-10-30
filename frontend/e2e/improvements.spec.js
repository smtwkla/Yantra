// The improvement screens (S068; the record is S067's) and the analysis on them (S069) — in place of the steps' manual checks.
// Each test makes its own tickets and improvements through the API (setup), then works them on
// the screens. Every dialog opened must fit (expectDialogFits).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { addActionByApi, addTicketByApi, markDoneByApi, raiseFixed, startImprovementByApi, TEST_PHOTO, uploadActionPhotoByApi } from "./support/improvements.js";
import { lessonMachines } from "./support/lessons.js";
import { apiAs, asPerson, personId, seedIds } from "./support/people.js";
import { actionId, causeId, istDay, istLocal, moveByApi, raiseByApi, saveDialog, shownDay } from "./support/tickets.js";

let seed;

test.beforeAll(async () => {
  seed = await seedIds();
});

/** The improvement page's ticket row for `serial`. */
const ticketRow = (page, serial) => page.locator(`li[data-ticket="${serial}"]`);
/** The remove buttons of the improvement page's ticket rows. */
const removeButtons = (page) => page.getByRole("button", { name: /^Remove .* from this improvement$/ });

test("S068: the engineer starts an improvement from a back-in-service ticket and lands on its page", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S068 start: contactor chatters");
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);

  await page.getByRole("button", { name: "Start improvement", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  // Filled from the ticket: the machine and the text; the user leads
  await expect(dialog.getByLabel("Title")).toHaveValue(`${seed.extruder.code}: S068 start: contactor chatters`);
  await expect(dialog.getByLabel("Problem")).toHaveValue("S068 start: contactor chatters");
  await expect(dialog.getByLabel("Lead").locator("option:checked")).toHaveText("Priya (engineer)");
  await saveDialog(page, "Start improvement");

  await expect(page).toHaveURL(/\/tickets\/improvements\/\d+$/);
  await expect(page.getByRole("heading", { name: /^IM-\d{4}-\d{2}-\d{3}$/ })).toBeVisible();
  await expect(page.locator(".state-badge")).toHaveText("Analysing");
  await expect(page.getByTestId("improvement-title")).toHaveText(`${seed.extruder.code}: S068 start: contactor chatters`);
  await expect(page.getByText("lead Priya (engineer)")).toBeVisible();
  await expect(page.getByText("Tickets (1)")).toBeVisible();
  await expect(ticketRow(page, ticket.serial)).toBeVisible();

  // Back on the ticket: the line is there and the button is gone
  // The timeline's "Ticket added" line links the serial too (S073 BR1-01)
  await ticketRow(page, ticket.serial).getByRole("link", { name: ticket.serial }).click();
  await expect(page.getByText(/Analysed in IM-\d{4}-\d{2}-\d{3} · Analysing/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Start improvement", exact: true })).toHaveCount(0);
});

test("S068: the engineer adds a ticket and removes it again; the machine's last ticket stays", async ({ page }) => {
  const first = await raiseFixed(seed.extruder.id, "S068 add: first");
  const second = await raiseFixed(seed.extruder.id, "S068 add: second", { breakdown: true });
  const improvement = await startImprovementByApi(first);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);
  await expect(page.getByText("Tickets (1)")).toBeVisible();
  await expect(page.getByTestId("improvement-loss")).toHaveText("1 ticket, 0 breakdowns · no downtime");
  // The machine's last ticket cannot go
  await expect(removeButtons(page)).toHaveCount(0);

  await page.getByRole("button", { name: "Add ticket", exact: true }).click();
  const dialog = await openDialog(page);
  await expect(dialog.getByRole("radio").first()).toBeVisible();
  await expectDialogFits(page);
  await dialog.locator("label", { hasText: second.serial }).getByRole("radio").check();
  await saveDialog(page, "Add ticket");

  await expect(page.getByText("Tickets (2)")).toBeVisible();
  await expect(page.getByTestId("improvement-loss")).toHaveText("2 tickets, 1 breakdown · down 50 min");
  // Two tickets of the machine: both can go
  await expect(removeButtons(page)).toHaveCount(2);
  await expectNoSidewaysScroll(page);

  await page.getByRole("button", { name: `Remove ${second.serial} from this improvement` }).click();
  await expect(page.getByText(`Remove ${second.serial} from ${improvement.serial}? The ticket stays as it is.`)).toBeVisible();
  await page.getByRole("button", { name: "Remove ticket", exact: true }).click();

  await expect(page.getByText("Tickets (1)")).toBeVisible();
  await expect(ticketRow(page, second.serial)).toHaveCount(0);
  await expect(page.getByTestId("improvement-loss")).toHaveText("1 ticket, 0 breakdowns · no downtime");
  await expect(removeButtons(page)).toHaveCount(0);
});

test("S068: the engineer edits the problem text", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S068 edit: before");
  const improvement = await startImprovementByApi(ticket);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);

  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Problem").fill("S068 edit: the contactor chatters when the motor starts");
  await saveDialog(page, "Save improvement");
  // The page's problem text; the timeline's "Changed" line repeats it (S073)
  await expect(page.locator(".problem-text")).toHaveText("S068 edit: the contactor chatters when the motor starts");
});

test("S068: the Improvements tab lists the improvement, the Unit filter narrows, Closed is empty", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S068 list: tab");
  const improvement = await startImprovementByApi(ticket, { title: "S068 list title" });
  await asPerson(page, "engineer", "/tickets");

  const tabs = page.getByTestId("tickets-tabs");
  await expect(tabs.getByRole("link", { name: "Tickets", exact: true })).toHaveAttribute("aria-current", "page");
  await tabs.getByRole("link", { name: "Improvements", exact: true }).click();
  await expect(tabs.getByRole("link", { name: "Improvements", exact: true })).toHaveAttribute("aria-current", "page");
  await expect(tabs.getByRole("link", { name: "Tickets", exact: true })).not.toHaveAttribute("aria-current", "page");

  const row = page.getByRole("link", { name: new RegExp(improvement.serial) });
  await expect(page.getByRole("combobox", { name: "State" }).locator("option:checked")).toHaveText("Open improvements");
  await expect(row).toContainText("S068 list title");
  await expect(row).toContainText("Analysing");
  await expect(row).toContainText("lead Priya (engineer)");
  await expect(row).toContainText("1 ticket, 0 breakdowns · no downtime");

  await page.getByRole("combobox", { name: "Unit" }).selectOption({ label: "SMTW.MCC1" });
  await expect(row).toHaveCount(0);
  await expect(page.getByText("No improvements match these filters.")).toBeVisible();
  await page.getByRole("combobox", { name: "Unit" }).selectOption({ label: "All units" });
  await expect(row).toBeVisible();

  await page.getByRole("combobox", { name: "State" }).selectOption({ label: "Closed improvements" });
  await expect(page.getByText("No closed improvements yet.")).toBeVisible();

  // The row opens the page
  await page.getByRole("combobox", { name: "State" }).selectOption({ label: "Open improvements" });
  await row.click();
  await expect(page.getByRole("heading", { name: improvement.serial })).toBeVisible();
});

test("S068: the operator sees the improvement but no button to change it", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S068 operator: read only");
  const second = await raiseFixed(seed.extruder.id, "S068 operator: second ticket");
  const improvement = await startImprovementByApi(ticket);
  // Two tickets of the machine: both rows are removable, so the check below is a real one (CR1-01)
  await addTicketByApi(improvement, second);
  await asPerson(page, "operator", `/tickets/improvements/${improvement.id}`);

  await expect(page.getByRole("heading", { name: improvement.serial })).toBeVisible();
  await expect(ticketRow(page, ticket.serial)).toBeVisible();
  await expect(ticketRow(page, second.serial)).toBeVisible();
  await expect(page.getByRole("button", { name: "Edit", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Add ticket", exact: true })).toHaveCount(0);
  await expect(removeButtons(page)).toHaveCount(0);

  await page.goto(`/tickets/${ticket.id}`);
  await expect(page.getByText(`Analysed in ${improvement.serial} · Analysing`)).toBeVisible();
  await expect(page.getByRole("button", { name: "Start improvement", exact: true })).toHaveCount(0);
});

test("S068: a ticket that is in another open improvement is refused beside the list", async ({ page, consoleWatch }) => {
  const first = await raiseFixed(seed.extruder.id, "S068 other: first");
  const other = await raiseFixed(seed.extruder.id, "S068 other: in another improvement");
  const improvement = await startImprovementByApi(first);
  const otherImprovement = await startImprovementByApi(other);
  consoleWatch.allowFailedRequest(`/api/improvements/${improvement.id}/tickets`, 409);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);

  await page.getByRole("button", { name: "Add ticket", exact: true }).click();
  const dialog = await openDialog(page);
  await expect(dialog.getByRole("radio").first()).toBeVisible();
  await expectDialogFits(page);
  await dialog.locator("label", { hasText: other.serial }).getByRole("radio").check();
  await dialog.getByRole("button", { name: "Add ticket", exact: true }).click();
  await expectFieldMessage(dialog, new RegExp(`${other.serial} is already in ${otherImprovement.serial}`));
});

test("S068: the storekeeper typing the list address sees a plain line and no Retry", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/improvements", 403);
  await asPerson(page, "storekeeper", "/tickets/improvements");
  await expect(page.getByText("You can't see improvements.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry" })).toHaveCount(0);
});

// ---------------------------------------------------------------------------------------------
// S069: the why-why chain and the root cause
// ---------------------------------------------------------------------------------------------

/**
 * Close a back-in-service `ticket` through the API (S069: a ticket's own cause beside the root
 * cause): the technician logs 30 min of labour, then the engineer closes it with the cause
 * `causeCode`, action 1 (Replace) and the ticket's first symptom (or `symptomId`), as tickets-parts.spec.js does.
 */
async function closeByApi(ticket, causeCode, symptomId = null) {
  const kannan = await personId("technician");
  const technician = await apiAs("technician");
  try {
    const people = (await (await technician.get(`/api/tickets/people?ticket_id=${ticket.id}`)).json()).items;
    const trade = people.find((p) => p.id === kannan).trades[0]?.id ?? null;
    const res = await technician.post(`/api/tickets/${ticket.id}/labour`, {
      data: { person_id: kannan, trade_id: trade, work_date: istDay(0), minutes: 30 },
    });
    expect(res.status(), await res.text()).toBe(201);
  } finally {
    await technician.dispose();
  }
  const engineer = await apiAs("engineer");
  let modeId = symptomId;
  try {
    if (modeId === null) modeId = (await (await engineer.get(`/api/tickets/modes?ticket_id=${ticket.id}`)).json()).items[0].id;
  } finally {
    await engineer.dispose();
  }
  return moveByApi("engineer", ticket.id, "close", {
    cause_id: await causeId(causeCode), action_id: await actionId("1"), failure_mode_id: modeId,
  });
}

/** Add whys to `improvement` through the API as the engineer, in order -> the detail. */
async function whysByApi(improvement, whys) {
  const api = await apiAs("engineer");
  let detail;
  try {
    for (const [question, answer] of whys) {
      const res = await api.post(`/api/improvements/${improvement.id}/whys`, { data: { question, answer } });
      expect(res.status(), await res.text()).toBe(201);
      detail = await res.json();
    }
  } finally {
    await api.dispose();
  }
  return detail;
}

/** The why-why card, and its row at `position`. */
const whyCard = (page) => page.getByTestId("why-why");
const whyRow = (page, position) => whyCard(page).locator(`li[data-why="${position}"]`);
const rootCard = (page) => page.getByTestId("root-cause");

/** Open *Add why*, fill it and save; the dialog must fit. -> the dialog (closed after the save). */
async function addWhy(page, question, answer, evidence) {
  await whyCard(page).getByRole("button", { name: "Add why", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Why?").fill(question);
  await dialog.getByLabel("Because").fill(answer);
  if (evidence) await dialog.getByLabel("Evidence (optional)").fill(evidence);
  return dialog;
}

test("S069: the engineer writes three whys, the second dialog shows the first answer, and moves why 3 to the front", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S069 chain: press did not start");
  const improvement = await startImprovementByApi(ticket);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);

  await addWhy(page, "Why did the press not start?", "The contactor did not close.", "Photo of the contactor");
  await saveDialog(page, "Add why");
  const second = await addWhy(page, "Why did the contactor not close?", "Its contact faces were coated with fine dust.");
  await expect(second.getByTestId("why-previous")).toHaveText("Because: The contactor did not close.");
  await saveDialog(page, "Add why");
  await addWhy(page, "Why was there dust on the faces?", "The panel door seal is torn.");
  await saveDialog(page, "Add why");

  await expect(whyRow(page, 1)).toContainText("1. Why did the press not start?");
  await expect(whyRow(page, 1)).toContainText("The contactor did not close.");
  await expect(whyRow(page, 1)).toContainText("Evidence: Photo of the contactor");
  await expect(whyRow(page, 1)).toContainText("Priya (engineer)");
  await expect(whyRow(page, 2)).toContainText("2. Why did the contactor not close?");
  await expect(whyRow(page, 3)).toContainText("3. Why was there dust on the faces?");

  await page.getByRole("button", { name: "Edit why 3", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByTestId("why-previous")).toHaveText("Because: Its contact faces were coated with fine dust.");
  await dialog.getByLabel("Place in the chain").selectOption("1");
  await saveDialog(page, "Save why");

  await expect(whyRow(page, 1)).toContainText("1. Why was there dust on the faces?");
  await expect(whyRow(page, 2)).toContainText("2. Why did the press not start?");
  await expect(whyRow(page, 3)).toContainText("3. Why did the contactor not close?");

  // A text-only edit does not resend the place (S069 A1): the PUT body has no position
  await page.getByRole("button", { name: "Edit why 2", exact: true }).click();
  const textDialog = await openDialog(page);
  await textDialog.getByLabel("Because").fill("The start button circuit was dead.");
  const put = page.waitForRequest((req) => req.method() === "PUT" && /\/whys\/\d+$/.test(req.url()));
  await saveDialog(page, "Save why");
  expect((await put).postDataJSON()).not.toHaveProperty("position");
  await expect(whyRow(page, 2)).toContainText("The start button circuit was dead.");
});

test("S069: the engineer removes why 2 after the confirmation on the row; the rest are numbered 1 and 2", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S069 remove: three whys");
  const improvement = await startImprovementByApi(ticket);
  await whysByApi(improvement, [["Why A?", "Because A"], ["Why B?", "Because B"], ["Why C?", "Because C"]]);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);

  await page.getByRole("button", { name: "Remove why 2", exact: true }).click();
  await expect(whyRow(page, 2)).toContainText("Remove why 2? You cannot undo this.");
  await whyRow(page, 2).getByRole("button", { name: "Remove why", exact: true }).click();

  await expect(whyCard(page).locator("li[data-why]")).toHaveCount(2);
  await expect(whyRow(page, 1)).toContainText("1. Why A?");
  await expect(whyRow(page, 2)).toContainText("2. Why C?");
});

test("S069: the engineer sets the root cause from the last why; the tickets' own cause shows beside it", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S069 root: worn contacts");
  await closeByApi(ticket, "3.4");
  const improvement = await startImprovementByApi(ticket);
  await whysByApi(improvement, [["Why did the press not start?", "The contacts were worn."],
    ["Why were they worn?", "The presses have no PM plan"]]);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);
  await expect(rootCard(page)).toContainText("No root cause yet. Find it with the why-why first.");

  await page.getByRole("button", { name: "Set root cause", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByLabel("Root cause", { exact: true })).toHaveValue("The presses have no PM plan");
  await dialog.getByLabel("Cause", { exact: true }).selectOption({ label: "4.2 Management error" });
  await saveDialog(page, "Save root cause");

  await expect(rootCard(page)).toContainText("4.2 Management error");
  await expect(rootCard(page)).toContainText("Group: Management");
  await expect(rootCard(page)).toContainText("The presses have no PM plan");
  const note = page.getByTestId("ticket-causes");
  await expect(note).toContainText("Cause on the tickets: 3.4 Expected wear and tear");
  await expect(note).toContainText("The ticket's cause says why the part failed. The root cause says why the plant let it happen.");
  await expect(page.getByRole("button", { name: "Edit root cause", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Set root cause", exact: true })).toHaveCount(0);
});

test("S069: the help line shows on the why-why card, also with no whys", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S069 help: empty chain");
  const improvement = await startImprovementByApi(ticket);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);
  await expect(whyCard(page)).toContainText("Ask why until the answer is something the plant can change.");
  await expect(whyCard(page)).toContainText("No whys yet.");
  await expect(whyCard(page)).toContainText("Start with why the problem happened.");
});

test("S069: the operator reads the whys and the root cause, with no button to change them", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S069 operator: read only");
  const improvement = await startImprovementByApi(ticket);
  await whysByApi(improvement, [["Why A?", "Because A"], ["Why B?", "Because B"]]);
  const api = await apiAs("engineer");
  try {
    const res = await api.put(`/api/improvements/${improvement.id}/root-cause`,
      { data: { root_cause: "Because B", root_cause_id: await causeId("4.2") } });
    expect(res.status(), await res.text()).toBe(200);
  } finally {
    await api.dispose();
  }
  await asPerson(page, "operator", `/tickets/improvements/${improvement.id}`);

  await expect(whyRow(page, 1)).toContainText("1. Why A?");
  await expect(whyRow(page, 2)).toContainText("2. Why B?");
  await expect(rootCard(page)).toContainText("4.2 Management error");
  for (const name of ["Add why", "Edit why 1", "Remove why 1", "Set root cause", "Edit root cause"]) {
    await expect(page.getByRole("button", { name, exact: true })).toHaveCount(0);
  }
});

// ---------------------------------------------------------------------------------------------
// S071: the countermeasures card, its dialogs, the inline cancel and the photos
// ---------------------------------------------------------------------------------------------

/** The countermeasures card, and its row for the action `id`. */
const measureCard = (page) => page.getByTestId("countermeasures");
const measureRow = (page, id) => measureCard(page).locator(`li[data-action="${id}"]`);

/** Open *Add countermeasure* and fill it (the date is left at its default); the dialog must fit. -> the dialog. */
async function fillAction(page, { kind, text, owner }) {
  await measureCard(page).getByRole("button", { name: "Add countermeasure", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Kind", { exact: true }).selectOption({ label: kind });
  await dialog.getByLabel("What will be done", { exact: true }).fill(text);
  await dialog.getByLabel("Owner", { exact: true }).selectOption({ label: owner });
  return dialog;
}

test("S071: the engineer adds a countermeasure, changes its due date, adds a second and cancels it on its row", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S071 plan: torn door gasket");
  const improvement = await startImprovementByApi(ticket);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);
  const card = measureCard(page);
  await expect(card).toContainText("No countermeasures yet.");
  await expect(card).toContainText("Add what the team will do about the root cause.");
  // The six kinds are said under the card, always
  for (const sentence of ["Fixes this failure now, often already done on the ticket.", "Applies the fix to the similar machines."]) {
    await expect(page.getByTestId("kind-help")).toContainText(sentence);
  }

  const dialog = await fillAction(page, { kind: "Corrective", text: "Replace the torn door gasket", owner: "Kannan (technician)" });
  await expect(dialog.getByTestId("kind-sentence")).toHaveText("Removes the cause here, so this failure does not come back.");
  await expect(dialog.getByLabel("Due date", { exact: true })).toHaveValue(istDay(14));
  await saveDialog(page, "Add countermeasure");

  const first = card.locator("li[data-action]").first();
  await expect(first).toContainText("Corrective");
  await expect(first).toContainText("Open");
  await expect(first).toContainText("Replace the torn door gasket");
  await expect(first).toContainText("Owner: Kannan (technician)");
  await expect(card.locator(".card-header")).toContainText("Countermeasures (0 of 1 done)");

  // Change the due date
  const due = istDay(20);
  await page.getByRole("button", { name: "Change countermeasure 1", exact: true }).click();
  await expectDialogFits(page);
  const change = await openDialog(page);
  await expect(change.locator(".modal-title")).toHaveText("Change countermeasure");
  await change.getByLabel("Due date", { exact: true }).fill(due);
  await saveDialog(page, "Save countermeasure");
  await expect(first).toContainText(`due ${shownDay(due)}`);

  // A second one, cancelled on its row
  await fillAction(page, { kind: "Preventive", text: "Add the door seal to the PM plan", owner: "Kannan (technician)" });
  await saveDialog(page, "Add countermeasure");
  await expect(card.locator("li[data-action]")).toHaveCount(2);
  const second = card.locator("li[data-action]").nth(1);
  await page.getByRole("button", { name: "Cancel countermeasure 2", exact: true }).click();
  await expect(second).toContainText("Cancel this countermeasure? It stays on the record with your reason.");
  const cancel = second.getByRole("button", { name: "Cancel countermeasure", exact: true });
  await expect(cancel).toBeDisabled();
  await second.getByLabel("Why cancel it?").fill("Added by mistake");
  await cancel.click();
  await expect(second).toContainText("Cancelled");
  await expect(second).toContainText("by Priya (engineer): Added by mistake");
  await expect(card.locator(".card-header")).toContainText("Countermeasures (0 of 1 done)");
  await expect(page.getByRole("button", { name: "Cancel countermeasure 2", exact: true })).toHaveCount(0);
});

test("S071: a cancel refused because the owner marked it done meanwhile shows the row done, with no cancel ask left", async ({ page, consoleWatch }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S071 stale cancel: done meanwhile");
  const improvement = await startImprovementByApi(ticket);
  const { action } = await addActionByApi(improvement, { text: "S071 stale cancel: fit the new gasket" });
  consoleWatch.allowFailedRequest(`/api/improvements/${improvement.id}/actions/${action.id}/cancel`, 409);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);
  const row = measureRow(page, action.id);
  await page.getByRole("button", { name: "Cancel countermeasure 1", exact: true }).click();
  await row.getByLabel("Why cancel it?").fill("Not needed");
  await markDoneByApi(improvement, action, "technician");   // the owner, on another phone
  await row.getByRole("button", { name: "Cancel countermeasure", exact: true }).click();

  await expect(row).toContainText("Done");
  await expect(row).not.toContainText("Cancel this countermeasure?");
  await expect(row.getByLabel("Why cancel it?")).toHaveCount(0);
});

test("S071: the engineer marks done a countermeasure owned by a person with no login; the row says who recorded it", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S071 proxy: fitter job");
  const improvement = await startImprovementByApi(ticket);
  const { action } = await addActionByApi(improvement, { owner: "Ramesh (operator, no phone)", text: "S071 proxy: clean the contacts" });
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);
  const row = measureRow(page, action.id);
  await row.getByRole("button", { name: "Mark done", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByTestId("done-target")).toHaveText("S071 proxy: clean the contacts");
  await dialog.getByLabel("What did you do?").fill("Contacts cleaned by the fitter.");
  await saveDialog(page, "Mark done");

  await expect(row).toContainText("Done");
  await expect(row).toContainText("recorded by Priya (engineer)");
  await expect(row).toContainText("Contacts cleaned by the fitter.");
  await expect(row.getByRole("button", { name: "Add photos", exact: true })).toBeVisible();
  await expect(row.getByRole("button", { name: "Mark done", exact: true })).toHaveCount(0);
  await expect(measureCard(page).locator(".card-header")).toContainText("Countermeasures (1 of 1 done)");
});

test("S071: a technician who is not the owner and an operator see the rows but none of the buttons", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S071 access: read only");
  const improvement = await startImprovementByApi(ticket);
  const { action } = await addActionByApi(improvement, { text: "S071 access: the owner's job" });
  for (const who of ["technician2", "operator"]) {
    await asPerson(page, who, `/tickets/improvements/${improvement.id}`);
    await expect(measureRow(page, action.id)).toContainText("S071 access: the owner's job");
    await expect(page.getByTestId("kind-help")).toContainText("Teaches the team what was learned.");
    for (const name of ["Mark done", "Change countermeasure 1", "Cancel countermeasure 1", "Add countermeasure"]) {
      await expect(page.getByRole("button", { name, exact: true }), `${who} sees ${name}`).toHaveCount(0);
    }
  }
});

test("S071: the manager removes a countermeasure photo, then restores it in Settings", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S071 photo: gasket");
  const improvement = await startImprovementByApi(ticket);
  const { action } = await addActionByApi(improvement, { text: "S071 photo: fit the gasket" });
  await markDoneByApi(improvement, action);
  await uploadActionPhotoByApi(action, "Gasket fitted");
  await asPerson(page, "manager", `/tickets/improvements/${improvement.id}`);
  const row = measureRow(page, action.id);
  await row.getByRole("button", { name: "Photos (1)", exact: true }).click();
  await row.getByRole("button", { name: "Gasket fitted" }).click();
  const viewer = page.locator(".modal.show");
  await viewer.getByRole("button", { name: "Remove", exact: true }).click();
  await viewer.getByRole("button", { name: "Yes", exact: true }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  // The count is true again: no photos left on a done row reads "Add photos"
  await expect(row.getByRole("button", { name: "Add photos", exact: true })).toBeVisible();
  await expect(row.getByRole("button", { name: "Photos (1)", exact: true })).toHaveCount(0);

  await page.goto("/settings");
  await page.getByRole("searchbox", { name: "Search removed documents" }).fill(improvement.serial);
  const removed = page.locator("tr", { hasText: "Gasket fitted" });
  await expect(removed).toContainText(`Countermeasure ${improvement.serial} · Corrective`);
  await removed.getByRole("button", { name: "Restore" }).click();
  await expect(page.getByText("Restored 'Gasket fitted'.")).toBeVisible();
  await expect(removed).toHaveCount(0);
});

test("S071: a photo the server refuses leaves the countermeasure done and the dialog open to add it again", async ({ page, consoleWatch }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S071 refused: bad photo");
  const improvement = await startImprovementByApi(ticket);
  const { action } = await addActionByApi(improvement, { text: "S071 refused: job with a bad photo" });
  consoleWatch.allowFailedRequest(`/api/improvements/actions/${action.id}/documents`, 400);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);
  const row = measureRow(page, action.id);
  await row.getByRole("button", { name: "Mark done", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("What did you do?").fill("Done, with a photo that is not a photo.");
  await dialog.locator("input[type=file]").setInputFiles({ name: "bad.jpg", mimeType: "image/jpeg", buffer: Buffer.from("not an image") });
  await dialog.locator(".modal-footer button[type=submit]").click();

  await expect(dialog.getByText("Marked done. A photo was not saved. Add it again, or close.")).toBeVisible();
  await expect(dialog.locator('li[data-photo="bad.jpg"]')).toBeVisible();
  await expect(dialog.locator(".modal-footer").getByRole("button", { name: "Close", exact: true })).toBeVisible();
  await expect(dialog.locator(".modal-footer button[type=submit]")).toHaveCount(0);
  await expect(row).toContainText("Done");
  // In the close-only phase a chosen photo goes up at once; closing then leaves the row at "Photos (1)"
  await dialog.locator("input[type=file]").setInputFiles(TEST_PHOTO);
  await expect(dialog.locator('li[data-photo="test-photo.jpg"] .fa-check')).toBeVisible();
  await dialog.locator(".modal-footer").getByRole("button", { name: "Close", exact: true }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(row.getByRole("button", { name: "Photos (1)", exact: true })).toBeVisible();
});

// ---------------------------------------------------------------------------------------------
// S073: the states, the watch, the timeline and the verified close
// ---------------------------------------------------------------------------------------------

const MINUTES_PER_DAY = 24 * 60;

/**
 * An improvement that is *Ready to verify* (S072 § 5.2), made through the API: a ticket on
 * `machine` (the MCC1 mill, which no other spec closes tickets on, so no repeat shows) raised as admin (who may back-date) 40 days back and fixed, closed with the machine's
 * first symptom, an improvement led by Priya with its root cause, one *Corrective* countermeasure
 * done 35 days back, and a watch of 30 days, which ended 5 days ago. -> {improvement, ticket, modeId}.
 */
async function readyImprovement(machine = seed.mcc1Mill) {
  const kannan = await personId("technician");
  const ticket = await raiseByApi("admin", {
    equipment_id: machine.id,
    intensity: "critical",
    description: "S073 set-up: the press did not start",
    occurred_at: istLocal(40 * MINUTES_PER_DAY),
    restore: { person_id: kannan, occurred_at: istLocal(40 * MINUTES_PER_DAY - 50) },
  });
  const closed = await closeByApi(ticket, "3.4");
  const improvement = await startImprovementByApi(ticket);
  const engineer = await apiAs("engineer");
  try {
    let res = await engineer.put(`/api/improvements/${improvement.id}/root-cause`,
      { data: { root_cause: "S073 set-up: no PM plan", root_cause_id: await causeId("4.2") } });
    expect(res.status(), await res.text()).toBe(200);
    const { action } = await addActionByApi(improvement, { text: "S073 set-up: fit the new seal" });
    res = await engineer.post(`/api/improvements/${improvement.id}/actions/${action.id}/done`,
      { data: { done_text: "S073 set-up: done", done_at: istLocal(35 * MINUTES_PER_DAY) } });
    expect(res.status(), await res.text()).toBe(200);
    res = await engineer.put(`/api/improvements/${improvement.id}`, { data: { watch_days: 30 } });
    expect(res.status(), await res.text()).toBe(200);
    return { improvement: await res.json(), ticket, modeId: closed.failure_mode?.id };
  } finally {
    await engineer.dispose();
  }
}

/** The improvement page's header badge. */
const stateBadgeOf = (page) => page.locator(".state-badge");
const timelineCard = (page) => page.getByTestId("improvement-timeline");

test("S073: the manager sees the watch after 30 days, taps Close: it worked, and the page reads closed", async ({ page }) => {
  const { improvement } = await readyImprovement();
  await asPerson(page, "manager", `/tickets/improvements/${improvement.id}`);

  await expect(stateBadgeOf(page)).toHaveText("Ready to verify");
  const watchCard = page.getByTestId("watch-card");
  await expect(watchCard).toContainText("Did it come back?");
  await expect(watchCard).toContainText(/No ticket with the symptom .* since \d{2}-\d{2}-\d{4}\./);
  await expect(watchCard.getByRole("row", { name: /^Breakdowns/ })).toBeVisible();
  await expect(watchCard.getByRole("row", { name: /^Downtime/ })).toBeVisible();
  await expect(watchCard.getByRole("columnheader", { name: "30 days after" })).toBeVisible();
  await expectNoSidewaysScroll(page);

  await page.getByRole("button", { name: "Close: it worked", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByTestId("verify-consequence")).toHaveText(`${improvement.serial} closes and cannot be changed after.`);
  await dialog.getByLabel("Remark (optional)").fill("Checked the panels on three presses.");
  await saveDialog(page, "Close: it worked");

  await expect(stateBadgeOf(page)).toHaveText("Closed: it worked");
  await expect(page.getByTestId("state-line")).toContainText(/^Closed \d{2}-\d{2}-\d{4} by Arun \(manager\): it worked$/);
  await expect(page.getByTestId("close-remark")).toHaveText("Checked the panels on three presses.");
  for (const name of ["Edit", "Add ticket", "Add why", "Add countermeasure", "Add note", "Drop improvement", "Change watch",
    "Close: it worked", "Did not work — analyse again"]) {
    await expect(page.getByRole("button", { name, exact: true }), `a closed page shows ${name}`).toHaveCount(0);
  }
  await expect(timelineCard(page).locator("li").first()).toContainText("Closed: it worked");
});

test("S073: the lead taps Did not work, is asked why, and lands on the new improvement with the same ticket", async ({ page, consoleWatch }) => {
  const { improvement, ticket } = await readyImprovement();
  consoleWatch.allowFailedRequest("/verify/not-effective", 400);
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);

  await page.getByRole("button", { name: "Did not work — analyse again", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByTestId("verify-consequence")).toContainText("A new improvement starts with its tickets, and you go there.");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Say why it did not work");
  await dialog.getByLabel("Why did it not work?").fill("The dust came back on the third press.");
  await saveDialog(page, "Close and analyse again");

  await expect(page).not.toHaveURL(new RegExp(`/improvements/${improvement.id}$`));
  await expect(stateBadgeOf(page)).toHaveText("Analysing");
  await expect(page.getByRole("link", { name: `Follow-up of ${improvement.serial}` })).toBeVisible();
  await expect(page.getByText("Tickets (1)")).toBeVisible();
  await expect(ticketRow(page, ticket.serial)).toBeVisible();

  await page.getByRole("link", { name: `Follow-up of ${improvement.serial}` }).click();
  await expect(stateBadgeOf(page)).toHaveText("Closed: did not work");
  await expect(page.getByTestId("state-line")).toContainText(/^Closed \d{2}-\d{2}-\d{4} by Priya \(engineer\), the lead: did not work$/);
  await expect(page.getByTestId("close-remark")).toHaveText("The dust came back on the third press.");
  await expect(page.getByRole("link", { name: /^Analysed again in IM-/ })).toBeVisible();
});

test("S073: a repeat of the symptom in the watch is shown with its ticket", async ({ page }) => {
  // A machine of its own, so the repeat shows on no other test's watch
  const { improvement, modeId } = await readyImprovement(seed.gearbox);
  const repeat = await raiseByApi("admin", {
    equipment_id: seed.gearbox.id,
    intensity: "critical",
    description: "S073 set-up: it came back",
    occurred_at: istLocal(10 * MINUTES_PER_DAY),
    restore: { person_id: await personId("technician"), occurred_at: istLocal(10 * MINUTES_PER_DAY - 50) },
  });
  await closeByApi(repeat, "3.4", modeId);
  await asPerson(page, "manager", `/tickets/improvements/${improvement.id}`);

  const warning = page.getByTestId("watch-card").locator(".alert-warning");
  await expect(warning).toContainText(/Came back \d+ times?:/);
  await expect(warning.getByRole("link", { name: repeat.serial })).toBeVisible();
  await expect(warning).toContainText("Check whether it has the same cause.");
  await expectNoSidewaysScroll(page);
});

test("S073: the operator adds a note to the timeline; IT admin sees no Add note", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S073 note: dust on the panel");
  const improvement = await startImprovementByApi(ticket);
  await asPerson(page, "operator", `/tickets/improvements/${improvement.id}`);

  await timelineCard(page).getByRole("button", { name: "Add note", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Note").fill("The same dust on the panel of press 4.");
  await saveDialog(page, "Save note");
  const first = timelineCard(page).locator("li").first();
  await expect(first).toContainText("Note");
  await expect(first).toContainText("The same dust on the panel of press 4.");
  await expect(first).toContainText("Muthu (operator)");

  await asPerson(page, "it_admin", `/tickets/improvements/${improvement.id}`);
  await expect(timelineCard(page).locator("li").first()).toContainText("The same dust on the panel of press 4.");
  await expect(page.getByRole("button", { name: "Add note", exact: true })).toHaveCount(0);
});

test("S073: the lead changes the watch to 120 days; the end date moves and the timeline says so", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S073 watch: change the length");
  const improvement = await startImprovementByApi(ticket);
  const engineer = await apiAs("engineer");
  try {
    let res = await engineer.put(`/api/improvements/${improvement.id}/root-cause`,
      { data: { root_cause: "S073 watch: no PM plan", root_cause_id: await causeId("4.2") } });
    expect(res.status(), await res.text()).toBe(200);
    const { action } = await addActionByApi(improvement, { text: "S073 watch: fit the new seal" });
    await markDoneByApi(improvement, action);
    res = await engineer.get(`/api/improvements/${improvement.id}`);
    expect((await res.json()).state).toBe("watching");
  } finally {
    await engineer.dispose();
  }
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);
  await expect(stateBadgeOf(page)).toHaveText("Watching");
  await expect(page.getByTestId("state-line")).toContainText(`until ${shownDay(istDay(90))}`);

  await page.getByRole("button", { name: "Change watch", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Watch for (days)").fill("120");
  await expect(dialog.getByTestId("watch-ends")).toHaveText(`Ends on ${shownDay(istDay(120))}`);
  await saveDialog(page, "Save watch");

  await expect(page.getByTestId("state-line")).toContainText(`until ${shownDay(istDay(120))}`);
  const first = timelineCard(page).locator("li").first();
  await expect(first).toContainText("Changed");
  await expect(first).toContainText("Watch: 90 days → 120 days");
});

test("S073: the lead drops an improvement with an open countermeasure; the countermeasure is cancelled", async ({ page }) => {
  const ticket = await raiseFixed(seed.extruder.id, "S073 drop: started by mistake");
  const improvement = await startImprovementByApi(ticket);
  const { action } = await addActionByApi(improvement, { text: "S073 drop: the job that is not needed" });
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);

  await page.getByRole("button", { name: "Drop improvement", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog).toContainText(`Drop ${improvement.serial}? Its open countermeasures are cancelled. You cannot undo this.`);
  await dialog.getByLabel("Why drop it?").fill("Started by mistake.");
  await saveDialog(page, "Drop improvement");

  await expect(stateBadgeOf(page)).toHaveText("Dropped");
  await expect(page.getByTestId("state-line")).toContainText(/^Dropped \d{2}-\d{2}-\d{4} by Priya \(engineer\), the lead$/);
  await expect(measureRow(page, action.id)).toContainText("Cancelled");
  await expect(page.getByRole("button", { name: "Drop improvement", exact: true })).toHaveCount(0);
});

// ---------------------------------------------------------------------------------------------
// S077: Write lesson on a Lesson countermeasure
// ---------------------------------------------------------------------------------------------

test("S077: Write lesson on a Lesson countermeasure opens the dialog seeded, and the countermeasure then links its lesson", async ({ page }, testInfo) => {
  // A machine of its own, so no seed machine gains a lesson
  const { a, className } = await lessonMachines(testInfo, "write");
  const improvement = await startImprovementByApi(await raiseFixed(a.id, "S077 write: contactor chatters"));
  const { action } = await addActionByApi(improvement, { kind: "lesson", text: "S077 write: keep the panel door shut" });
  await asPerson(page, "engineer", `/tickets/improvements/${improvement.id}`);
  const row = measureRow(page, action.id);
  await row.getByRole("button", { name: "Write lesson", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  // Seeded with the countermeasure's text; the improvement's machine has no class, so the dialog read it
  await expect(dialog.getByLabel("Lesson text")).toHaveValue("S077 write: keep the panel door shut");
  await expect(dialog.getByLabel(`Show on every machine of class ${className}`)).not.toBeChecked();
  await dialog.getByLabel("Title").fill("Keep the panel door shut");
  await saveDialog(page, "Save lesson");

  // The page stays on the improvement; the row links the lesson
  await expect(page).toHaveURL(new RegExp(`/tickets/improvements/${improvement.id}$`));
  const link = row.getByRole("link", { name: /^Lesson OPL-\d+ · Keep the panel door shut$/ });
  await expect(link).toBeVisible();
  await expect(row.getByRole("button", { name: "Write lesson", exact: true })).toHaveCount(0);
  await expect(row.getByRole("button", { name: "Mark done", exact: true })).toBeVisible();
  await link.click();
  await expect(page).toHaveURL(/\/equipment\/lessons\/\d+$/);
  await expect(page.getByText(`From improvement ${improvement.serial}`)).toBeVisible();
});
