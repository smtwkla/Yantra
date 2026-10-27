// Every screen opens (S024 § 1.4): each route of router/index.js, for each role that can reach
// it, shows its heading with no console error, Vue warning or uncaught error (test.js), and
// is not blank.  The test that would have caught S017's blank raise screen and S018 CR1-01's
// dialogs.
import { test, expect } from "./support/test.js";
import { apiAs, asPerson, seedIds } from "./support/people.js";

const EVERYONE = ["operator", "supervisor", "technician", "engineer", "manager", "storekeeper", "it_admin"];
// ticket:read and ticket:raise: every site role but the storekeeper, and IT admin (config_rbac)
const TICKET_ROLES = EVERYONE.filter((key) => key !== "storekeeper");
const SETTINGS_ROLES = ["manager", "it_admin"];
// S064 UX-12: Masters is for the holders of an edit key on masters data
const MASTERS_ROLES = ["engineer", "manager", "it_admin"];

let seed;
let ticket;

test.beforeAll(async () => {
  seed = await seedIds();
  const operator = await apiAs("operator");
  const res = await operator.post("/api/tickets", {
    data: { equipment_id: seed.extruder.id, intensity: "degraded", description: "Screens test: oil seeping" },
  });
  expect(res.status()).toBe(201);
  ticket = await res.json();
  await operator.dispose();
});

/** The visible top bar's title (route meta.title): the screen's heading on every page. */
function topbarTitle(page) {
  return page.locator(".topbar-center").filter({ visible: true });
}

// path, title in the top bar, what else must show (given the page and the role), who may open it
const screens = () => [
  // S064: the search shows on every width (Print asset list is the office's, from md up)
  { path: "/equipment", title: "Equipment", shows: (page) => page.getByRole("searchbox", { name: "Search" }), who: EVERYONE },
  {
    path: `/equipment/${seed.extruder.id}`, title: "Equipment",
    shows: (page) => page.getByRole("heading", { name: `${seed.extruder.code} — ${seed.extruder.name}` }), who: EVERYONE,
  },
  {
    // The QR label's link (S014) lands on the equipment page
    path: `/e/${seed.extruder.code}`, title: "Equipment",
    shows: (page) => page.getByRole("heading", { name: `${seed.extruder.code} — ${seed.extruder.name}` }), who: EVERYONE,
  },
  { path: "/tickets", title: "Tickets", shows: (page) => page.getByRole("combobox", { name: "State" }), who: TICKET_ROLES },
  // S031: the My activity tab is there for every role, whatever its default tab
  // S040: the site heading (code first) for a one-site user, the site picker for the manager; both hold with
  // no meters in the lane's database (empty state, BR1-12).  S050: every role opens it; the storekeeper and
  // IT admin (no reading:log) get only the Register tab, with the equipment search
  {
    path: "/readings", title: "Readings", who: EVERYONE,
    shows: (page, key) => {
      if (["storekeeper", "it_admin"].includes(key)) return page.getByLabel("Which equipment?");
      return key === "manager"
        ? page.getByLabel("Site", { exact: true })
        : page.getByTestId("sheet-heading").filter({ hasText: "SMTW — " });
    },
  },
  { path: "/me", title: "Me", shows: (page) => page.getByRole("button", { name: "My activity", exact: true }), who: TICKET_ROLES },
  { path: "/tickets/new", title: "Raise ticket", shows: (page) => page.getByRole("heading", { name: "Raise ticket" }), who: TICKET_ROLES },
  {
    path: `/tickets/new?equipment=${seed.extruder.id}`, title: "Raise ticket",
    shows: (page) => page.getByRole("button", { name: /Stopped/ }), who: TICKET_ROLES,
  },
  {
    path: `/tickets/${ticket.id}`, title: "Ticket",
    shows: (page) => page.getByRole("heading", { name: ticket.serial }), who: TICKET_ROLES,
  },
  { path: `/labels?ids=${seed.extruder.id}&parts=1`, title: "QR labels", shows: (page) => page.getByText("2 labels on 1 sheet"), who: EVERYONE },
  { path: "/asset-list", title: "Asset list", shows: (page) => page.getByRole("heading", { name: "SMTW.MCC2", exact: false }), who: EVERYONE },
  { path: "/masters", title: "Masters", shows: (page) => page.getByRole("button", { name: "Sites" }), who: MASTERS_ROLES },
  // S064 UX-19: a card every settings role sees (Database is IT's alone now)
  { path: "/settings", title: "Settings", shows: (page) => page.getByText("Removed documents").first(), who: SETTINGS_ROLES },
  // S021: push:subscribe is every role's ('*'); the card shows for every state of the device
  {
    path: "/notifications", title: "My notifications",
    shows: (page) => page.getByText("This device", { exact: true }).first(), who: EVERYONE,
  },
  { path: "/no-such-page", title: "Page not found", shows: (page) => page.getByRole("heading", { name: "Page not found" }), who: EVERYONE },
];

for (const key of EVERYONE) {
  test(`every screen opens as ${key}`, { tag: ["@smoke", "@device"] }, async ({ page }) => {
    await asPerson(page, key);
    for (const screen of screens().filter((s) => s.who.includes(key))) {
      await test.step(screen.path, async () => {
        await page.goto(screen.path);
        await expect(topbarTitle(page)).toHaveText(screen.title);
        await expect(screen.shows(page, key)).toBeVisible();
        await expect(page.locator("main.app-content")).not.toBeEmpty();
      });
    }
  });
}

test("a request that lost its test headers gets no access, never admin", { tag: ["@smoke", "@device"] }, async ({ page }) => {
  // No asPerson: the e2e backend's stub user is "nobody" (S024 § 5.1)
  const meResponse = page.waitForResponse((r) => r.url().endsWith("/api/auth/me"));
  await page.goto("/");
  const me = await (await meResponse).json();
  expect(me.permissions).toEqual([]);
  expect(me.roles).toEqual([]);
  await expect(page.getByText("You have no access yet")).toBeVisible();
});

// S040 (S039 BR1-14): the manager has six nav items; on a phone the bottom bar shows them all, inside the screen
test("S040: the manager's bottom bar shows all six items without sideways scroll", { tag: ["@smoke", "@device"] }, async ({ page }) => {
  await asPerson(page, "manager");
  const nav = page.locator(".app-bottom-nav");
  test.skip(!(await nav.isVisible()), "the bottom bar is a phone screen");
  const items = nav.locator(".bottom-nav-item");
  await expect(items).toHaveText(["Me", "Equipment", "Tickets", "Readings", "Masters", "Settings"]);
  const viewport = page.viewportSize();
  for (const box of await Promise.all((await items.all()).map((item) => item.boundingBox()))) {
    expect(box.x, "an item starts left of the screen").toBeGreaterThanOrEqual(0);
    expect(box.x + box.width, "an item ends right of the screen").toBeLessThanOrEqual(viewport.width + 1);
  }
  const overflow = await nav.evaluate((el) => el.scrollWidth - el.clientWidth);
  expect(overflow, "the bottom bar scrolls sideways").toBeLessThanOrEqual(1);
});
