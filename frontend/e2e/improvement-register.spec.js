// The improvement register's print page (S076) — in place of the step's manual checks, but paper:
// the sections for the period and for today, the site and period controls kept in the link, the
// refusals, the roles without the key, and the paper rules. Set-up by API (support/improvements.js);
// the lane's database holds other tests' improvements, so rows are found by serial, never by count.
// A close as "it worked" or "did not work" needs a 30-day watch: the API tests cover those.
import { test, expect } from "./support/test.js";
import { expectNoSidewaysScroll } from "./support/dialogs.js";
import { addActionByApi, dropByApi, raiseFixed, startImprovementByApi } from "./support/improvements.js";
import { asPerson, seedIds } from "./support/people.js";
import { istDay } from "./support/tickets.js";

const REGISTER = "/tickets/improvements/register";
const THREE_DAYS = 3 * 24 * 60;

let seed;
let started; // a breakdown 3 days old, an improvement from it, one countermeasure 3 days late
let dropped; // a second improvement, dropped by the lead

test.beforeAll(async () => {
  seed = await seedIds();
  const ticket = await raiseFixed(seed.extruder.id, "S076 register: contactor chatters", { breakdown: true, minutesAgo: THREE_DAYS });
  started = await startImprovementByApi(ticket, { title: "S076 register: contactor chatters" });
  await addActionByApi(started, { text: "S076 register: fit the new gasket", due: istDay(-3) });
  const second = await raiseFixed(seed.extruder.id, "S076 register: the one dropped");
  dropped = await startImprovementByApi(second, { title: "S076 register: the one dropped" });
  await dropByApi(dropped, "S076 register: started by mistake");
});

/** The sheet's section under the heading that starts with `title`. */
const section = (page, title) => page.locator("section", { has: page.getByRole("heading", { name: new RegExp(`^${title}`) }) });
/** The table row that holds `text`, in `scope`. */
const rowWith = (scope, text) => scope.locator("tbody tr", { hasText: text });

/** Choose the site whose option starts with `code` ("SMTW — Main factory"), found by its text. */
async function chooseSite(page, code) {
  const select = page.getByLabel("Site", { exact: true });
  const value = await select.locator("option", { hasText: new RegExp(`^${code} `) }).getAttribute("value");
  await select.selectOption(value);
}

/** The first and last day of the IST month `monthsBack` months before today's, "DD-MM-YYYY to DD-MM-YYYY". */
function monthText(monthsBack) {
  const [year, month] = istDay(0).split("-").map(Number);
  const index = year * 12 + (month - 1) - monthsBack;
  const y = Math.floor(index / 12);
  const m = (index % 12) + 1;
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const mm = String(m).padStart(2, "0");
  return `01-${mm}-${y} to ${last}-${mm}-${y}`;
}

test("S076: the engineer sees the register of this month: the improvement started, open with its age, and its overdue countermeasure", async ({ page }) => {
  await asPerson(page, "engineer", REGISTER);
  await expect(page.getByRole("heading", { name: "Improvement register", level: 1 })).toBeVisible();
  const header = page.locator(".sheet-header");
  await expect(header).toContainText("SMTW — ");
  await expect(header).toContainText(monthText(0));
  await expect(header).toContainText(/Printed on \d{2}-\d{2}-\d{4} \d{2}:\d{2} by Priya \(engineer\)/);

  // Started in the period: the state now
  const startedRows = rowWith(section(page, "Started in the period"), started.serial);
  await expect(startedRows).toContainText("S076 register: contactor chatters");
  await expect(startedRows).toContainText("Analysing");

  // Open now: the table counts it, the list shows its age and its countermeasures
  const open = section(page, "Open now");
  await expect(open.locator("table.counts")).toContainText("Analysing");
  const openRow = rowWith(open, started.serial);
  await expect(openRow.locator("td").nth(1)).toHaveText("0");
  await expect(openRow).toContainText("1 open, 1 overdue");

  // Overdue now: the countermeasure, its owner and the days late
  const lateRow = rowWith(section(page, "Countermeasures overdue now"), started.serial);
  await expect(lateRow).toContainText("S076 register: fit the new gasket");
  await expect(lateRow).toContainText("Corrective");
  await expect(lateRow).toContainText("Kannan (technician)");
  await expect(lateRow.locator("td").last()).toHaveText("3");

  // On screen the serial links to the improvement
  await expect(startedRows.getByRole("link", { name: started.serial })).toHaveAttribute("href", `/tickets/improvements/${started.id}`);
});

test("S076: the dropped improvement shows under Closed in the period with its reason", async ({ page }) => {
  await asPerson(page, "engineer", REGISTER);
  const closed = section(page, "Closed in the period");
  const row = rowWith(closed, dropped.serial);
  await expect(row).toContainText("Dropped");
  await expect(row).toContainText("S076 register: started by mistake");
  await expect(row).toContainText("Priya (engineer)");
  // The lead dropped it, but a drop is no verification: never "the lead" (BR1-03)
  await expect(row).not.toContainText("the lead");
  await expect(closed.locator(".count-line")).toContainText(/Dropped [1-9]\d*/);
});

test("S076: the manager picks BRICKS and Show last month; the link and the period line change", async ({ page }) => {
  await asPerson(page, "manager", REGISTER);
  await expect(page.getByLabel("Site", { exact: true })).toBeVisible();
  await chooseSite(page, "SMTW");
  await expect(page.locator(".sheet-header")).toContainText("SMTW — ");
  await chooseSite(page, "BRICKS");
  await expect(page.locator(".sheet-header")).toContainText("BRICKS — ");
  await expect(page).toHaveURL(/site_id=\d+/);

  await page.getByRole("button", { name: "Show last month" }).click();
  await expect(page.locator(".sheet-header")).toContainText(monthText(1));
  await expect(page).toHaveURL(/from=\d{4}-\d{2}-01&to=\d{4}-\d{2}-\d{2}/);
  await expect(page.getByLabel("From", { exact: true })).toHaveValue(/^\d{4}-\d{2}-01$/);

  // A reload keeps the choice
  await page.reload();
  await expect(page.locator(".sheet-header")).toContainText("BRICKS — ");
  await expect(page.locator(".sheet-header")).toContainText(monthText(1));
});

test("S076: a start after the end is refused under the period fields, and the sheet stays", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/improvements/register", 400);
  await asPerson(page, "engineer", REGISTER);
  const header = page.locator(".sheet-header");
  await expect(header).toContainText(monthText(0));

  await page.getByLabel("From", { exact: true }).fill("2090-05-10");
  const message = page.getByRole("alert").filter({ hasText: "The start must be on or before the end" });
  await expect(message).toBeVisible();
  // The register on screen is the last good one, with its own period
  await expect(header).toContainText(monthText(0));
  await expect(page.getByRole("button", { name: "Retry" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Print", exact: true })).toBeVisible();
});

test("S076: the operator has no Print register button and the address shows a plain line, no Retry", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/improvements/register", 403);
  await asPerson(page, "operator", "/tickets/improvements");
  await expect(page.getByRole("combobox", { name: "State" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Print register" })).toHaveCount(0);

  await page.goto(REGISTER);
  await expect(page.getByText("You can't see the register.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Improvement register" })).toHaveCount(0);
  // Only the plain line: no date fields, month buttons or print help (CR1-01/02)
  await expect(page.getByLabel("From", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Show this month" })).toHaveCount(0);
  await expect(page.getByText("Print in")).toHaveCount(0);
});

test("S076: Show this month works on a page opened with a refused period", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/improvements/register", 400);
  await asPerson(page, "engineer", `${REGISTER}?from=2090-05-10&to=2090-05-01`);
  await expect(page.getByRole("alert").filter({ hasText: "The start must be on or before the end" })).toBeVisible();
  await expect(page.locator(".sheet-header")).toHaveCount(0);
  await page.getByRole("button", { name: "Show this month" }).click();
  await expect(page.locator(".sheet-header")).toContainText(monthText(0));
});

test("S076: on paper the controls are left out and the sheet has the review lines", async ({ page }) => {
  await asPerson(page, "engineer", REGISTER);
  await expect(page.getByRole("heading", { name: "Improvement register", level: 1 })).toBeVisible();
  await expect(page.getByLabel("From", { exact: true })).toBeVisible();

  await page.emulateMedia({ media: "print" });
  await expect(page.getByLabel("From", { exact: true })).toBeHidden();
  await expect(page.getByRole("button", { name: "Show this month" })).toBeHidden();
  await expect(page.getByRole("button", { name: "Print", exact: true })).toBeHidden();
  const lines = page.locator(".review-lines");
  await expect(lines).toBeVisible();
  for (const text of ["Reviewed by", "Date", "Decisions and actions"]) {
    await expect(lines.getByText(text, { exact: true })).toBeVisible();
  }
  await page.emulateMedia({ media: "screen" });
  await expect(page.getByLabel("From", { exact: true })).toBeVisible();
});

test("S076: Print register on the Improvements list opens the register in a new tab", { tag: "@device" }, async ({ page }) => {
  test.skip(page.viewportSize().width < 768, "the office's print buttons are hidden on a phone (S076 D12)");
  await asPerson(page, "engineer", "/tickets/improvements");
  const [sheet] = await Promise.all([
    page.context().waitForEvent("page"),
    page.getByRole("button", { name: "Print register" }).click(),
  ]);
  await expect(sheet).toHaveURL(/\/tickets\/improvements\/register/);
  await expect(sheet.getByRole("heading", { name: "Improvement register", level: 1 })).toBeVisible();
  await sheet.close();
});

test("S076: the register fits a phone with no sideways scroll", { tag: "@device" }, async ({ page }) => {
  test.skip(page.viewportSize().width >= 768, "a phone check: the office's screens are wider");
  await asPerson(page, "engineer", REGISTER);
  await expect(page.getByRole("heading", { name: "Improvement register", level: 1 })).toBeVisible();
  await expect(rowWith(section(page, "Open now"), started.serial)).toBeVisible();
  await expectNoSidewaysScroll(page);
});
