// The improvement screens (S068; the record is S067's) — in place of the step's manual checks.
// Each test makes its own tickets and improvements through the API (setup), then works them on
// the screens. Every dialog opened must fit (expectDialogFits).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { addTicketByApi, raiseFixed, startImprovementByApi } from "./support/improvements.js";
import { asPerson, seedIds } from "./support/people.js";
import { saveDialog } from "./support/tickets.js";

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
