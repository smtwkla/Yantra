// The Me page (S031 § 8 Automated): open work, tickets I raised, my activity.  Each test raises
// its own ticket on the seed's extruder through the API (setup) and finds it by serial, because
// other specs in the same lane add tickets too.  The tickets are closed after each test.
import { test, expect } from "./support/test.js";
import { expectNoSidewaysScroll } from "./support/dialogs.js";
import { apiAs, asPerson, seedIds } from "./support/people.js";
import { navItem } from "./support/nav.js";
import { causeId, moveByApi, raiseByApi } from "./support/tickets.js";

let seed;
let raised = []; // this test's tickets, closed after it

test.beforeAll(async () => {
  seed = await seedIds();
});

test.afterEach(async () => {
  const api = await apiAs("admin");
  try {
    for (const id of raised) {
      const ticket = await (await api.get(`/api/tickets/${id}`)).json();
      if (ticket.state === "closed") continue;
      const res = await api.post(`/api/tickets/${id}/moves/not-a-fault`, {
        data: { cause_id: await causeId("5.1"), remark: "S031 test: tidy-up" },
      });
      expect(res.status(), await res.text()).toBe(200);
    }
  } finally {
    raised = [];
    await api.dispose();
  }
});

/** A defect on the extruder, raised by `key` (default the operator) through the API -> the ticket. */
async function raiseDefect(description, key = "operator") {
  const ticket = await raiseByApi(key, { equipment_id: seed.extruder.id, intensity: "degraded", description });
  raised.push(ticket.id);
  return ticket;
}

/** Open Me from the bottom bar (phone) or the sidebar (desktop): the one visible "Me" item. */
async function openMe(page) {
  await navItem(page, "Me").click();
  await expect(page).toHaveURL(/\/me(\?|$)/);
}

const tabButton = (page, name) => page.getByRole("button", { name, exact: true });
const rowOf = (page, serial) => page.locator(".list-group-item").filter({ hasText: serial });

test("S031: a technician acknowledges a ticket; Open work lists it; a tap opens the ticket", async ({ page }) => {
  const ticket = await raiseDefect("Me test: open work");
  await moveByApi("technician", ticket.id, "acknowledge");
  await asPerson(page, "technician", "/equipment");
  await openMe(page);

  await expect(tabButton(page, "Open work")).toHaveAttribute("aria-current", "page");
  const row = rowOf(page, ticket.serial);
  await expect(row).toBeVisible();
  await expect(page.getByText(/\d+ open tickets? assigned to you/)).toBeVisible();
  await row.click();
  await expect(page).toHaveURL(new RegExp(`/tickets/${ticket.id}$`));
  await expect(page.getByRole("heading", { name: ticket.serial })).toBeVisible();
});

test("S031: an operator opens Me on Raised by me; a ticket closed as not a fault shows under Closed", async ({ page }) => {
  const ticket = await raiseDefect("Me test: raised by the operator");
  await asPerson(page, "operator", "/equipment");
  await openMe(page);

  await expect(tabButton(page, "Raised by me")).toHaveAttribute("aria-current", "page");
  await expect(rowOf(page, ticket.serial)).toContainText("Raised");

  await moveByApi("engineer", ticket.id, "not-a-fault", { cause_id: await causeId("5.1"), remark: "S031 test: nothing wrong" });
  await page.getByRole("combobox", { name: "State" }).selectOption("closed");
  await expect(page).toHaveURL(/state=closed/);
  await expect(rowOf(page, ticket.serial)).toContainText("Closed · Not a fault");
});

test("S031: My activity shows what the technician recorded, not the operator's Raised line; Back returns to it", async ({ page }) => {
  const ticket = await raiseDefect("Me test: activity");
  await moveByApi("technician", ticket.id, "acknowledge");
  await asPerson(page, "technician", "/equipment");
  await openMe(page);
  await tabButton(page, "My activity").click();
  await expect(page).toHaveURL(/tab=activity/);

  const rows = rowOf(page, ticket.serial);
  await expect(rows.first()).toBeVisible();
  // The assigned line is written after the acknowledged line, so it comes first
  await expect(rows.first()).toContainText("Assigned");
  await expect(rows.locator(".fw-semibold").filter({ hasText: /^Acknowledged$/ })).toHaveCount(1);
  await expect(rows.locator(".fw-semibold").filter({ hasText: /^Raised$/ })).toHaveCount(0);
  await expect(rows.first()).toContainText(`${seed.extruder.code} — ${seed.extruder.name}`);
  // The brief gives no count line on this tab
  await expect(page.getByText(/^\d+ tickets?$/)).toHaveCount(0);

  // A nav tap on Me from this tab goes back to Open work; the console watcher fails the test
  // if the activity items are drawn as ticket rows meanwhile
  await openMe(page);
  await expect(tabButton(page, "Open work")).toHaveAttribute("aria-current", "page");
  await expect(rowOf(page, ticket.serial)).toBeVisible();
  await tabButton(page, "My activity").click();
  await expect(rows.first()).toBeVisible();

  await rows.first().click();
  await expect(page).toHaveURL(new RegExp(`/tickets/${ticket.id}$`));
  await page.goBack();
  await expect(page).toHaveURL(/tab=activity/);
  await expect(tabButton(page, "My activity")).toHaveAttribute("aria-current", "page");
  await expect(rowOf(page, ticket.serial).first()).toBeVisible();
});

test("S031: IT admin has no Team record: Open work says so, and the own raise shows under Raised by me", async ({ page }) => {
  const ticket = await raiseDefect("Me test: raised by IT admin", "it_admin");
  await asPerson(page, "it_admin", "/equipment");
  await openMe(page);

  await expect(tabButton(page, "Open work")).toHaveAttribute("aria-current", "page");
  await expect(page.getByText("You are not in Team. Add yourself in Masters › Team to be assigned tickets.")).toBeVisible();
  await tabButton(page, "Raised by me").click();
  await expect(rowOf(page, ticket.serial)).toBeVisible();
});

test("S035: a technician opening / lands on Me, and Me is the first nav item", async ({ page }) => {
  await asPerson(page, "technician", "/");
  await expect(page).toHaveURL(/\/me(\?|$)/);
  // Bottom bar on a phone, sidebar on desktop: only one of them is visible.
  const firstItem = page.locator(".sidebar-nav .sidebar-btn:visible, .app-bottom-nav .bottom-nav-item:visible").first();
  await expect(firstItem).toHaveAccessibleName("Me");
});

test("S031: the storekeeper has no Me item, and /me lands on Equipment", async ({ page }) => {
  await asPerson(page, "storekeeper", "/equipment");
  await expect(navItem(page, "Me")).toHaveCount(0);
  await page.goto("/me");
  await expect(page).toHaveURL(/\/equipment$/);
});

test("S031: the three tabs fit the screen width", { tag: "@device" }, async ({ page }) => {
  await asPerson(page, "technician", "/me");
  for (const name of ["Open work", "Raised by me", "My activity"]) {
    await expect(tabButton(page, name)).toBeInViewport();
  }
  await expectNoSidewaysScroll(page);
});
