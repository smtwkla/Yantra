// The improvement screens (S068; the record is S067's) and the analysis on them (S069) — in place of the steps' manual checks.
// Each test makes its own tickets and improvements through the API (setup), then works them on
// the screens. Every dialog opened must fit (expectDialogFits).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { addTicketByApi, raiseFixed, startImprovementByApi } from "./support/improvements.js";
import { apiAs, asPerson, personId, seedIds } from "./support/people.js";
import { actionId, causeId, istDay, moveByApi, saveDialog } from "./support/tickets.js";

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
  await page.getByRole("link", { name: ticket.serial }).click();
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
  await expect(page.getByText("S068 edit: the contactor chatters when the motor starts")).toBeVisible();
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
 * `causeCode`, action 1 (Replace) and the ticket's first symptom, as tickets-parts.spec.js does.
 */
async function closeByApi(ticket, causeCode) {
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
  let modeId;
  try {
    modeId = (await (await engineer.get(`/api/tickets/modes?ticket_id=${ticket.id}`)).json()).items[0].id;
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
