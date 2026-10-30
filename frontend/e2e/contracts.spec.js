// Masters › Contracts (S080, R02.1) — the register of vendor contracts: add and edit in one dialog, the
// call-out number and cost note by role, the status badges and the Status filter, an inactive vendor, a
// deactivated contract, the sites a user reads, and the list on a phone.  The seed has no vendors or contracts:
// each test makes its own by API, named with its tag, and looks for its own rows only.  Dates are relative to
// today (IST), far from the 60-day edge.  The call-out number is obviously fake (D10).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { apiAs, asPerson } from "./support/people.js";
import { propertyTag } from "./support/properties.js";
import { saveDialog } from "./support/tickets.js";

const CALLOUT = "+91 00000 00000";
const IST_OFFSET_MS = 5.5 * 3600 * 1000;

/** Today + `offset` days, in IST, as YYYY-MM-DD (what the API and a date input take). */
function day(offset) {
  return new Date(Date.now() + IST_OFFSET_MS + offset * 86_400_000).toISOString().slice(0, 10);
}

/** YYYY-MM-DD -> DD-MM-YYYY, as the screen shows a date. */
function shown(iso) {
  const [y, m, d] = iso.split("-");
  return `${d}-${m}-${y}`;
}

/** `method` `path` as the seed person `key` with `data` -> the JSON answer (a set-up step must succeed). */
async function callAs(key, method, path, data) {
  const api = await apiAs(key);
  try {
    const res = await api[method](path, data === undefined ? undefined : { data });
    expect(res.ok(), await res.text()).toBe(true);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

const vendorByApi = (name) => callAs("engineer", "post", "/api/masters/vendors", { name });

async function siteId(code) {
  const sites = await callAs("admin", "get", "/api/masters/sites");
  return sites.items.find((s) => s.code === code).id;
}

/** A contract by API as `key` (the manager by default, at SMTW unless site_id is given). */
async function contractByApi(vendor, title, fields = {}, key = "manager") {
  return callAs(key, "post", "/api/contracts", {
    site_id: fields.site_id ?? (await siteId("SMTW")), vendor_id: vendor.id, contract_type: "amc", title,
    from_date: day(-30), to_date: day(300), ...fields,
  });
}

/** Masters › Contracts as the seed person `key`. */
async function openContracts(page, key) {
  await asPerson(page, key, "/masters");
  await page.getByRole("button", { name: "Contracts", exact: true }).click();
  await expect(page.locator(".card-header").filter({ hasText: "Contracts" })).toBeVisible();
}

const row = (page, title) => page.locator("table tbody tr").filter({ hasText: title });

/** Open Add contract and fill the required fields (the engineer's one site is preselected). */
async function fillNewContract(page, vendor, title, { from = day(-10), to = day(355) } = {}) {
  await page.getByRole("button", { name: "Add contract" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Vendor", { exact: true }).selectOption({ label: vendor.name });
  if (title) await dialog.getByLabel("Title").fill(title);
  await dialog.getByLabel("From").fill(from);
  await dialog.getByLabel("To", { exact: true }).fill(to);
  return dialog;
}

test("S080: the engineer adds a contract and sees it In force in Masters › Contracts", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/api/contracts", 400);
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const title = `E2E AMC ${tag}`;
  await openContracts(page, "engineer");
  const dialog = await fillNewContract(page, vendor, "");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Enter a title.");
  await dialog.getByLabel("Title").fill(title);
  await dialog.getByLabel("Labour").check();
  await dialog.getByLabel("PM visits per year").fill("4");
  await dialog.getByLabel("Response time (hours)").fill("24");
  await dialog.getByLabel("Call-out number").fill(CALLOUT);
  await saveDialog(page, "Save");
  const listed = row(page, title);
  await expect(listed).toContainText(vendor.name);
  await expect(listed.locator(".badge").first()).toHaveText("In force");
});

test("S080: a To date before the From date is refused beside the To field", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/api/contracts", 400);
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  await openContracts(page, "engineer");
  const dialog = await fillNewContract(page, vendor, `E2E backwards ${tag}`, { from: day(10), to: day(9) });
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Enter a To date on or after the From date.");
  await expect(dialog.getByLabel("To", { exact: true })).toHaveClass(/is-invalid/);
});

test("S080: the engineer sees the call-out number field and no cost note; the manager sees both", async ({ page }) => {
  await openContracts(page, "engineer");
  await page.getByRole("button", { name: "Add contract" }).click();
  await expectDialogFits(page);
  let dialog = await openDialog(page);
  await expect(dialog.getByLabel("Call-out number")).toBeVisible();
  await expect(dialog.getByLabel("Cost note")).toHaveCount(0);
  await expect(dialog.getByText("Managers only")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);

  await openContracts(page, "manager");
  await page.getByRole("button", { name: "Add contract" }).click();
  await expectDialogFits(page);
  dialog = await openDialog(page);
  await dialog.getByLabel("Site").selectOption(String(await siteId("SMTW")));
  await expect(dialog.getByLabel("Call-out number")).toBeVisible();
  await expect(dialog.getByText("Managers only")).toBeVisible();
  await expect(dialog.getByLabel("Cost note")).toBeVisible();
});

test("S080: IT admin adds a contract without the call-out number or the cost note", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const title = `E2E IT admin ${tag}`;
  await openContracts(page, "it_admin");
  await page.getByRole("button", { name: "Add contract" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Site").selectOption(String(await siteId("SMTW")));
  await dialog.getByLabel("Vendor", { exact: true }).selectOption({ label: vendor.name });
  await dialog.getByLabel("Title").fill(title);
  await dialog.getByLabel("From").fill(day(-10));
  await dialog.getByLabel("To", { exact: true }).fill(day(355));
  await expect(dialog.getByLabel("Call-out number")).toHaveCount(0);
  await expect(dialog.getByLabel("Cost note")).toHaveCount(0);
  await saveDialog(page, "Save");
  await expect(row(page, title)).toContainText(vendor.name);
});

test("S080: the status badges and the Status filter", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const ending = await contractByApi(vendor, `E2E ending ${tag}`, { from_date: day(-300), to_date: day(20) });
  const upcoming = await contractByApi(vendor, `E2E upcoming ${tag}`, { from_date: day(100), to_date: day(400) });
  const ended = await contractByApi(vendor, `E2E ended ${tag}`, { from_date: day(-400), to_date: day(-10) });
  await openContracts(page, "engineer");
  await expect(row(page, ending.title).locator(".badge").first()).toHaveText(/^Ends in \d+ days$/);
  await expect(row(page, upcoming.title).locator(".badge").first()).toHaveText(`Starts on ${shown(day(100))}`);
  await expect(row(page, ended.title)).toHaveCount(0);
  await expect(page.getByText("Ended contracts: choose Ended in Status.")).toBeVisible();

  await page.getByLabel("Status").selectOption({ label: "Ended" });
  await expect(row(page, ended.title).locator(".badge").first()).toHaveText("Ended");
  await expect(row(page, ending.title)).toHaveCount(0);
});

test("S080: an inactive vendor is not offered for a new contract, and its contract shows it as inactive", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const gone = await vendorByApi(`E2E Vendor gone ${tag}`);
  const contract = await contractByApi(gone, `E2E kept ${tag}`);
  await callAs("engineer", "put", `/api/masters/vendors/${gone.id}`, { active: false });
  await openContracts(page, "engineer");
  await page.getByRole("button", { name: "Add contract" }).click();
  await expectDialogFits(page);
  let dialog = await openDialog(page);
  await expect(dialog.getByLabel("Vendor", { exact: true }).locator("option", { hasText: gone.name })).toHaveCount(0);
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);

  await expect(row(page, contract.title)).toContainText(`${gone.name} (inactive)`);
  await row(page, contract.title).getByTitle("Edit").click();
  await expectDialogFits(page);
  dialog = await openDialog(page);
  await expect(dialog.getByLabel("Vendor", { exact: true }).locator("option:checked")).toHaveText(`${gone.name} (inactive)`);
  await dialog.getByLabel("Title").fill(`${contract.title} edited`);
  await saveDialog(page, "Save");
  await expect(row(page, `${contract.title} edited`)).toBeVisible();
});

test("S080: a deactivated contract leaves the list, and Show inactive brings it back", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const contract = await contractByApi(vendor, `E2E to deactivate ${tag}`);
  await openContracts(page, "engineer");
  await row(page, contract.title).getByTitle("Edit").click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByRole("button", { name: "Deactivate" }).click();
  const yes = dialog.getByRole("button", { name: "Yes", exact: true });
  await expect(dialog.getByText(`Deactivate ${contract.title}?`)).toBeVisible();
  await yes.click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(row(page, contract.title)).toHaveCount(0);

  await page.getByLabel("Show inactive").check();
  await expect(row(page, contract.title)).toContainText("Inactive");
});

test("S080: the engineer does not see another site's contract; the manager sees Edit on both", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const bricks = await contractByApi(vendor, `E2E BRICKS ${tag}`, { site_id: await siteId("BRICKS") });
  const smtw = await contractByApi(vendor, `E2E SMTW ${tag}`);
  await openContracts(page, "engineer");
  await expect(row(page, smtw.title)).toBeVisible();
  await expect(row(page, bricks.title)).toHaveCount(0);

  await openContracts(page, "manager");
  await expect(row(page, smtw.title).getByTitle("Edit")).toBeVisible();
  await expect(row(page, bricks.title).getByTitle("Edit")).toBeVisible();
});

test("S080: the Contracts list fits a phone with no sideways scroll", { tag: "@device" }, async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const titles = [];
  for (const [n, to] of [[1, 20], [2, 200], [3, 300]]) {
    titles.push((await contractByApi(vendor, `E2E phone ${n} ${tag}`, { from_date: day(-30), to_date: day(to) })).title);
  }
  await openContracts(page, "engineer");
  for (const title of titles) await expect(row(page, title)).toBeVisible();
  await expectNoSidewaysScroll(page);
  const isPhone = page.viewportSize().width < 768;
  const first = row(page, titles[0]);
  if (isPhone) {
    await expect(page.locator("table thead th", { hasText: "Site" })).toBeHidden();
    await expect(page.locator("table thead th", { hasText: "From" })).toBeHidden();
    await expect(first.locator("td").nth(1).locator(".d-md-none")).toHaveText(`AMC · ${vendor.name} · SMTW`);
  } else {
    await expect(page.locator("table thead th", { hasText: "Site" })).toBeVisible();
    await expect(first.locator("td").nth(3)).toHaveText("SMTW");
  }
});
