// Settings (S064): Save on Network and on Labels asks first, with what the change does (UX-04,
// UX-17); the Database and Background tasks cards are IT's, and a manager sees Removed documents
// first (UX-19); the access log in words (UX-26).
import { test, expect } from "./support/test.js";
import { apiAs, asPerson } from "./support/people.js";

const NETWORK = "/api/settings/network";
const card = (page, title) => page.locator(".card", { has: page.locator(".card-header", { hasText: title }) });

test("S064: Network Save asks first and lists the added and removed ranges; No saves nothing, Yes, save saves", async ({ page }) => {
  const api = await apiAs("admin");
  const stored = (await (await api.get(NETWORK)).json()).networks;
  const extra = "10.99.0.0/16";
  try {
    // Admin: the lock-out guard protects IT admin's own address only (S013 § 5.2), so the test
    // does not depend on the address the e2e server sees
    await asPerson(page, "admin", "/settings");
    const network = card(page, "Network");
    const ranges = network.getByLabel("Plant network ranges");
    await ranges.fill([...stored, extra].join("\n"));
    await network.getByRole("button", { name: "Save", exact: true }).click();
    const confirm = network.locator('[data-test="network-confirm"]');
    await expect(confirm).toContainText("Save these ranges? IT admin outside them will be refused within 5 minutes.");
    await expect(confirm).toContainText(`Added: ${extra}`);
    await expect(confirm).not.toContainText("Removed:");

    await confirm.getByRole("button", { name: "No", exact: true }).click();
    await expect(confirm).toHaveCount(0);
    await expect(ranges).toHaveValue([...stored, extra].join("\n")); // the typed list is kept
    expect((await (await api.get(NETWORK)).json()).networks).toEqual(stored);

    await network.getByRole("button", { name: "Save", exact: true }).click();
    await confirm.getByRole("button", { name: "Yes, save" }).click();
    await expect(network.getByText("Saved", { exact: true })).toBeVisible();
    expect((await (await api.get(NETWORK)).json()).networks).toContain(extra);

    // Taking it out again lists it as removed
    await ranges.fill(stored.join("\n"));
    await network.getByRole("button", { name: "Save", exact: true }).click();
    await expect(confirm).toContainText(`Removed: ${extra}`);
    await confirm.getByRole("button", { name: "Yes, save" }).click();
    await expect(network.getByText("Saved", { exact: true })).toBeVisible();
  } finally {
    await api.put(NETWORK, { data: { networks: stored.join("\n") } });
    await api.dispose();
  }
});

test("S064: Labels Save asks first with the sample link; No keeps the address as stored", async ({ page }) => {
  await asPerson(page, "it_admin", "/settings");
  const labels = card(page, "Labels");
  const address = labels.getByLabel("Label link address");
  const stored = await address.inputValue();
  await address.fill("https://yantra-test.example.test/");
  await labels.getByRole("button", { name: "Save", exact: true }).click();
  const confirm = labels.locator('[data-test="labels-confirm"]');
  await expect(confirm).toContainText(
    "Labels printed from now on will open https://yantra-test.example.test/e/MCC2CMP001. Save?",
  );
  await confirm.getByRole("button", { name: "No", exact: true }).click();
  await expect(confirm).toHaveCount(0);
  await page.reload();
  await expect(card(page, "Labels").getByLabel("Label link address")).toHaveValue(stored);
});

test("S064: a manager's Settings has no Database or Background tasks card and starts with Removed documents; IT admin sees both cards", async ({ page }) => {
  await asPerson(page, "manager", "/settings");
  await expect(card(page, "Removed documents")).toBeVisible();
  await expect(page.locator("main .card").first()).toContainText("Removed documents");
  await expect(card(page, "Uploads")).toBeVisible();
  await expect(card(page, "Database")).toHaveCount(0);
  await expect(card(page, "Background tasks")).toHaveCount(0);

  await asPerson(page, "it_admin", "/settings");
  await expect(card(page, "Database")).toBeVisible();
  await expect(card(page, "Background tasks")).toBeVisible();
  await expect(page.locator("main .card").first()).toContainText("Database");
});

// The e2e backend writes no access log (its test identity skips the hook), so the list is the
// server's answer in the shape of /api/settings/access-log, and the test judges how it is shown
const LOG_ROW = { client_ip: "10.24.1.5", is_internal: true, method: "GET", user_agent: null, ts: "2026-10-28T09:00:00" };
const ACCESS_LOG = {
  page: 1, per_page: 50, total: 3,
  items: [
    { ...LOG_ROW, id: 3, username: "e2e_operator", role: "maint_operator", outcome: "denied_perm", detail: "settings:read", path: "/api/settings/app" },
    { ...LOG_ROW, id: 2, username: "e2e_engineer", role: "maint_engineer", outcome: "denied_network", detail: "Your role can use Yantra only on the plant network.", path: "/api/tickets" },
    { ...LOG_ROW, id: 1, username: "e2e_it_admin", role: "it_admin", outcome: "ok", detail: null, path: "/api/auth/me" },
  ],
};

test("S064: the access log shows Allowed, a role by its name, and Needed: <key> on a refusal", async ({ page }) => {
  await page.route("**/api/settings/access-log?**", (route) => route.fulfill({ json: ACCESS_LOG }));
  await asPerson(page, "it_admin", "/settings");
  const log = card(page, "Access log");
  const refused = log.locator("tbody tr", { hasText: "e2e_operator" });
  await expect(refused).toContainText("Refused: permission");
  await expect(refused).toContainText("Needed: settings:read");
  await expect(refused).toContainText("Operator");
  await expect(refused).not.toContainText("maint_operator");
  // A refusal's own text is not a key: shown as it is
  const network = log.locator("tbody tr", { hasText: "e2e_engineer" });
  await expect(network).toContainText("Your role can use Yantra only on the plant network.");
  await expect(network).not.toContainText("Needed:");
  await expect(network).toContainText("Engineer");
  const allowed = log.locator("tbody tr", { hasText: "e2e_it_admin" });
  await expect(allowed).toContainText("Allowed");
  await expect(allowed).toContainText("IT admin");
  await expect(log).not.toContainText("Let in");
});
