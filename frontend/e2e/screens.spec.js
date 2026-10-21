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

// path, title in the top bar, what else must show, who may open it
const screens = () => [
  { path: "/equipment", title: "Equipment", shows: (page) => page.getByRole("button", { name: /Print asset list/ }), who: EVERYONE },
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
  { path: "/masters", title: "Masters", shows: (page) => page.getByRole("button", { name: "Sites" }), who: EVERYONE },
  { path: "/settings", title: "Settings", shows: (page) => page.getByText("Database", { exact: true }).first(), who: SETTINGS_ROLES },
  { path: "/no-such-page", title: "Page not found", shows: (page) => page.getByRole("heading", { name: "Page not found" }), who: EVERYONE },
];

for (const key of EVERYONE) {
  test(`every screen opens as ${key}`, async ({ page }) => {
    await asPerson(page, key);
    for (const screen of screens().filter((s) => s.who.includes(key))) {
      await test.step(screen.path, async () => {
        await page.goto(screen.path);
        await expect(topbarTitle(page)).toHaveText(screen.title);
        await expect(screen.shows(page)).toBeVisible();
        await expect(page.locator("main.app-content")).not.toBeEmpty();
      });
    }
  });
}

test("a request that lost its test headers gets no access, never admin", async ({ page }) => {
  // No asPerson: the e2e backend's stub user is "nobody" (S024 § 5.1)
  const meResponse = page.waitForResponse((r) => r.url().endsWith("/api/auth/me"));
  await page.goto("/");
  const me = await (await meResponse).json();
  expect(me.permissions).toEqual([]);
  expect(me.roles).toEqual([]);
  await expect(page.getByText("You have no access yet")).toBeVisible();
});
