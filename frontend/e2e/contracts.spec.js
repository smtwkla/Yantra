// Masters › Contracts (S080, R02.1) — the register of vendor contracts: add and edit in one dialog, the
// call-out number and cost note by role, the status badges and the Status filter, an inactive vendor, a
// deactivated contract, the sites a user reads, and the list on a phone.  The contract page (S081, R02.2): the
// machines covered, Add machine, the price per machine and the total for the manager only, Remove, the overlap
// of two AMCs, the machine's history lines, and Cost before GST in the list; each S081 test makes its own
// machines by API (as equipment.spec.js's createEquipment).  The seed has no vendors or contracts:
// each test makes its own by API, named with its tag, and looks for its own rows only.  Dates are relative to
// today (IST), far from the 60-day edge.  The call-out number is obviously fake (D10).  Under contract on the
// machine (S082): the card on the equipment page (Do not repair, the call-out number as a tel: link by role, the
// machine's contract on its part, an ended contract, the empty card, the place before Open tickets) and the list's
// Contract filter; each test makes its own machines, so other tests' contracts never show on its card.  The
// contract's documents (S083): a manager adds a PDF, removes it and restores it from Settings; an engineer sees
// no Documents card.  Contract renewal (S085): Renew contract, its notice, the chain lines on both pages, an
// inactive vendor, a scrapped machine and an inactive renewal.  Breakdown calls (S086): the vendor's tickets on
// the contract page with their downtime and the wait on the vendor, the calls used, the two warnings, the rows by
// the reader's units, the contract line and Do not repair on the ticket page, and the vendor in the people picker;
// each test makes its own Team records of its own vendor and never links a seed person.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { equipmentRow, openFilters } from "./support/equipmentList.js";
import { writeLessonByApi } from "./support/lessons.js";
import { apiAs, asPerson, personId } from "./support/people.js";
import { propertyTag } from "./support/properties.js";
import { card, causeId, istDay, istLocal, moveByApi, raiseByApi, saveDialog, thisMinute } from "./support/tickets.js";

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

// ---------------------------------------------------------------------------
// The machines on a contract (S081)
// ---------------------------------------------------------------------------

/** A machine by API as IT admin, in the unit `unitCode` (a GA37 compressor) -> the node. */
async function machineByApi(name, unitCode = "SMTW.MCC1") {
  const units = await callAs("admin", "get", "/api/masters/units");
  const models = await callAs("admin", "get", "/api/masters/equipment-models");
  return callAs("admin", "post", "/api/equipment", {
    level: "equipment", unit_id: units.items.find((u) => u.full_code === unitCode).id,
    model_id: models.items.find((m) => m.label === "Atlas Copco GA37").id, name,
  });
}

/** A machine line by API (the manager, so a price is kept). */
const lineByApi = (contract, machine, price = null) =>
  callAs("manager", "post", `/api/contracts/${contract.id}/equipment`, { equipment_id: machine.id, price });

/** The tag's vendor, an AMC at SMTW and one machine, on it unless `onIt` is false. */
async function contractWithMachine(testInfo, { onIt = true, price = null } = {}) {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const contract = await contractByApi(vendor, `E2E AMC ${tag}`);
  const machine = await machineByApi(`E2E compressor ${tag}`);
  if (onIt) await lineByApi(contract, machine, price);
  return { tag, vendor, contract, machine };
}

const machinesCard = (page) => page.getByTestId("contract-machines");
const machineLine = (page, machine) => machinesCard(page).getByTestId("contract-machine").filter({ hasText: machine.code });
const historyText = (contract) => `${contract.title} (AMC, ${shown(day(-30))} to ${shown(day(300))})`;

test("S081: the engineer adds a machine to a contract; the page lists it and the machine's history shows the line", async ({ page }, testInfo) => {
  const { contract, machine } = await contractWithMachine(testInfo, { onIt: false });
  await asPerson(page, "engineer", `/contracts/${contract.id}`);
  await expect(page.getByRole("heading", { name: contract.title })).toBeVisible();
  await expect(machinesCard(page)).toContainText("No machines on this contract yet. Add the first one with Add machine.");
  await machinesCard(page).getByRole("button", { name: "Add machine" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.locator(".modal-footer")).toContainText("Choose a machine");
  await dialog.getByLabel("Which equipment?").fill(machine.name);
  await dialog.locator(".list-group-item", { hasText: machine.name }).click();
  await expect(dialog.getByTestId("picked-machine")).toContainText(`${machine.code} — ${machine.name}`);
  await saveDialog(page, "Add machine");
  const line = machineLine(page, machine);
  await expect(line).toContainText(`${machine.code} — ${machine.name}`);
  await expect(machinesCard(page).locator(".card-header")).toContainText("Machines covered (1)");
  await line.getByRole("link", { name: `${machine.code} — ${machine.name}` }).click();
  await expect(card(page, "History")).toContainText(`Added to contract: ${historyText(contract)}`);
});

test("S081: the manager enters a price per machine and sees the total; the engineer sees no price", async ({ page }, testInfo) => {
  const { contract, machine } = await contractWithMachine(testInfo);
  await asPerson(page, "manager", `/contracts/${contract.id}`);
  const line = machineLine(page, machine);
  await expect(line.getByTestId("line-price")).toHaveText("No price");
  await expect(page.getByTestId("contract-total")).toHaveText("No prices entered yet.");
  await line.getByRole("button", { name: "Edit price" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.locator(".modal-title")).toHaveText(`Edit price — ${machine.code}`);
  await dialog.getByLabel("Price (₹, before GST)").fill("9809");
  await saveDialog(page, "Save price");
  await expect(line.getByTestId("line-price")).toHaveText("₹9,809");
  await expect(page.getByTestId("contract-total")).toHaveText("Total: ₹9,809 before GST · 1 of 1 machines priced.");

  await asPerson(page, "engineer", `/contracts/${contract.id}`);
  await expect(machineLine(page, machine)).toBeVisible();
  await expect(page.getByTestId("line-price")).toHaveCount(0);
  await expect(page.getByTestId("contract-total")).toHaveCount(0);
  await expect(machineLine(page, machine).getByRole("button", { name: "Edit price" })).toHaveCount(0);
  await machinesCard(page).getByRole("button", { name: "Add machine" }).click();
  await expectDialogFits(page);
  const engineerDialog = await openDialog(page);
  await expect(engineerDialog.getByLabel("Which equipment?")).toBeVisible();
  await expect(engineerDialog.getByLabel("Price (₹, before GST)")).toHaveCount(0);
});

test("S081: a machine of another site is not offered in Add machine", async ({ page }, testInfo) => {
  const { tag, contract } = await contractWithMachine(testInfo, { onIt: false });
  const bricks = await machineByApi(`E2E BRICKS pump ${tag}`, "BRICKS.FILTER");
  // The manager holds both sites, so only the contract's site keeps the BRICKS machine out
  await asPerson(page, "manager", `/contracts/${contract.id}`);
  await machinesCard(page).getByRole("button", { name: "Add machine" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Which equipment?").fill(bricks.name);
  await expect(dialog.getByText("No machine of SMTW matches.")).toBeVisible();
  await expect(dialog.locator(".list-group-item", { hasText: bricks.name })).toHaveCount(0);
});

test("S081: Remove asks first; the machine leaves the contract page and its history shows the line", async ({ page }, testInfo) => {
  const { contract, machine } = await contractWithMachine(testInfo, { price: "9809" });
  await asPerson(page, "engineer", `/contracts/${contract.id}`);
  const line = machineLine(page, machine);
  await line.getByRole("button", { name: "Remove" }).click();
  await expect(line).toContainText(`Remove ${machine.code} from this contract? Its history keeps the line.`);
  await line.getByRole("button", { name: "Keep" }).click();
  await expect(line).not.toContainText("from this contract?");
  await line.getByRole("button", { name: "Remove" }).click();
  await expect(line.getByRole("button", { name: "Keep" })).toBeVisible();
  await line.getByRole("button", { name: "Remove" }).click(); // the question's Remove: the row's own button is gone
  await expect(machineLine(page, machine)).toHaveCount(0);
  await expect(machinesCard(page)).toContainText("No machines on this contract yet.");
  await asPerson(page, "engineer", `/equipment/${machine.id}`);
  await expect(card(page, "History")).toContainText(`Removed from contract: ${historyText(contract)}`);
});

test("S081: a second AMC on the same machine shows the overlap line on both contract pages", async ({ page }, testInfo) => {
  const { vendor, contract, machine, tag } = await contractWithMachine(testInfo);
  const second = await contractByApi(vendor, `E2E second AMC ${tag}`, { from_date: day(100), to_date: day(500) });
  await lineByApi(second, machine);
  await asPerson(page, "engineer", `/contracts/${contract.id}`);
  await expect(machineLine(page, machine).getByTestId("overlap")).toHaveText(
    `Also in another AMC: ${second.title}, ${shown(day(100))} to ${shown(day(500))}.`);
  await asPerson(page, "engineer", `/contracts/${second.id}`);
  await expect(machineLine(page, machine).getByTestId("overlap")).toHaveText(
    `Also in another AMC: ${contract.title}, ${shown(day(-30))} to ${shown(day(300))}.`);
});

test("S081: Masters › Contracts shows Cost before GST to the manager only, and the title opens the contract page", async ({ page }, testInfo) => {
  const { contract } = await contractWithMachine(testInfo, { price: "28028" });
  await openContracts(page, "engineer");
  await expect(row(page, contract.title)).toBeVisible();
  await expect(page.locator("table thead th", { hasText: "Cost before GST" })).toHaveCount(0);
  await expect(row(page, contract.title)).not.toContainText("₹");

  await openContracts(page, "manager");
  await expect(page.locator("table thead th", { hasText: "Cost before GST" })).toHaveCount(1);
  // The column shows from the md width; on a phone its cell is in the page but hidden
  await expect(row(page, contract.title).locator("td").filter({ hasText: "₹" })).toHaveText("₹28,028");
  await row(page, contract.title).getByRole("link", { name: contract.title }).click();
  await expect(page).toHaveURL(new RegExp(`/contracts/${contract.id}$`));
  await expect(page.getByRole("heading", { name: contract.title })).toBeVisible();
  await expect(page.getByTestId("contract-total")).toHaveText("Total: ₹28,028 before GST · 1 of 1 machines priced.");
});

test("S081: the contract page with its machines fits a phone with no sideways scroll", { tag: "@device" }, async ({ page }, testInfo) => {
  const { tag, contract, machine } = await contractWithMachine(testInfo, { price: "9809.50" });
  for (const n of [2, 3]) await lineByApi(contract, await machineByApi(`E2E compressor ${n} ${tag}`), "18040");
  await asPerson(page, "manager", `/contracts/${contract.id}`);
  await expect(machinesCard(page).getByTestId("contract-machine")).toHaveCount(3);
  await expect(machineLine(page, machine).getByTestId("line-price")).toHaveText("₹9,809.50");
  await expect(page.getByTestId("contract-total")).toHaveText("Total: ₹45,889.50 before GST · 3 of 3 machines priced.");
  await expectNoSidewaysScroll(page);
});

// ---------------------------------------------------------------------------
// Under contract on the machine (S082): the card on the equipment page and the list's Contract filter
// ---------------------------------------------------------------------------

const DO_NOT_REPAIR = "Do not repair. Call the engineer; the vendor repairs this machine.";
const ASK_THE_ENGINEER = "To call the vendor, ask the engineer.";
const contractCard = (page) => page.getByTestId("contract-card");
const cardItem = (page, contract) => contractCard(page).locator(`[data-contract="${contract.id}"]`);

/**
 * Open the node's page as `key` and wait for the card's answer, so a test that expects no card is not passing
 * before the answer is in.
 */
async function openNodeAs(page, key, node) {
  await asPerson(page, key);
  const answered = page.waitForResponse((r) => r.url().includes(`/api/contracts/for-equipment/${node.id}`));
  await page.goto(`/equipment/${node.id}`);
  await answered;
  await expect(page.getByRole("heading", { name: `${node.code} — ${node.name}` })).toBeVisible();
}

/** A component-unit of `machine` by API as IT admin -> the node. */
const partByApi = (machine, name) => callAs("admin", "post", "/api/equipment", {
  level: "component_unit", parent_id: machine.id, model_id: machine.model_id, name,
});

test("S082: a technician sees the Under contract card with Do not repair and no number; the engineer sees the call-out number as a call link", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const vendorOnly = await contractByApi(vendor, `E2E AMC ${tag}`, { only_vendor_repairs: true, callout_number: CALLOUT,
    response_hours: 24, covers_labour: true, covers_breakdown_calls: true, breakdown_calls_per_year: 4 });
  const machine = await machineByApi(`E2E compressor ${tag}`);
  await lineByApi(vendorOnly, machine);
  const plain = await contractByApi(vendor, `E2E plain AMC ${tag}`, { callout_number: CALLOUT });
  const second = await machineByApi(`E2E compressor 2 ${tag}`);
  await lineByApi(plain, second);

  await openNodeAs(page, "technician", machine);
  const item = cardItem(page, vendorOnly);
  await expect(contractCard(page).locator(".card-header")).toHaveText("Under contract");
  await expect(item.getByRole("alert")).toHaveText(DO_NOT_REPAIR);
  await expect(item).toContainText(`Under AMC with ${vendor.name} until ${shown(day(300))}`);
  await expect(item).toContainText("Response time: 24 hours");
  await expect(item).toContainText("Covered: labour, breakdown calls (4 a year).");
  await expect(item).toContainText("Not covered: spare parts, consumables.");
  await expect(item).not.toContainText(CALLOUT);
  await expect(item).not.toContainText(ASK_THE_ENGINEER); // the warning already says to call the engineer
  await openNodeAs(page, "technician", second);
  await expect(cardItem(page, plain)).toContainText(ASK_THE_ENGINEER);
  await expect(cardItem(page, plain).getByRole("alert")).toHaveCount(0);

  await openNodeAs(page, "engineer", machine);
  await expect(item.getByRole("alert")).toHaveText(DO_NOT_REPAIR);
  const call = item.getByRole("link", { name: CALLOUT });
  await expect(call).toHaveAttribute("href", "tel:+910000000000");
  expect((await call.boundingBox()).height).toBeGreaterThanOrEqual(44); // a gloved thumb (CR1-01)
  await expect(item).toContainText(`Call-out number: ${CALLOUT}`);
  await item.getByRole("link", { name: "Open contract" }).click();
  await expect(page).toHaveURL(new RegExp(`/contracts/${vendorOnly.id}$`));
  await expect(page.getByRole("heading", { name: vendorOnly.title })).toBeVisible();
});

test("S082: the Under contract card comes before Open tickets", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const contract = await contractByApi(vendor, `E2E AMC ${tag}`, { only_vendor_repairs: true });
  const machine = await machineByApi(`E2E compressor ${tag}`, "SMTW.MCC2");
  await lineByApi(contract, machine);
  await raiseByApi("operator", { equipment_id: machine.id, intensity: "degraded", description: `S082 order: ticket ${tag}` });
  await openNodeAs(page, "technician", machine);
  const tickets = page.locator(".card-header", { hasText: /^\s*Open tickets/ });
  await expect(tickets).toBeVisible();
  const contractY = (await contractCard(page).boundingBox()).y;
  expect(contractY, "the Under contract card is below Open tickets").toBeLessThan((await tickets.boundingBox()).y);

  await writeLessonByApi(machine, { title: `S082 order: keep the guard on ${tag}` });
  await openNodeAs(page, "technician", machine);
  await expect(page.getByTestId("lessons-card")).toBeVisible();
  const lessonsY = (await page.getByTestId("lessons-card").boundingBox()).y;
  const cardY = (await contractCard(page).boundingBox()).y;
  expect(lessonsY, "the Lessons card is below Under contract").toBeLessThan(cardY);
  expect(cardY, "the Under contract card is below Open tickets").toBeLessThan((await tickets.boundingBox()).y);
});

test("S082: a contract on a machine shows on its part's card, naming the machine", async ({ page }, testInfo) => {
  const { tag, vendor, contract, machine } = await contractWithMachine(testInfo);
  const part = await partByApi(machine, `E2E motor ${tag}`);
  await openNodeAs(page, "technician", part);
  const item = cardItem(page, contract);
  await expect(item).toContainText(`Under AMC with ${vendor.name} until ${shown(day(300))}`);
  await expect(item).toContainText(`Through ${machine.code} — ${machine.name}, this part's machine.`);
});

test("S082: an ended contract shows on the card as ended, with no warning", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const contract = await contractByApi(vendor, `E2E ended AMC ${tag}`, {
    from_date: day(-400), to_date: day(-10), only_vendor_repairs: true, callout_number: CALLOUT });
  const machine = await machineByApi(`E2E compressor ${tag}`);
  await lineByApi(contract, machine);
  await openNodeAs(page, "engineer", machine);
  const item = cardItem(page, contract);
  await expect(item).toContainText(`AMC with ${vendor.name} ended on ${shown(day(-10))}.`);
  await expect(item).toHaveClass(/text-secondary/);
  await expect(item.getByRole("alert")).toHaveCount(0);
  await expect(item).not.toContainText(CALLOUT);
  await expect(item.getByRole("link", { name: "Open contract" })).toBeVisible();
});

test("S082: the engineer sees No contract on this machine; the operator sees no card", async ({ page }, testInfo) => {
  const machine = await machineByApi(`E2E compressor ${propertyTag(testInfo)}`, "SMTW.MCC2");
  await openNodeAs(page, "engineer", machine);
  await expect(contractCard(page)).toContainText("No contract on this machine.");
  await openNodeAs(page, "operator", machine);
  await expect(contractCard(page)).toHaveCount(0);
});

test("S082: a machine removed from its contract loses the card", async ({ page }, testInfo) => {
  const { contract, machine } = await contractWithMachine(testInfo);
  await openNodeAs(page, "technician", machine);
  await expect(cardItem(page, contract)).toBeVisible();
  await callAs("engineer", "delete", `/api/contracts/${contract.id}/equipment/${machine.id}`);
  await openNodeAs(page, "technician", machine);
  await expect(contractCard(page)).toHaveCount(0);
});

test("S082: Under contract and Not under contract filter the equipment list", async ({ page }, testInfo) => {
  const { tag, machine } = await contractWithMachine(testInfo);
  const other = await machineByApi(`E2E compressor 2 ${tag}`);
  await asPerson(page, "engineer", `/equipment?q=${encodeURIComponent(tag)}`);
  await expect(equipmentRow(page, machine)).toBeVisible();
  await expect(equipmentRow(page, other)).toBeVisible();
  await openFilters(page);
  const select = page.getByRole("combobox", { name: "Contract" });
  await select.selectOption({ label: "Under contract" });
  await expect(page).toHaveURL(/contract=under/);
  await expect(equipmentRow(page, machine)).toBeVisible();
  await expect(equipmentRow(page, other)).toHaveCount(0);
  await select.selectOption({ label: "Not under contract" });
  await expect(page).toHaveURL(/contract=not_under/);
  await expect(equipmentRow(page, other)).toBeVisible();
  await expect(equipmentRow(page, machine)).toHaveCount(0);
  await select.selectOption({ label: "Any contract status" });
  await expect(page).not.toHaveURL(/contract=/);
  await expect(equipmentRow(page, machine)).toBeVisible();
});

test("S082: the Under contract card with its warning fits a phone with no sideways scroll", { tag: "@device" }, async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor with a long name for the phone ${tag}`);
  const contract = await contractByApi(vendor, `E2E AMC ${tag}`, { only_vendor_repairs: true, response_hours: 48,
    covers_labour: true, covers_consumables: true, covers_breakdown_calls: true, breakdown_calls_per_year: 12 });
  const machine = await machineByApi(`E2E compressor ${tag}`);
  await lineByApi(contract, machine);
  await openNodeAs(page, "technician", machine);
  await expect(cardItem(page, contract).getByRole("alert")).toHaveText(DO_NOT_REPAIR);
  await expectNoSidewaysScroll(page);
});

// ---------------------------------------------------------------------------
// The contract's documents (S083, R02.3): the signed contract, its annexures and the quotes on the contract page,
// for the site's managers only (contract:read_senior).  Each test makes its own contract, so its Documents card
// holds only its own files.
// ---------------------------------------------------------------------------

const MANUAL = path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", "test-manual.pdf");
const SIGNED_LINE = "Only the managers of SMTW see these documents and photos.";

const documentsCard = (page) =>
  page.locator(".card", { has: page.locator(".card-header", { hasText: /^\s*Documents/ }) });

/** A contract at SMTW by API, named with the test's tag. */
async function contractForDocuments(testInfo, label) {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${label} ${tag}`);
  return contractByApi(vendor, `E2E AMC ${label} ${tag}`);
}

/** The test PDF uploaded to the contract by API as the manager -> the document. */
async function contractPdfByApi(contract, title) {
  const api = await apiAs("manager");
  try {
    const res = await api.post(`/api/contracts/${contract.id}/documents`, {
      multipart: { kind: "document", title, file: { name: "test-manual.pdf", mimeType: "application/pdf", buffer: fs.readFileSync(MANUAL) } },
    });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

test("S083: a manager adds the signed contract as a PDF and sees it in Documents", async ({ page }, testInfo) => {
  const contract = await contractForDocuments(testInfo, "signed");
  await asPerson(page, "manager", `/contracts/${contract.id}`);
  await expect(page.getByText(SIGNED_LINE)).toBeVisible();
  await expect(documentsCard(page)).toContainText("No documents yet.");
  await page.getByRole("button", { name: "Add document" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("File").setInputFiles(MANUAL);
  await dialog.getByLabel("Title").fill("Signed contract");
  await saveDialog(page, "Upload");
  await expect(documentsCard(page)).toContainText("Signed contract");
  await expect(documentsCard(page)).toContainText("test-manual.pdf");
});

test("S083: a manager removes a contract document and restores it from Settings", async ({ page }, testInfo) => {
  const contract = await contractForDocuments(testInfo, "restore");
  await contractPdfByApi(contract, "Fuji AMC quote");
  await asPerson(page, "manager", `/contracts/${contract.id}`);
  const documents = documentsCard(page);
  await expect(documents).toContainText("Fuji AMC quote");
  await documents.getByRole("button", { name: "More actions" }).click();
  await documents.getByRole("button", { name: "Remove" }).click();
  await expect(documents.getByText("Remove this document?")).toBeVisible();
  await documents.getByRole("button", { name: "Yes", exact: true }).click();
  await expect(documents).toContainText("No documents yet.");

  await page.goto("/settings");
  await page.getByRole("searchbox", { name: "Search removed documents" }).fill(contract.title);
  const removed = page.locator("tr", { hasText: "Fuji AMC quote" });
  await expect(removed).toContainText(`Contract ${contract.title}`);
  await expect(removed).toContainText("SMTW");
  await removed.getByRole("button", { name: "Restore" }).click();
  await expect(page.getByText("Restored 'Fuji AMC quote'.")).toBeVisible();
  await expect(removed).toHaveCount(0);

  await page.goto(`/contracts/${contract.id}`);
  await expect(documentsCard(page)).toContainText("Fuji AMC quote");
});

test("S083: an engineer sees no Documents card on the contract page", async ({ page }, testInfo) => {
  const contract = await contractForDocuments(testInfo, "engineer");
  await asPerson(page, "engineer", `/contracts/${contract.id}`);
  await expect(page.getByRole("heading", { name: contract.title })).toBeVisible();
  await expect(machinesCard(page)).toBeVisible();
  await expect(page.getByRole("button", { name: "Add document" })).toHaveCount(0);
  await expect(page.locator(".card-header", { hasText: /^\s*Documents/ })).toHaveCount(0);
  await expect(page.getByText(SIGNED_LINE)).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// Contract renewal (S085, R02.4): Renew contract on the contract page makes the next contract with the same terms
// and machines; prices and the cost note start empty; the chain shows on both pages.  The old contract runs from
// 300 days ago to 65 days ahead; each test makes its own vendor, contract and machines.
// ---------------------------------------------------------------------------

const RENEW_FROM = -300;
const RENEW_TO = 65;
const WAY_OUT = "To renew this contract again, set that renewal active in Masters › Contracts and change its terms.";
const chain = (page) => page.getByTestId("contract-chain");
const renewButton = (page) => page.getByRole("button", { name: "Renew contract" });

/** The tag's vendor, an AMC at SMTW from 300 days ago to 65 days ahead, and `machines` machines on it. */
async function contractToRenew(testInfo, { machines = 0, price = null } = {}) {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const contract = await contractByApi(vendor, `E2E AMC ${tag} 2026–27`, { from_date: day(RENEW_FROM), to_date: day(RENEW_TO) });
  const nodes = [];
  for (let n = 1; n <= machines; n += 1) {
    const machine = await machineByApi(`E2E compressor ${tag} ${n}`);
    await lineByApi(contract, machine, price);
    nodes.push(machine);
  }
  return { tag, vendor, contract, machines: nodes };
}

/** A renewal by API as the engineer, with the terms and the proposed dates -> its detail. */
async function renewByApi(contract, title) {
  const detail = await callAs("engineer", "get", `/api/contracts/${contract.id}`);
  return callAs("engineer", "post", `/api/contracts/${contract.id}/renew`, {
    vendor_id: detail.vendor_id, contract_type: detail.contract_type, title,
    from_date: detail.renewal.from_date, to_date: detail.renewal.to_date,
  });
}

/** Open Renew contract on the contract page -> the dialog. */
async function openRenew(page) {
  await renewButton(page).click();
  await expectDialogFits(page);
  return openDialog(page);
}

test("S085: the engineer renews a contract; the new contract opens with its terms and machines, and the chain shows on both pages", async ({ page }, testInfo) => {
  const { contract, vendor, machines } = await contractToRenew(testInfo, { machines: 2 });
  const offer = (await callAs("engineer", "get", `/api/contracts/${contract.id}`)).renewal;
  await asPerson(page, "engineer", `/contracts/${contract.id}`);
  const dialog = await openRenew(page);
  await expect(dialog.locator(".modal-title")).toHaveText(`Renew contract — ${contract.title}`);
  await expect(dialog.getByLabel("Title")).toHaveValue(contract.title);
  await expect(dialog.getByLabel("Vendor", { exact: true }).locator("option:checked")).toHaveText(vendor.name);
  await expect(dialog.getByLabel("From")).toHaveValue(day(RENEW_TO + 1));
  await expect(dialog.getByLabel("To", { exact: true })).toHaveValue(offer.to_date);
  const codes = machines.map((m) => m.code).sort().join(", ");
  await expect(dialog.getByTestId("renewal-notice")).toContainText(`2 machines are copied: ${codes}.`);
  await expect(dialog.getByTestId("renewal-notice")).toContainText("Prices start empty: the managers of SMTW enter them on the new contract.");
  const newTitle = contract.title.replace("2026–27", "2027–28");
  await dialog.getByLabel("Title").fill(newTitle);
  await saveDialog(page, "Renew contract");

  await expect(page.getByRole("heading", { name: newTitle })).toBeVisible();
  for (const machine of machines) await expect(machineLine(page, machine)).toBeVisible();
  await expect(chain(page)).toContainText(`Renews: ${contract.title} · ${shown(day(RENEW_FROM))} to ${shown(day(RENEW_TO))}`);
  await chain(page).getByRole("link", { name: contract.title }).click();
  await expect(page.getByRole("heading", { name: contract.title })).toBeVisible();
  await expect(chain(page)).toContainText(`Renewed by: ${newTitle} · ${shown(offer.from_date)} to ${shown(offer.to_date)}`);
  await expect(renewButton(page)).toHaveCount(0);
});

test("S085: when the vendors cannot be loaded, the renew dialog opens and says so", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/api/masters/vendors", 503);
  const { contract } = await contractToRenew(testInfo);
  await page.route("**/api/masters/vendors**", (route) => route.fulfill({ status: 503, json: { error: "Service unavailable" } }));
  await asPerson(page, "engineer", `/contracts/${contract.id}`);
  const dialog = await openRenew(page);
  await expect(dialog).toContainText("The list of vendors could not be loaded. Close the dialog and try again.");
});

test("S085: the manager renews a priced contract; the new contract shows No prices entered yet", async ({ page }, testInfo) => {
  const { contract } = await contractToRenew(testInfo, { machines: 1, price: "9809" });
  await asPerson(page, "manager", `/contracts/${contract.id}`);
  await expect(page.getByTestId("contract-total")).toHaveText("Total: ₹9,809 before GST · 1 of 1 machines priced.");
  const dialog = await openRenew(page);
  await expect(dialog.getByLabel("Cost note")).toHaveValue("");
  await expect(dialog.getByTestId("renewal-notice")).toContainText("Prices start empty: enter them on the new contract.");
  const newTitle = `${contract.title} renewed`;
  await dialog.getByLabel("Title").fill(newTitle);
  await saveDialog(page, "Renew contract");
  await expect(page.getByRole("heading", { name: newTitle })).toBeVisible();
  await expect(page.getByTestId("contract-total")).toHaveText("No prices entered yet.");
  await chain(page).getByRole("link", { name: contract.title }).click();
  await expect(page.getByTestId("contract-total")).toHaveText("Total: ₹9,809 before GST · 1 of 1 machines priced.");
});

test("S085: an inactive vendor is refused on renewal beside the Vendor field", async ({ page, consoleWatch }, testInfo) => {
  const { tag, contract, vendor } = await contractToRenew(testInfo);
  consoleWatch.allowFailedRequest(`/api/contracts/${contract.id}/renew`, 400);
  const other = await vendorByApi(`E2E Vendor other ${tag}`);
  await callAs("engineer", "put", `/api/masters/vendors/${vendor.id}`, { active: false });
  await asPerson(page, "engineer", `/contracts/${contract.id}`);
  const dialog = await openRenew(page);
  const vendorField = dialog.getByLabel("Vendor", { exact: true });
  await expect(vendorField.locator("option:checked")).toHaveText(`${vendor.name} (inactive)`);
  const refusal = `Vendor ${vendor.name} is inactive. Choose another vendor or reactivate it.`;
  await expect(dialog.getByText(refusal)).toBeVisible();
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expect(vendorField).toHaveClass(/is-invalid/);
  await expectFieldMessage(dialog, refusal);
  await vendorField.selectOption({ label: other.name });
  await saveDialog(page, "Renew contract");
  await expect(page.locator(".text-secondary", { hasText: `${other.name} · SMTW` }).first()).toBeVisible();
  await expect(chain(page)).toContainText(`Renews: ${contract.title}`);
});

test("S085: a scrapped machine is named in the notice and not copied", async ({ page }, testInfo) => {
  const { contract, machines } = await contractToRenew(testInfo, { machines: 2 });
  const [kept, scrapped] = machines;
  await callAs("admin", "put", `/api/equipment/${scrapped.id}`, { lifecycle: "scrapped" });
  await asPerson(page, "engineer", `/contracts/${contract.id}`);
  const dialog = await openRenew(page);
  await expect(dialog.getByTestId("renewal-notice")).toContainText(`1 machine is copied: ${kept.code}.`);
  await expect(dialog.getByTestId("renewal-notice")).toContainText(`Not copied: ${scrapped.code} (scrapped).`);
  await dialog.getByLabel("Title").fill(`${contract.title} renewed`);
  await saveDialog(page, "Renew contract");
  await expect(page.getByRole("heading", { name: `${contract.title} renewed` })).toBeVisible();
  await expect(machineLine(page, kept)).toBeVisible();
  await expect(machineLine(page, scrapped)).toHaveCount(0);
  await expect(machinesCard(page).locator(".card-header")).toContainText("Machines covered (1)");
});

test("S085: a renewal set inactive shows the way out to the engineer, and no Renew contract button", async ({ page }, testInfo) => {
  const { contract } = await contractToRenew(testInfo);
  const renewal = await renewByApi(contract, `${contract.title} renewed`);
  await callAs("engineer", "put", `/api/contracts/${renewal.id}`, { active: false });
  await asPerson(page, "engineer", `/contracts/${contract.id}`);
  await expect(chain(page)).toContainText(`Renewed by: ${renewal.title} · ${shown(renewal.from_date)} to ${shown(renewal.to_date)} (inactive)`);
  await expect(chain(page)).toContainText(WAY_OUT);
  await expect(renewButton(page)).toHaveCount(0);

  await asPerson(page, "operator", `/contracts/${contract.id}`);
  await expect(chain(page)).toContainText(`Renewed by: ${renewal.title}`);
  await expect(page.getByText(WAY_OUT)).toHaveCount(0);
});

test("S085: the operator sees the chain but no Renew contract button", async ({ page }, testInfo) => {
  const { contract } = await contractToRenew(testInfo);
  await asPerson(page, "operator", `/contracts/${contract.id}`);
  await expect(page.getByRole("heading", { name: contract.title })).toBeVisible();
  await expect(renewButton(page)).toHaveCount(0);
  const renewal = await renewByApi(contract, `${contract.title} renewed`);
  await asPerson(page, "operator", `/contracts/${renewal.id}`);
  await expect(chain(page)).toContainText(`Renews: ${contract.title}`);
  await expect(renewButton(page)).toHaveCount(0);
});

// ---------------------------------------------------------------------------
// Breakdown calls (S086, R02.6): the vendor's tickets on the contract page, and the contract on the ticket page.
// Each test makes its own vendor, Team records (by API as IT admin, never a seed person: other specs read the
// seed people's picker text unchanged, BR1-01), machines and tickets.
// ---------------------------------------------------------------------------

const callsCard = (page) => page.getByTestId("breakdown-calls");
const callRow = (page, ticket) => callsCard(page).getByTestId("breakdown-call").filter({ hasText: ticket.serial });
const NOT_ALL_UNITS = "Only the calls on machines of your units are listed.";
const NO_CALLS_OF_YOURS = "No calls on machines of your units. Only those are listed here.";

/** A contractor's Team record of `vendor` with `role` at SMTW, all units, by API as IT admin -> the person. */
async function teamRecordByApi(vendor, name, role = "maint_technician") {
  const person = await callAs("admin", "post", "/api/masters/people", {
    name, employment: "contractor", vendor_id: vendor.id, trade_ids: [],
  });
  await siteRoleByApi(person, role);
  return person;
}

const siteRoleByApi = async (person, role) => callAs("admin", "put",
  `/api/masters/people/${person.id}/sites/${await siteId("SMTW")}`, { role, all_units: true, unit_ids: [] });

const assignByApi = (ticket, person) => callAs("engineer", "post", `/api/tickets/${ticket.id}/assignees`,
  { person_id: person.id });

const labourByApi = (ticket, person) => callAs("engineer", "post", `/api/tickets/${ticket.id}/labour`,
  { person_id: person.id, work_date: istDay(0), minutes: 60 });

/** A breakdown on `node` raised `minutesAgo` before `base`, with `person` assigned -> the ticket. */
async function callByApi(node, person, tag, { minutesAgo = 60, base = thisMinute() } = {}) {
  const ticket = await raiseByApi("engineer", {
    equipment_id: node.id, intensity: "critical", description: `S086 call ${tag}`, occurred_at: istLocal(minutesAgo, base),
  });
  await assignByApi(ticket, person);
  return ticket;
}

/** The tag's vendor, a contract at SMTW with `fields` covering one new machine in `unitCode`, and a Team record. */
async function callsSetUp(testInfo, { fields = {}, unitCode = "SMTW.MCC1", role = "maint_technician" } = {}) {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const contract = await contractByApi(vendor, `E2E AMC ${tag}`, fields);
  const machine = await machineByApi(`E2E compressor ${tag}`, unitCode);
  await lineByApi(contract, machine);
  const person = await teamRecordByApi(vendor, `E2E vendor tech ${tag}`, role);
  return { tag, vendor, contract, machine, person };
}

/** The contract page as `key`, after the calls card's answer is in. */
async function openCallsAs(page, key, contract) {
  await asPerson(page, key);
  const answered = page.waitForResponse((r) => r.url().includes(`/api/contracts/${contract.id}/calls`));
  await page.goto(`/contracts/${contract.id}`);
  await answered;
  await expect(page.getByRole("heading", { name: contract.title })).toBeVisible();
}

test("S086: the contract page lists the vendor's breakdown call with downtime and the total line", async ({ page }, testInfo) => {
  const { tag, contract, machine, person } = await callsSetUp(testInfo);
  const base = thisMinute();
  const ticket = await callByApi(machine, person, tag, { minutesAgo: 200, base });
  await moveByApi("engineer", ticket.id, "schedule", {
    occurred_at: istLocal(150, base), planned_date: istDay(1), waiting_reason: "vendor",
  });
  await moveByApi("engineer", ticket.id, "start", { occurred_at: istLocal(30, base) });
  await moveByApi("engineer", ticket.id, "restore", { occurred_at: istLocal(10, base), person_id: person.id });

  await openCallsAs(page, "engineer", contract);
  await expect(callsCard(page).locator(".card-header")).toContainText("Breakdown calls");
  const row = callRow(page, ticket);
  await expect(row).toContainText(`${machine.code} — ${machine.name}`);
  await expect(row).toContainText("Down 3 h 10 min · waited on the vendor 2 h");
  await expect(row).toContainText("back in service");
  await expect(row).toContainText(`By: ${person.name}`);
  await expect(callsCard(page).getByTestId("calls-total")).toHaveText("1 call · down 3 h 10 min · waited on the vendor 2 h");
  await row.getByRole("link", { name: ticket.serial }).click();
  await expect(page).toHaveURL(new RegExp(`/tickets/${ticket.id}$`));
  await expect(page.getByRole("heading", { name: ticket.serial })).toBeVisible();
});

test("S086: an open defect call does not say the machine is not back in service", async ({ page }, testInfo) => {
  const { tag, contract, machine, person } = await callsSetUp(testInfo);
  const defect = await raiseByApi("engineer", {
    equipment_id: machine.id, intensity: "degraded", description: `S086 defect ${tag}`,
  });
  await assignByApi(defect, person);
  const breakdown = await callByApi(machine, person, tag);
  await openCallsAs(page, "engineer", contract);
  await expect(callRow(page, breakdown)).toContainText("not back in service yet");
  await expect(callRow(page, defect)).toBeVisible();
  await expect(callRow(page, defect)).not.toContainText("not back in service");
});

test("S086: a ticket worked only by in-house people is not a breakdown call", async ({ page }, testInfo) => {
  const { tag, contract, machine, person } = await callsSetUp(testInfo);
  const vendorCall = await callByApi(machine, person, tag);
  const inHouse = await raiseByApi("engineer", {
    equipment_id: machine.id, intensity: "critical", description: `S086 in-house ${tag}`,
  });
  await assignByApi(inHouse, { id: await personId("technician") });

  await openCallsAs(page, "engineer", contract);
  await expect(callRow(page, vendorCall)).toBeVisible();
  await expect(callsCard(page).getByTestId("breakdown-call")).toHaveCount(1);
  await expect(callsCard(page)).not.toContainText(inHouse.serial);
});

test("S086: a call on a part of the covered machine is listed with the part", async ({ page }, testInfo) => {
  const { tag, contract, machine, person } = await callsSetUp(testInfo);
  const part = await partByApi(machine, `E2E motor ${tag}`);
  const ticket = await callByApi(part, person, tag);

  await openCallsAs(page, "engineer", contract);
  await expect(callRow(page, ticket)).toContainText(`${machine.code} — ${machine.name} › ${part.code} — ${part.name}`);
});

test("S086: 1 of 2 calls used shows when the contract agrees a number", async ({ page }, testInfo) => {
  const { tag, vendor, contract, machine, person } = await callsSetUp(testInfo, {
    fields: { covers_breakdown_calls: true, breakdown_calls_per_year: 2 },
  });
  await callByApi(machine, person, tag);
  const tight = await contractByApi(vendor, `E2E AMC tight ${tag}`, { covers_breakdown_calls: true, breakdown_calls_per_year: 1 });
  const second = await machineByApi(`E2E compressor 2 ${tag}`);
  await lineByApi(tight, second);
  await callByApi(second, person, tag, { minutesAgo: 90 });
  await callByApi(second, person, tag, { minutesAgo: 30 });

  await openCallsAs(page, "engineer", contract);
  await expect(callsCard(page).getByTestId("calls-used")).toHaveText("1 of 2 calls used this period.");
  await openCallsAs(page, "engineer", tight);
  const used = callsCard(page).getByTestId("calls-used");
  await expect(used).toHaveText("2 of 1 calls used — more than agreed.");
  await expect(used).toHaveClass(/text-danger/);
});

test("S086: the contract page warns when no Team record is linked to the vendor", async ({ page }, testInfo) => {
  const tag = propertyTag(testInfo);
  const vendor = await vendorByApi(`E2E Vendor ${tag}`);
  const contract = await contractByApi(vendor, `E2E AMC ${tag}`);
  const warning = callsCard(page).getByRole("alert");

  await openCallsAs(page, "engineer", contract);
  await expect(warning).toHaveText(`No Team record is linked to ${vendor.name}. Link the vendor's technician, or a`
    + ` record such as '${vendor.name} service', in Masters › Team.`);
  const person = await teamRecordByApi(vendor, `E2E vendor tech ${tag}`, "maint_operator");
  await openCallsAs(page, "engineer", contract);
  await expect(warning).toHaveText(`No Team record of ${vendor.name} can be assigned at SMTW. Give one a Technician`
    + " role there in Masters › Team.");
  await siteRoleByApi(person, "maint_technician");
  await openCallsAs(page, "engineer", contract);
  await expect(callsCard(page)).toContainText("No breakdown calls on this contract yet.");
  await expect(warning).toHaveCount(0);
});

test("S086: the storekeeper sees the contract page without the Breakdown calls card", async ({ page }, testInfo) => {
  const { tag, contract, machine, person } = await callsSetUp(testInfo);
  await callByApi(machine, person, tag);
  await asPerson(page, "storekeeper", `/contracts/${contract.id}`);
  await expect(page.getByRole("heading", { name: contract.title })).toBeVisible();
  await expect(machinesCard(page)).toBeVisible();
  await expect(callsCard(page)).toHaveCount(0);
});

test("S086: the operator sees only the calls of their units and no used line", async ({ page }, testInfo) => {
  const { tag, vendor, contract, machine, person } = await callsSetUp(testInfo, {
    fields: { covers_breakdown_calls: true, breakdown_calls_per_year: 4 }, unitCode: "SMTW.MCC2",
  });
  const mcc1Machine = await machineByApi(`E2E MCC1 compressor ${tag}`, "SMTW.MCC1");
  await lineByApi(contract, mcc1Machine);
  const mine = await callByApi(machine, person, tag, { minutesAgo: 90 });
  const notMine = await callByApi(mcc1Machine, person, tag, { minutesAgo: 30 });
  const elsewhere = await contractByApi(vendor, `E2E AMC MCC1 only ${tag}`);
  const other = await machineByApi(`E2E MCC1 compressor 2 ${tag}`, "SMTW.MCC1");
  await lineByApi(elsewhere, other);
  await callByApi(other, person, tag);

  await openCallsAs(page, "operator", contract);
  await expect(callRow(page, mine)).toBeVisible();
  await expect(callsCard(page)).not.toContainText(notMine.serial);
  await expect(callsCard(page)).toContainText(NOT_ALL_UNITS);
  await expect(callsCard(page).getByTestId("calls-used")).toHaveCount(0);

  await openCallsAs(page, "operator", elsewhere);
  await expect(callsCard(page).getByTestId("breakdown-call")).toHaveCount(0);
  await expect(callsCard(page).locator(".card-body")).toHaveText(NO_CALLS_OF_YOURS);
  await expect(callsCard(page)).not.toContainText(NOT_ALL_UNITS);
});

test("S086: an open ticket on a covered machine shows the contract line and Do not repair", async ({ page }, testInfo) => {
  const { tag, vendor, contract, machine } = await callsSetUp(testInfo, {
    fields: { only_vendor_repairs: true, response_hours: 24, covers_breakdown_calls: true },
  });
  const ticket = await raiseByApi("engineer", { equipment_id: machine.id, intensity: "critical", description: `S086 line ${tag}` });

  const line = page.getByTestId("ticket-contract");
  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  await expect(line).toContainText(`Under AMC with ${vendor.name} until ${shown(day(300))} · response 24 hours · breakdown calls included`);
  await expect(line.getByRole("alert")).toHaveText(DO_NOT_REPAIR);
  const before = await line.evaluate((el) => {
    const bar = document.querySelector(".action-bar");
    return Boolean(bar) && Boolean(el.compareDocumentPosition(bar) & Node.DOCUMENT_POSITION_FOLLOWING);
  });
  expect(before, "the contract line comes before the action bar").toBe(true);
  await line.getByRole("link", { name: `Under AMC with ${vendor.name}` }).click();
  await expect(page).toHaveURL(new RegExp(`/contracts/${contract.id}$`));

  await moveByApi("engineer", ticket.id, "not-a-fault", { cause_id: await causeId("5.1"), remark: `S086 closed ${tag}` });
  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  await expect(page.getByRole("heading", { name: ticket.serial })).toBeVisible();
  await expect(page.getByText("Not a fault", { exact: true }).first()).toBeVisible();
  await expect(line).toHaveCount(0);
});

test("S086: the assignee picker shows the vendor beside a linked person and finds them by the vendor's name", async ({ page }, testInfo) => {
  const { tag, vendor, machine, person } = await callsSetUp(testInfo);
  const ticket = await raiseByApi("engineer", { equipment_id: machine.id, intensity: "degraded", description: `S086 picker ${tag}` });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  await page.getByRole("button", { name: "Assign" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByPlaceholder("Type a name or vendor to filter").fill(vendor.name.toLowerCase());
  const pick = dialog.getByRole("button", { name: `${person.name} · Technician · ${vendor.name}` });
  await expect(pick).toBeVisible();
  await pick.click();
  await expect(dialog).toContainText(`${person.name}Technician · ${vendor.name}`); // the picked line, above the filter
  await saveDialog(page, "Assign");
  await expect(card(page, "Assigned")).toContainText(person.name);
});

test("S086: the Breakdown calls card fits a phone with no sideways scroll", { tag: "@device" }, async ({ page }, testInfo) => {
  const { tag, contract, machine, person } = await callsSetUp(testInfo, { role: "maint_operator" });
  const part = await partByApi(machine, `E2E motor with a long name for the phone ${tag}`);
  for (const node of [machine, part]) {
    const ticket = await raiseByApi("engineer", { equipment_id: node.id, intensity: "critical", description: `S086 fit ${tag}` });
    await labourByApi(ticket, person);
  }
  await openCallsAs(page, "engineer", contract);
  await expect(callsCard(page).getByTestId("breakdown-call")).toHaveCount(2);
  await expect(callsCard(page).getByRole("alert")).toBeVisible();
  await expectNoSidewaysScroll(page);
});
