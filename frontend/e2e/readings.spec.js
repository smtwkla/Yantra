// Meter readings from the equipment page (S039 § 1.3, § 1.4, § 8), the end-of-day sheet (S040) and the
// reading register (S050 § 8.4).
//
// Set-up (BR1-09, BR2-04, BS1-03): the three projects share one database, so no test reads or
// writes a seed node.  Each test makes its own machine at SMTW.MCC2 (the operator's unit) with
// S038's meterMachine, of a press model of its own, so no seed model is touched and no test
// depends on another's readings or order.  The Yes / No meter type is made once per project in
// beforeAll (no Yes / No seed, S037 decision 8).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll, openDialog } from "./support/dialogs.js";
import { logByApi, meterMachine } from "./support/meters.js";
import { apiAs, asPerson } from "./support/people.js";
import { card, istLocal, saveDialog, setEventTime, shownTime } from "./support/tickets.js";

const UNIT = "SMTW.MCC2";
const MIN_TOUCH_PX = 48; // the Yes / No buttons on a phone (U3)
const NOW_TIME = /\d{2}-\d{2}-\d{4} \d{2}:\d{2}/;

// The page's own requests are answered by page.route below (a held, failed or 404 answer).  WebKit
// does not route them while the app's service worker (S021) controls the page, so none is started.
test.use({ serviceWorkers: "block" });

let questionName; // this project's Yes / No meter type, expected Yes

test.beforeAll(async ({}, testInfo) => {
  questionName = `E2E oil level above min ${testInfo.project.name} ${Date.now().toString(36)}`;
  const api = await apiAs("engineer");
  try {
    const res = await api.post("/api/masters/meter-types", {
      data: { name: questionName, kind: "yes_no", unit: null, decimals: 0, expected_answer: "yes" },
    });
    expect(res.status(), await res.text()).toBe(201);
  } finally {
    await api.dispose();
  }
});

const meterRow = (page, name) => card(page, "Meters").getByTestId("node-meter").filter({ hasText: name });
const lastReading = (page, name) => meterRow(page, name).getByTestId("last-reading");

async function openLog(page, name) {
  await meterRow(page, name).getByRole("button", { name: "Log reading" }).click();
  await expectDialogFits(page);
  return openDialog(page);
}

async function openHistory(page, name) {
  await lastReading(page, name).click();
  const dialog = await openDialog(page);
  // A close-only dialog (no Save / Cancel for expectDialogFits): its Close is on screen
  await expect(dialog.locator(".modal-footer").getByRole("button", { name: "Close" })).toBeInViewport();
  return dialog;
}

test("S039: an operator logs a reading from the equipment page", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "log", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  await expect(meterRow(page, "Run hours")).toContainText("No readings yet");
  await expect(lastReading(page, "Run hours")).toHaveCount(0); // not a tap target before any reading

  const dialog = await openLog(page, "Run hours");
  await expect(dialog.locator(".modal-title")).toHaveText("Log reading · Run hours");
  await expect(dialog).not.toContainText("Last reading"); // none yet (BR2-08)
  const value = dialog.getByLabel("Value", { exact: true });
  await expect(value).toHaveAttribute("inputmode", "decimal");
  await expect(dialog.locator(".input-group-text")).toHaveText("h");
  await expect(dialog).toContainText("Time of reading");
  await expect(dialog.getByLabel("Meter reset")).not.toBeChecked();
  await value.fill("120.5");
  await saveDialog(page, "Save");

  await expect(lastReading(page, "Run hours")).toContainText("120.5 h ·");
  await expect(lastReading(page, "Run hours")).toContainText(NOW_TIME);
  await expect(meterRow(page, "Run hours").getByRole("status")).toHaveCount(0); // inside what is good: no message
});

test("S039: a counter lower than the last reading is refused beside the value", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest(`/readings`, 400); // the refusal is the point of the test
  const machine = await meterMachine(testInfo, "lower", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  const earlier = istLocal(60);
  await logByApi(machine, "Run hours", "1000", earlier);
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const dialog = await openLog(page, "Run hours");
  await expect(dialog).toContainText(`Last reading: 1,000.0 h on ${shownTime(earlier)}`);
  await dialog.getByLabel("Value", { exact: true }).fill("900");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, `Lower than the reading of ${shownTime(earlier)} (1,000.0 h). Check the value, or tick`
    + " Meter reset if the meter was reset.");
  await expect(dialog.getByLabel("Value", { exact: true })).toHaveValue("900"); // the typed value is kept

  // The meter was replaced: ticked as a reset, the same value is saved
  await dialog.getByLabel("Meter reset").check();
  await saveDialog(page, "Save");
  await expect(lastReading(page, "Run hours")).toContainText("900.0 h ·");
});

test("S039: a gauge above its limit is saved and shows High", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "high", { unit: UNIT, ownMeters: [["Oil temperature", { max_value: "60" }]] });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const dialog = await openLog(page, "Oil temperature");
  await expect(dialog.getByLabel("Meter reset")).toHaveCount(0); // a gauge is never reset
  await dialog.getByLabel("Value", { exact: true }).fill("65");
  await saveDialog(page, "Save");

  const row = meterRow(page, "Oil temperature");
  await expect(row.getByRole("status")).toHaveText("Saved. Above the limit of 60 °C.");
  await expect(lastReading(page, "Oil temperature")).toContainText("65.0 °C ·");
  await expect(lastReading(page, "Oil temperature").locator(".badge")).toHaveText("High");
});

test("S039: the saved message names the limit in force at saving (CR1-06)", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "limitchange", { unit: UNIT, ownMeters: [["Oil temperature", { max_value: "60" }]] });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const dialog = await openLog(page, "Oil temperature");
  // An engineer lowers the limit while the dialog is open
  const api = await apiAs("engineer");
  try {
    const types = await (await api.get("/api/masters/meter-types")).json();
    const oil = types.items.find((t) => t.name === "Oil temperature");
    const res = await api.put(`/api/equipment/${machine.id}/meters/${oil.id}`, { data: { min_value: null, max_value: "50" } });
    expect(res.status(), await res.text()).toBe(200);
  } finally {
    await api.dispose();
  }
  await dialog.getByLabel("Value", { exact: true }).fill("65");
  await saveDialog(page, "Save");
  await expect(meterRow(page, "Oil temperature").getByRole("status")).toHaveText("Saved. Above the limit of 50 °C.");
});

test("S039: an engineer removes a wrong reading and the operator enters it again", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "remove", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  const typed = istLocal(30);
  await logByApi(machine, "Run hours", "99999", typed);
  await asPerson(page, "engineer", `/equipment/${machine.id}`);
  const dialog = await openHistory(page, "Run hours");
  await expect(dialog.locator(".modal-title")).toHaveText("History · Run hours");
  const row = dialog.getByTestId("reading-row");
  await expect(row).toContainText("99,999.0 h");
  await expect(row).toContainText("e2e_operator");

  await row.getByRole("button", { name: "Remove" }).click();
  await expect(row).toContainText(`Remove the reading of ${shownTime(typed)} (99,999.0 h)? It no longer counts. You cannot undo this.`);
  await row.getByRole("button", { name: "Keep" }).click();
  await expect(row).not.toContainText("It no longer counts");
  await row.getByRole("button", { name: "Remove" }).click();
  await row.getByRole("button", { name: "Remove" }).click();
  await expect(dialog.getByTestId("reading-row")).toHaveCount(0);
  await expect(dialog).toContainText("No readings.");

  // Show removed: the reading stays on record, with who removed it
  await dialog.getByLabel("Show removed").check();
  await expect(dialog.getByTestId("reading-row")).toContainText("Removed");
  await expect(dialog.getByTestId("reading-row")).toContainText("e2e_engineer");
  await dialog.locator(".modal-footer").getByRole("button", { name: "Close" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(meterRow(page, "Run hours")).toContainText("No readings yet");

  // The operator enters the right value: the removed one no longer counts
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const log = await openLog(page, "Run hours");
  await log.getByLabel("Value", { exact: true }).fill("120");
  await saveDialog(page, "Save");
  await expect(lastReading(page, "Run hours")).toContainText("120.0 h ·");
});

test("S039: the operator who logged a reading sees no Remove on it", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "own", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await logByApi(machine, "Run hours", "50", istLocal(30), { note: "E2E by the operator" });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const dialog = await openHistory(page, "Run hours");
  const row = dialog.getByTestId("reading-row");
  await expect(row).toContainText("E2E by the operator");
  await expect(row.getByRole("button", { name: "Remove" })).toHaveCount(0);
  await expect(dialog.getByLabel("Show removed")).toHaveCount(0);
});

test("S039: a shift's production lower than the last one is saved", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "shift", { unit: UNIT, ownMeters: [["Shift production", {}]] });
  await logByApi(machine, "Shift production", "420", istLocal(60));
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const dialog = await openLog(page, "Shift production");
  await expect(dialog).toContainText("The amount for the period just ended, such as this shift.");
  await expect(dialog.getByLabel("Meter reset")).toHaveCount(0);
  await dialog.getByLabel("Value", { exact: true }).fill("380");
  await saveDialog(page, "Save");
  await expect(lastReading(page, "Shift production")).toContainText("380 pcs ·");
  await expect(meterRow(page, "Shift production").getByRole("status")).toHaveCount(0);
});

test("S039: a No on a Yes / No meter, then Save, shows Not OK", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "yesno", { unit: UNIT, ownMeters: [[questionName, {}]] });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const dialog = await openLog(page, questionName);
  await expect(dialog.locator(".modal-title")).toHaveText(questionName); // the question is the heading
  const save = dialog.locator(".modal-footer button[type=submit]");
  await expect(save).toBeDisabled();
  await expect(save).toHaveAttribute("title", "Pick Yes or No");

  const viewport = page.viewportSize();
  for (const answer of ["Yes", "No"]) {
    const button = dialog.getByRole("button", { name: answer, exact: true });
    const box = await button.boundingBox();
    expect(box.height, `${answer} is too small for a thumb`).toBeGreaterThanOrEqual(MIN_TOUCH_PX);
    expect(box.x >= 0 && box.x + box.width <= viewport.width, `${answer} is off screen`).toBe(true);
    await expect(button).toBeInViewport();
  }
  await dialog.getByRole("button", { name: "No", exact: true }).click();
  await expect(dialog.getByRole("button", { name: "No", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(save).toBeEnabled();
  await dialog.getByLabel("Note").fill("E2E topped up after the check");
  await saveDialog(page, "Save");

  await expect(meterRow(page, questionName).getByRole("status")).toHaveText("Saved. Not OK: the expected answer is Yes.");
  await expect(lastReading(page, questionName)).toContainText("No ·");
  await expect(lastReading(page, questionName).locator(".badge")).toHaveText("Not OK");
  const history = await openHistory(page, questionName);
  const row = history.getByTestId("reading-row");
  await expect(row).toContainText("Not OK");
  await expect(row).toContainText("E2E topped up after the check"); // the note typed after the answer is kept
});

// ---------------------------------------------------------------------------
// S040: the end-of-day sheet.  The sheet lists every machine at SMTW with meters, from every test
// and project in the lane, so each assertion is scoped to the test's own card (found by its
// machine's name) and the header counts are read as patterns, never as literal numbers (BS1-01).
// ---------------------------------------------------------------------------

const sheetCard = (page, machine) => page.getByTestId("sheet-machine").filter({ hasText: machine.name });
const sheetRow = (cardLocator, name) => cardLocator.getByTestId("sheet-meter").filter({ hasText: name });
const rowInput = (row) => row.locator("input.form-control");
const saveReadings = (page) => page.getByRole("button", { name: "Save readings" });
const askEngineer = (page) => page.getByText("A wrong reading is removed by an engineer. Ask one.");
const NOT_SAVED = "Not saved. Try again in a minute.";
const SAME_MINUTE = "A reading at this time exists. Pick another time, or remove that reading first.";
const SITE_KEY = "yantra.readings.site_id";

// The sheet's own rule for a meter's last reading: "Today HH:MM · v" when it was taken today (IST),
// else "v · DD-MM-YYYY HH:MM" (CR1-01: a reading an hour ago is yesterday's in the first hour after midnight)
const lastLine = (taken, reading) => (taken.slice(0, 10) === istLocal(0).slice(0, 10)
  ? `Today ${taken.slice(11)} · ${reading}`
  : `${reading} · ${shownTime(taken)}`);
// Minutes since 00:00 IST: a reading that many minutes ago, or fewer, is always today's
const minutesIntoIstDay = () => {
  const [hours, minutes] = istLocal(0).slice(11).split(":").map(Number);
  return hours * 60 + minutes;
};
const countOf = async (locator) => Number((await locator.textContent()).match(/^(\d+) of/)[1]);

async function openSheet(page, key) {
  await asPerson(page, key, "/readings");
  await expect(page.getByTestId("sheet-heading")).toBeVisible();
}

test("S040: the end-of-day sheet saves the filled rows and shows each refusal", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/readings", 400); // the refusal is the point of the test
  const machine = await meterMachine(testInfo, "s40save", {
    unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", { max_value: "60" }]],
  });
  const earlier = istLocal(60);
  await logByApi(machine, "Run hours", "1000", earlier);
  await openSheet(page, "operator");
  await expect(page.getByTestId("sheet-heading")).toContainText("SMTW — ");
  const machineCard = sheetCard(page, machine);
  const hours = sheetRow(machineCard, "Run hours");
  const oil = sheetRow(machineCard, "Oil temperature");
  await expect(hours.getByTestId("sheet-last")).toContainText(lastLine(earlier, "1,000.0 h"));
  await expect(hours.getByLabel("Meter reset")).toHaveCount(0); // hidden until a "Lower than" refusal (BR1-02)
  const filledBefore = await countOf(page.getByTestId("filled-count"));

  await rowInput(hours).fill("900");
  await rowInput(oil).fill("55");
  await expect(page.getByTestId("filled-count")).toContainText(`${filledBefore + 2} of`);
  await saveReadings(page).click();

  await expect(oil.getByRole("status")).toHaveText("Saved");
  await expect(rowInput(oil)).toHaveAttribute("readonly", ""); // a saved row turns read-only
  await expect(hours.getByRole("alert")).toHaveText(`Lower than the reading of ${shownTime(earlier)} (1,000.0 h). Check the value,`
    + " or tick Meter reset if the meter was reset.");
  await expect(hours.getByRole("alert")).toBeInViewport();
  await expect(rowInput(hours)).toHaveValue("900"); // the typed value is kept
  await expectNoSidewaysScroll(page);

  // The meter was replaced: tick Meter reset and save again; the saved row is not posted twice
  await hours.getByLabel("Meter reset").check();
  await saveReadings(page).click();
  await expect(hours.getByRole("status")).toHaveText("Saved");
  await expect(oil.getByRole("status")).toHaveText("Saved");
  const api = await apiAs("engineer");
  try {
    const types = await (await api.get("/api/masters/meter-types")).json();
    const oilType = types.items.find((t) => t.name === "Oil temperature");
    const history = await (await api.get(`/api/equipment/${machine.id}/readings?meter_type_id=${oilType.id}`)).json();
    expect(history.total).toBe(1);
  } finally {
    await api.dispose();
  }
});

test("S040: Undo on a saved row makes it editable again", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40undo", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await openSheet(page, "engineer");
  const row = sheetRow(sheetCard(page, machine), "Run hours");
  await rowInput(row).fill("120");
  await saveReadings(page).click();
  await expect(row.getByRole("status")).toHaveText("Saved");
  await expect(askEngineer(page)).toHaveCount(0); // the engineer removes readings: no line about asking one

  await row.getByRole("button", { name: "Undo" }).click();
  await expect(row.getByRole("button", { name: "Undo" })).toHaveCount(0);
  await expect(rowInput(row)).not.toHaveAttribute("readonly", "");
  await expect(rowInput(row)).toHaveValue("120"); // the value is kept
  // The reading is removed on the server: the same value saves again in the same minute
  await saveReadings(page).click();
  await expect(row.getByRole("status")).toHaveText("Saved");
  const api = await apiAs("engineer");
  try {
    const types = await (await api.get("/api/masters/meter-types")).json();
    const hoursType = types.items.find((t) => t.name === "Run hours");
    const history = await (await api.get(`/api/equipment/${machine.id}/readings?meter_type_id=${hoursType.id}&include_removed=1`)).json();
    expect(history.total).toBe(2); // the removed one stays on record
    expect(history.items.filter((r) => r.removed_at === null)).toHaveLength(1);
  } finally {
    await api.dispose();
  }
});

test("S040: the operator's saved row reads Saved, the sheet shows the Ask an engineer line once, and there is no Undo", async ({ page }, testInfo) => {
  const mine = await meterMachine(testInfo, "s40op", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  const other = await meterMachine(testInfo, "s40opmcc1", { unit: "SMTW.MCC1", ownMeters: [["Run hours", {}]] });
  await openSheet(page, "operator");
  await expect(askEngineer(page)).toHaveCount(0); // not before a first save
  const row = sheetRow(sheetCard(page, mine), "Run hours");
  await rowInput(row).fill("75");
  await saveReadings(page).click();
  await expect(row.getByRole("status")).toHaveText("Saved");
  await expect(page.getByRole("button", { name: "Undo" })).toHaveCount(0);
  await expect(askEngineer(page)).toHaveCount(1);
  // The operator holds MCC2 only: another unit of the site is not on the sheet (BR2-02)
  await expect(page.getByTestId("sheet-unit").filter({ hasText: "MCC2" })).toHaveCount(1);
  await expect(page.getByTestId("sheet-unit").filter({ hasText: "MCC1" })).toHaveCount(0);
  await expect(page.getByText(other.name)).toHaveCount(0);
});

test("S040: a shift production row takes an amount lower than the last one", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40shift", { unit: UNIT, ownMeters: [["Shift production", {}]] });
  const taken = istLocal(60);
  await logByApi(machine, "Shift production", "420", taken);
  await openSheet(page, "operator");
  const row = sheetRow(sheetCard(page, machine), "Shift production");
  await expect(row).toContainText("The amount for the period just ended, such as this shift.");
  await expect(row.getByTestId("sheet-last")).toContainText(lastLine(taken, "420 pcs"));
  await rowInput(row).fill("380");
  await expect(row.getByLabel("Meter reset")).toHaveCount(0);
  await saveReadings(page).click();
  await expect(row.getByRole("status")).toHaveText("Saved");
  await expect(row.getByLabel("Meter reset")).toHaveCount(0);
});

test("S040: a Yes / No row answered No saves and shows Not OK", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40yn", { unit: UNIT, ownMeters: [[questionName, {}]] });
  await openSheet(page, "operator");
  const row = sheetRow(sheetCard(page, machine), questionName);
  await row.scrollIntoViewIfNeeded();
  await expect(row).toContainText(questionName); // the question is the row's label
  const viewport = page.viewportSize();
  for (const answer of ["Yes", "No"]) {
    const button = row.getByRole("button", { name: answer, exact: true });
    const box = await button.boundingBox();
    expect(box.height, `${answer} is too small for a thumb`).toBeGreaterThanOrEqual(MIN_TOUCH_PX);
    expect(box.x >= 0 && box.x + box.width <= viewport.width, `${answer} is off screen`).toBe(true);
    await expect(button).toBeInViewport();
  }
  const no = row.getByRole("button", { name: "No", exact: true });
  await no.click();
  await expect(no).toHaveAttribute("aria-pressed", "true");
  await no.click(); // a second tap clears the answer
  await expect(no).toHaveAttribute("aria-pressed", "false");
  await expect(row.getByRole("button", { name: "Yes", exact: true })).toHaveAttribute("aria-pressed", "false");
  await no.click();
  await expect(no).toHaveAttribute("aria-pressed", "true");
  await saveReadings(page).click(); // picking only chooses; Save readings saves (decision 9)

  await expect(row.getByRole("status")).toHaveText("Saved. Not OK: the expected answer is Yes.");
  await expect(no).toBeDisabled();
  const api = await apiAs("operator");
  try {
    const types = await (await api.get("/api/masters/meter-types")).json();
    const type = types.items.find((t) => t.name === questionName);
    const history = await (await api.get(`/api/equipment/${machine.id}/readings?meter_type_id=${type.id}`)).json();
    expect(history.items.map((r) => [r.value, r.limit_state])).toEqual([["no", "not_ok"]]);
  } finally {
    await api.dispose();
  }
});

test("S040: Save readings is disabled while saving, and the bar is above the bottom nav", { tag: "@device" }, async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40wait", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  let release;
  const held = new Promise((resolve) => { release = resolve; });
  await page.route(`**/api/equipment/${machine.id}/readings`, async (route) => {
    await held; // the POST waits until the test lets it go
    await route.continue();
  });
  await openSheet(page, "operator");
  const row = sheetRow(sheetCard(page, machine), "Run hours");
  await rowInput(row).fill("10");
  const save = saveReadings(page);
  await expect(save).toBeEnabled();
  const nav = page.locator(".app-bottom-nav");
  if (await nav.isVisible()) {
    // On a phone the bar sticks to the bottom of the screen, above the nav (BR1-04)
    await expect(save).toBeInViewport();
    const [saveBox, navBox] = await Promise.all([save.boundingBox(), nav.boundingBox()]);
    expect(saveBox.y + saveBox.height, "Save readings is under the bottom nav").toBeLessThanOrEqual(navBox.y + 1);
  }
  await save.click();
  await expect(save).toBeDisabled(); // a row in flight is never posted twice
  release();
  await expect(row.getByRole("status")).toHaveText("Saved");
});

test("S040: the supervisor sees no site picker and both MCC1 and MCC2 on one sheet; the manager picks a site and it is remembered", async ({ page }, testInfo) => {
  const mcc1 = await meterMachine(testInfo, "s40sup1", { unit: "SMTW.MCC1", ownMeters: [["Run hours", {}]] });
  const mcc2 = await meterMachine(testInfo, "s40sup2", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await openSheet(page, "supervisor");
  await expect(page.getByLabel("Site", { exact: true })).toHaveCount(0); // one site: no picker
  await expect(page.getByTestId("sheet-heading")).toContainText("SMTW — ");
  await expect(page.getByTestId("sheet-unit").filter({ hasText: "MCC1" }).filter({ has: sheetCard(page, mcc1) })).toHaveCount(1);
  await expect(page.getByTestId("sheet-unit").filter({ hasText: "MCC2" }).filter({ has: sheetCard(page, mcc2) })).toHaveCount(1);

  // The manager logs at two sites: a picker.  BRICKS has no meters in a lane's database (BR1-12)
  await asPerson(page, "manager", "/readings");
  const picker = page.getByLabel("Site", { exact: true });
  await expect(picker).toBeVisible();
  const chosen = picker.locator("option:checked");
  await picker.selectOption({ label: "SMTW" });
  await expect(page.getByTestId("sheet-heading")).toContainText("SMTW — ");
  await page.reload();
  await expect(page.getByTestId("sheet-heading")).toContainText("SMTW — ");
  await expect(chosen).toHaveText("SMTW"); // remembered, not the first site
  await picker.selectOption({ label: "BRICKS" });
  await expect(page.getByTestId("sheet-heading")).toContainText("BRICKS — ");
  await expect(page.getByText("No machine at this site has meters.")).toBeVisible();
  await expect(saveReadings(page)).toHaveCount(0);
  await expect(picker).toBeVisible(); // another site can be picked (BR2-10)
  await page.reload();
  await expect(chosen).toHaveText("BRICKS");
});

test("S040: a meter read today shows Today and its tick", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40today", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  const taken = istLocal(Math.min(2, minutesIntoIstDay())); // always today, also just after midnight
  await logByApi(machine, "Run hours", "300", taken);
  await logByApi(machine, "Oil temperature", "40", istLocal(60 * 24 * 3)); // three days ago
  await openSheet(page, "operator");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  const oil = sheetRow(sheetCard(page, machine), "Oil temperature");
  await expect(hours.getByTestId("sheet-last")).toHaveText(`Today ${taken.slice(11)} · 300.0 h`);
  await expect(hours.locator(".fa-circle-check")).toHaveCount(1);
  await expect(oil.getByTestId("sheet-last")).toContainText("40.0 °C · ");
  await expect(oil.getByTestId("sheet-last")).not.toContainText("Today");
  await expect(oil.locator(".fa-circle-check")).toHaveCount(0);
  await expect(rowInput(hours)).toHaveValue(""); // still empty, and can be typed in
  await expect(rowInput(hours)).toBeEditable();
  // A reading saved now counts as read today in the header
  const before = await countOf(page.getByTestId("read-today-count"));
  await rowInput(oil).fill("41");
  await saveReadings(page).click();
  await expect(oil.getByRole("status")).toHaveText("Saved");
  await expect(page.getByTestId("read-today-count")).toContainText(`${before + 1} of`);
});

// ---------------------------------------------------------------------------
// S040 fix round 1 (CR1-02 to CR1-05)
// ---------------------------------------------------------------------------

/** Count the POSTs of the machine's readings; `reply(route)` answers each one. */
async function watchPosts(page, machine, reply) {
  const seen = { posts: 0 };
  await page.route(`**/api/equipment/${machine.id}/readings`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    seen.posts += 1;
    return reply(route);
  });
  return seen;
}

const FAILURES = [
  ["503", 503, (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: "Service unavailable" }) })],
  ["no answer", "ERR_FAILED", (route) => route.abort("failed")],
];
for (const [label, consoleStatus, reply] of FAILURES) {
  test(`S040: a failed save (${label}) stops the loop; both rows read Not saved and keep their values`, async ({ page, consoleWatch }, testInfo) => {
    consoleWatch.allowFailedRequest("/readings", consoleStatus);
    const machine = await meterMachine(testInfo, `s40fail${label.replace(" ", "")}`, {
      unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]],
    });
    const seen = await watchPosts(page, machine, reply);
    await openSheet(page, "operator");
    const hours = sheetRow(sheetCard(page, machine), "Run hours");
    const oil = sheetRow(sheetCard(page, machine), "Oil temperature");
    await rowInput(hours).fill("100");
    await rowInput(oil).fill("40");
    await saveReadings(page).click();
    await expect(hours.getByRole("alert")).toHaveText(NOT_SAVED);
    await expect(oil.getByRole("alert")).toHaveText(NOT_SAVED);
    await expect(rowInput(hours)).toHaveValue("100");
    await expect(rowInput(oil)).toHaveValue("40");
    expect(seen.posts, "the loop went on after the failure").toBe(1);
    await expect(saveReadings(page)).toBeEnabled(); // try again in a minute
  });
}

test("S040: a refused Time of reading shows once on the time field and stops the loop (CR1-04)", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/readings", 400);
  const machine = await meterMachine(testInfo, "s40time", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  const seen = await watchPosts(page, machine, (route) => route.continue());
  await openSheet(page, "operator");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  const oil = sheetRow(sheetCard(page, machine), "Oil temperature");
  await setEventTime(page, istLocal(60 * 24 * 8)); // more than 7 days back
  await rowInput(hours).fill("100");
  await rowInput(oil).fill("40");
  await saveReadings(page).click();
  await expect(page.locator(".invalid-feedback")).toHaveCount(1); // once, on the shared field
  await expect(page.locator(".invalid-feedback")).toBeInViewport();
  await expect(hours.getByRole("alert")).toHaveText("Not saved. Change Time of reading, then save again.");
  await expect(oil.getByRole("alert")).toHaveText("Not saved. Change Time of reading, then save again.");
  await expect(rowInput(oil)).toHaveValue("40");
  expect(seen.posts, "every row was posted with the refused time").toBe(1);
});

test("S040: a reading already at that minute is refused on its own row, not on Time of reading (CR1-04)", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/readings", 409);
  const machine = await meterMachine(testInfo, "s40same", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  const taken = istLocal(30);
  await logByApi(machine, "Run hours", "100", taken);
  await openSheet(page, "operator");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  const oil = sheetRow(sheetCard(page, machine), "Oil temperature");
  await setEventTime(page, taken);
  await rowInput(hours).fill("110");
  await rowInput(oil).fill("40");
  await saveReadings(page).click();
  await expect(oil.getByRole("status")).toHaveText("Saved"); // the loop went on
  await expect(hours.getByRole("alert")).toHaveText(SAME_MINUTE);
  await expect(page.locator(".invalid-feedback")).toHaveCount(0);
});

test("S040: the site picker asks before it discards typed readings, and waits during a save (CR1-02)", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40pick", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await asPerson(page, "manager", "/readings");
  const picker = page.getByLabel("Site", { exact: true });
  const chosen = picker.locator("option:checked");
  await picker.selectOption({ label: "SMTW" });
  await expect(page.getByTestId("sheet-heading")).toContainText("SMTW — ");
  const row = sheetRow(sheetCard(page, machine), "Run hours");
  await rowInput(row).fill("50");

  await picker.selectOption({ label: "BRICKS" });
  const confirm = page.getByTestId("discard-confirm");
  await expect(confirm).toContainText("Discard 1 typed reading? Switching site removes them. You cannot undo this.");
  await expect(chosen).toHaveText("SMTW"); // the picker is back on the current site
  // Keep editing is the first button (the main one), Discard the second, as in FormModal (CR2-01)
  await expect(confirm.getByRole("button")).toHaveText(["Keep editing", "Discard"]);
  await expect(confirm.getByRole("button", { name: "Keep editing" })).toHaveClass(/btn-primary/);
  await expect(confirm.getByRole("button", { name: "Discard" })).toHaveClass(/btn-outline-danger/);
  await confirm.getByRole("button", { name: "Keep editing" }).click();
  await expect(confirm).toHaveCount(0);
  await expect(page.getByTestId("sheet-heading")).toContainText("SMTW — ");
  await expect(rowInput(row)).toHaveValue("50");

  // While a save runs, the picker is disabled
  let release;
  const held = new Promise((resolve) => { release = resolve; });
  await page.route(`**/api/equipment/${machine.id}/readings`, async (route) => {
    await held;
    await route.continue();
  });
  await saveReadings(page).click();
  await expect(picker).toBeDisabled();
  release();
  await expect(row.getByRole("status")).toHaveText("Saved");
  await expect(picker).toBeEnabled();

  // Nothing typed any more: the switch needs no question
  await picker.selectOption({ label: "BRICKS" });
  await expect(page.getByTestId("sheet-heading")).toContainText("BRICKS — ");
  await expect(page.getByTestId("discard-confirm")).toHaveCount(0);
});

test("S040: clearing the typed readings closes the picker's question (CR2-02)", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40clear", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await asPerson(page, "manager", "/readings");
  const picker = page.getByLabel("Site", { exact: true });
  await picker.selectOption({ label: "SMTW" });
  const input = rowInput(sheetRow(sheetCard(page, machine), "Run hours"));
  await input.fill("50");
  await picker.selectOption({ label: "BRICKS" });
  await expect(page.getByTestId("discard-confirm")).toBeVisible();
  await input.fill("");
  await expect(page.getByTestId("discard-confirm")).toHaveCount(0);
  await expect(page.getByTestId("sheet-heading")).toContainText("SMTW — ");
});

test("S040: Discard on the picker's question switches site and drops the typed readings (CR1-02)", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40discard", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await asPerson(page, "manager", "/readings");
  const picker = page.getByLabel("Site", { exact: true });
  await picker.selectOption({ label: "SMTW" });
  await rowInput(sheetRow(sheetCard(page, machine), "Run hours")).fill("50");
  await picker.selectOption({ label: "BRICKS" });
  await page.getByTestId("discard-confirm").getByRole("button", { name: "Discard" }).click();
  await expect(page.getByTestId("sheet-heading")).toContainText("BRICKS — ");
  await picker.selectOption({ label: "SMTW" });
  await expect(page.getByTestId("sheet-heading")).toContainText("SMTW — ");
  await expect(rowInput(sheetRow(sheetCard(page, machine), "Run hours"))).toHaveValue("");
});

test("S040: a 404 on the sheet forgets the site and offers the sites that are left (CR1-05)", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/readings/sheet", 404);
  let first = true;
  await page.route("**/api/readings/sheet**", async (route) => {
    if (!first) return route.continue();
    first = false;
    return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: "Not found" }) });
  });
  await asPerson(page, "manager", "/readings");
  await expect(page.getByRole("alert")).toHaveText("This site is no longer available. Pick another site.");
  expect(await page.evaluate((key) => localStorage.getItem(key), SITE_KEY)).toBeNull();
  const picker = page.getByLabel("Site", { exact: true });
  await expect(picker.locator("option:not([disabled])")).toHaveCount(1); // the site that answered 404 is not offered again
  await picker.selectOption({ index: 1 });
  await expect(page.getByTestId("sheet-heading")).toBeVisible();
});

test("S040: a 404 with no site left shows the no-units message, not an empty picker (CR1-03)", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/readings/sheet", 404);
  await page.route("**/api/readings/sheet**", (route) => route.fulfill({
    status: 404, contentType: "application/json", body: JSON.stringify({ error: "Not found" }),
  }));
  await asPerson(page, "operator", "/readings");
  await expect(page.getByText("You have no units assigned — ask IT admin for unit access.")).toBeVisible();
  await expect(page.getByLabel("Site", { exact: true })).toHaveCount(0);
  await expect(page.getByText("This site is no longer available.")).toHaveCount(0);
  expect(await page.evaluate((key) => localStorage.getItem(key), SITE_KEY)).toBeNull();
});

// ---------------------------------------------------------------------------
// S040 A1: Enter more readings after a save.
// ---------------------------------------------------------------------------

const enterMore = (page) => page.getByRole("button", { name: "Enter more readings" });

test("S040 A1: a full save makes the round read-only, and Enter more readings starts a fresh one", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40a1new", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  await openSheet(page, "engineer");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  const oil = sheetRow(sheetCard(page, machine), "Oil temperature");
  await expect(enterMore(page)).toHaveCount(0); // nothing saved yet
  await setEventTime(page, istLocal(30)); // so the next round, at now, is another minute
  await rowInput(hours).fill("100");
  await saveReadings(page).click();

  // The whole round is read-only; the button reads Saved and is disabled
  await expect(hours.getByRole("status")).toHaveText("Saved");
  await expect(rowInput(hours)).toHaveAttribute("readonly", "");
  await expect(rowInput(oil)).toHaveAttribute("readonly", ""); // an empty row is locked too
  await expect(page.locator("input[type=datetime-local]")).toHaveAttribute("readonly", ""); // Time of reading is locked
  await expect(page.getByRole("checkbox", { name: "Now", exact: true })).toBeDisabled(); // S051
  await expect(page.getByRole("button", { name: "Saved", exact: true })).toBeDisabled();
  await expect(saveReadings(page)).toHaveCount(0);
  await expect(enterMore(page)).toBeVisible();
  expect((await enterMore(page).boundingBox()).height).toBeGreaterThanOrEqual(44);
  await expectNoSidewaysScroll(page);

  await enterMore(page).click();
  await expect(enterMore(page)).toHaveCount(0);
  await expect(rowInput(hours)).toHaveValue("");
  await expect(rowInput(hours)).not.toHaveAttribute("readonly", "");
  await expect(rowInput(oil)).not.toHaveAttribute("readonly", ""); // editable again
  await expect(hours.getByRole("status")).toHaveCount(0);
  await expect(hours.getByRole("button", { name: "Undo" })).toHaveCount(0); // no Undo of the old round
  await expect(page.getByRole("checkbox", { name: "Now", exact: true })).toBeEnabled(); // Time of reading is back to Now (S051)
  await expect(page.getByRole("checkbox", { name: "Now", exact: true })).toBeChecked();
  await expect(hours.getByTestId("sheet-last")).toContainText("100.0 h"); // the round just saved is the last reading
  await expect(saveReadings(page)).toBeDisabled(); // nothing typed yet

  await rowInput(hours).fill("110");
  await saveReadings(page).click();
  await expect(hours.getByRole("status")).toHaveText("Saved");
});

test("S040 A1: a partial save keeps the refused row editable and offers no Enter more readings", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/readings", 400);
  const machine = await meterMachine(testInfo, "s40a1part", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  await logByApi(machine, "Run hours", "1000", istLocal(60));
  await openSheet(page, "engineer");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  const oil = sheetRow(sheetCard(page, machine), "Oil temperature");
  await rowInput(hours).fill("900"); // lower than the last: refused
  await rowInput(oil).fill("40");
  await saveReadings(page).click();
  await expect(oil.getByRole("status")).toHaveText("Saved");
  await expect(hours.getByRole("alert")).toBeVisible();
  await expect(rowInput(hours)).not.toHaveAttribute("readonly", "");
  await expect(rowInput(oil)).toHaveAttribute("readonly", "");
  await expect(saveReadings(page)).toBeEnabled();
  await expect(enterMore(page)).toHaveCount(0);

  // The retry saves the refused row; only then is the round done
  await hours.getByLabel("Meter reset").check();
  await saveReadings(page).click();
  await expect(hours.getByRole("status")).toHaveText("Saved");
  await expect(page.getByRole("button", { name: "Saved", exact: true })).toBeDisabled();
  await expect(enterMore(page)).toBeVisible();
});

test("S040 A1: the same meter at the same minute is refused in the next round; another meter is not", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/readings", 409);
  const machine = await meterMachine(testInfo, "s40a1same", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  const taken = istLocal(30);
  await openSheet(page, "engineer");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  const oil = sheetRow(sheetCard(page, machine), "Oil temperature");
  await setEventTime(page, taken);
  await rowInput(hours).fill("100");
  await saveReadings(page).click();
  await expect(hours.getByRole("status")).toHaveText("Saved");

  await enterMore(page).click();
  await setEventTime(page, taken); // back to the same minute
  await rowInput(hours).fill("110");
  await rowInput(oil).fill("40");
  await saveReadings(page).click();
  await expect(oil.getByRole("status")).toHaveText("Saved"); // another meter is not blocked
  await expect(hours.getByRole("alert")).toHaveText(SAME_MINUTE);
  await expect(rowInput(hours)).toHaveValue("110"); // kept, editable
  await expect(enterMore(page)).toHaveCount(0); // a row is left to retry
});

test("S040 A1: emptying a refused row to retype it does not lock the round (CR4-01)", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/readings", 400);
  const machine = await meterMachine(testInfo, "s40a1clear", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  await logByApi(machine, "Run hours", "1000", istLocal(60));
  await openSheet(page, "engineer");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  const oil = sheetRow(sheetCard(page, machine), "Oil temperature");
  await rowInput(hours).fill("900"); // lower than the last: refused
  await rowInput(oil).fill("40");
  await saveReadings(page).click();
  await expect(oil.getByRole("status")).toHaveText("Saved");
  await expect(hours.getByRole("alert")).toBeVisible();

  // Backspace to the empty field, as on a phone keypad: the field still takes input
  await rowInput(hours).fill("");
  await expect(rowInput(hours)).not.toHaveAttribute("readonly", "");
  await expect(page.getByRole("checkbox", { name: "Now", exact: true })).toBeEnabled(); // Time of reading is not locked (S051)
  await rowInput(hours).pressSequentially("1100");
  await expect(rowInput(hours)).toHaveValue("1100");
  await expect(saveReadings(page)).toBeEnabled();
  await saveReadings(page).click();
  await expect(hours.getByRole("status")).toHaveText("Saved");
  await expect(enterMore(page)).toBeVisible();
});

test("S040 A1: after a partial save, giving up the refused row offers Enter more readings (CR5-01)", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/readings", 400);
  const machine = await meterMachine(testInfo, "s40a1giveup", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  await logByApi(machine, "Run hours", "1000", istLocal(60));
  await openSheet(page, "engineer");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  const oil = sheetRow(sheetCard(page, machine), "Oil temperature");
  await rowInput(hours).fill("900"); // lower than the last: refused
  await rowInput(oil).fill("40");
  await saveReadings(page).click();
  await expect(oil.getByRole("status")).toHaveText("Saved");
  await expect(hours.getByRole("alert")).toBeVisible();
  await expect(enterMore(page)).toHaveCount(0); // a row is left to retry

  await rowInput(hours).fill(""); // the meter is broken: skip the reading
  await expect(enterMore(page)).toBeVisible();
  await expect(rowInput(hours)).not.toHaveAttribute("readonly", ""); // not locked
  await expect(rowInput(oil)).toHaveAttribute("readonly", "");

  await enterMore(page).click();
  await expect(rowInput(oil)).not.toHaveAttribute("readonly", ""); // a fresh round
  await expect(rowInput(oil)).toHaveValue("");
  await expect(rowInput(hours)).toHaveValue("");
});

test("S040 A1: Undo after a full save of two rows opens the round, and the row can be cleared and retyped (CR4-01)", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40a1undo", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  await openSheet(page, "engineer");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  const oil = sheetRow(sheetCard(page, machine), "Oil temperature");
  await rowInput(hours).fill("100");
  await rowInput(oil).fill("40");
  await saveReadings(page).click();
  await expect(hours.getByRole("status")).toHaveText("Saved");
  await expect(oil.getByRole("status")).toHaveText("Saved");
  await expect(enterMore(page)).toBeVisible();

  await oil.getByRole("button", { name: "Undo" }).click();
  await expect(rowInput(oil)).not.toHaveAttribute("readonly", "");
  await expect(enterMore(page)).toHaveCount(0);
  await rowInput(oil).fill(""); // the wrong value is wiped to type the right one
  await expect(rowInput(oil)).not.toHaveAttribute("readonly", "");
  await rowInput(oil).pressSequentially("45");
  await expect(rowInput(oil)).toHaveValue("45");
  await saveReadings(page).click();
  await expect(oil.getByRole("status")).toHaveText("Saved");
  await expect(enterMore(page)).toBeVisible();
});

test("S040 A1: switching the site after a saved round asks nothing", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s40a1site", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await asPerson(page, "manager", "/readings");
  const picker = page.getByLabel("Site", { exact: true });
  await picker.selectOption({ label: "SMTW" });
  await expect(page.getByTestId("sheet-heading")).toContainText("SMTW — ");
  const row = sheetRow(sheetCard(page, machine), "Run hours");
  await rowInput(row).fill("50");
  await saveReadings(page).click();
  await expect(row.getByRole("status")).toHaveText("Saved");
  await expect(enterMore(page)).toBeVisible();

  await picker.selectOption({ label: "BRICKS" });
  await expect(page.getByTestId("sheet-heading")).toContainText("BRICKS — ");
  await expect(page.getByTestId("discard-confirm")).toHaveCount(0);
});

// S051: the time field shows the time, with a Now tick
const nowBox = (scope) => scope.getByRole("checkbox", { name: "Now", exact: true });
const timeInput = (scope) => scope.locator("input[type=datetime-local]");

test("S051: Log reading opens with Now ticked and the time read-only; unticking makes it editable, ticking again read-only", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s51now", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const dialog = await openLog(page, "Run hours");
  await expect(nowBox(dialog)).toBeChecked();
  await expect(timeInput(dialog)).toHaveAttribute("readonly", "");
  // the phone's clock to the minute; a minute boundary during the test does not fail it
  const shown = await timeInput(dialog).inputValue();
  expect([istLocal(0), istLocal(1)]).toContain(shown);

  await nowBox(dialog).uncheck();
  await expect(timeInput(dialog)).not.toHaveAttribute("readonly", "");
  await timeInput(dialog).fill(istLocal(90));
  await expect(timeInput(dialog)).toHaveValue(istLocal(90));

  await nowBox(dialog).check();
  await expect(timeInput(dialog)).toHaveAttribute("readonly", "");
  expect([istLocal(0), istLocal(1)]).toContain(await timeInput(dialog).inputValue());
});

test("S051: emptying the time to retype it keeps the field unticked and editable (BR1-01)", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s51clear", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const dialog = await openLog(page, "Run hours");
  await nowBox(dialog).uncheck();
  await timeInput(dialog).fill(istLocal(90));
  await timeInput(dialog).fill(""); // what Chrome reports while a part of the date is deleted
  await expect(nowBox(dialog)).not.toBeChecked();
  await expect(timeInput(dialog)).not.toHaveAttribute("readonly", "");
  await timeInput(dialog).fill(istLocal(60));
  await expect(timeInput(dialog)).toHaveValue(istLocal(60));
  await expect(nowBox(dialog)).not.toBeChecked();
});

test("S051: the time field and the Now box fit on one line, and the Now label is a 44 px tap target", { tag: "@device" }, async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s51fit", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const dialog = await openLog(page, "Run hours");
  await expectDialogFits(page);
  const input = await timeInput(dialog).boundingBox();
  const box = await nowBox(dialog).boundingBox();
  expect(box.x).toBeGreaterThanOrEqual(input.x + input.width - 1); // to the right, not below
  expect(Math.abs((box.y + box.height / 2) - (input.y + input.height / 2))).toBeLessThan(input.height / 2); // one line
  // The tap target is the label that toggles the box (CR1-02), not a wrapper around it
  const tap = dialog.locator("label[for=reading-now]");
  expect((await tap.boundingBox()).height).toBeGreaterThanOrEqual(44);
  await tap.click({ position: { x: 4, y: 3 } }); // the top edge of the area, away from the word
  await expect(nowBox(dialog)).not.toBeChecked();
});

test("S051: untouched and unticked, the time follows the clock and the save sends no taken_at (BR1-02)", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s51follow", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await page.clock.install(); // a fake clock, so a minute passes without waiting
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  const dialog = await openLog(page, "Run hours");
  await nowBox(dialog).uncheck();
  const before = await timeInput(dialog).inputValue();
  await page.clock.runFor(60_000);
  await expect.poll(() => timeInput(dialog).inputValue()).not.toBe(before); // moved on, still editable
  await expect(timeInput(dialog)).not.toHaveAttribute("readonly", "");
  await dialog.getByLabel("Value", { exact: true }).fill("55");
  const sent = page.waitForRequest((req) => req.method() === "POST" && req.url().endsWith(`/api/equipment/${machine.id}/readings`));
  await saveDialog(page, "Save");
  expect(JSON.parse((await sent).postData())).not.toHaveProperty("taken_at");
});

test("S051: Log reading opens again with Now ticked, also after the time was emptied and the dialog closed (CR1-01)", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s51reopen", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  let dialog = await openLog(page, "Run hours");
  await nowBox(dialog).uncheck();
  await timeInput(dialog).fill(istLocal(90));
  await timeInput(dialog).fill("");
  await dialog.locator(".modal-footer").getByRole("button", { name: "Cancel" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);

  dialog = await openLog(page, "Oil temperature");
  await expect(nowBox(dialog)).toBeChecked();
  await expect(timeInput(dialog)).toHaveAttribute("readonly", "");
  expect([istLocal(0), istLocal(1)]).toContain(await timeInput(dialog).inputValue());
});

test("S051: Enter more readings starts the next round with Now ticked and the time of now (CR1-01)", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s51more", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await openSheet(page, "engineer");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  const time = page.locator("input[type=datetime-local]");
  await page.getByRole("checkbox", { name: "Now", exact: true }).uncheck();
  await time.fill(istLocal(90));
  await time.fill(""); // emptied: unticked, and the time sent is the server's
  await rowInput(hours).fill("100");
  await saveReadings(page).click();
  await expect(hours.getByRole("status")).toHaveText("Saved");
  await enterMore(page).click();
  await expect(page.getByRole("checkbox", { name: "Now", exact: true })).toBeChecked();
  await expect(time).toHaveAttribute("readonly", "");
  expect([istLocal(0), istLocal(1)]).toContain(await time.inputValue());
});

// S050: the meter reading register, a Register tab on Readings and Open register on the Meters card
const registerRows = (page) => page.getByTestId("register-row");
const registerHeaders = (page) => page.getByTestId("register-frame").locator("thead th");
const picker = (page) => page.getByLabel("Which equipment?");
const tabButton = (page, name) => page.getByRole("button", { name, exact: true });
const chooser = (page) => page.getByRole("button", { name: /^Meters: / });

/** Readings of `node` through the API as the operator, one request each: [meter name, value, takenAt]. */
async function logReadings(node, entries) {
  const api = await apiAs("operator");
  try {
    const types = (await (await api.get("/api/masters/meter-types")).json()).items;
    for (const [name, value, takenAt] of entries) {
      const res = await api.post(`/api/equipment/${node.id}/readings`, {
        data: { meter_type_id: types.find((t) => t.name === name).id, value, taken_at: takenAt },
      });
      expect(res.status(), await res.text()).toBe(201);
    }
  } finally {
    await api.dispose();
  }
}

/** A component-unit under `machine`, of the machine's model, with its own meters (names), as admin. */
async function partOf(machine, name, meterNames) {
  const api = await apiAs("admin");
  try {
    const types = (await (await api.get("/api/masters/meter-types")).json()).items;
    const res = await api.post("/api/equipment", {
      data: { level: "component_unit", parent_id: machine.id, model_id: machine.model_id, name },
    });
    expect(res.status(), await res.text()).toBe(201);
    const part = await res.json();
    for (const meter of meterNames) {
      const added = await api.post(`/api/equipment/${part.id}/meters`, { data: { meter_type_id: types.find((t) => t.name === meter).id } });
      expect(added.status(), await added.text()).toBe(201);
    }
    return part;
  } finally {
    await api.dispose();
  }
}

async function pickInRegister(page, code) {
  await picker(page).fill(code);
  await page.getByRole("button", { name: new RegExp(`^${code} — `) }).click();
}

test("S050: Open register on a press's Meters card shows a row per reading time, newest first, a column per meter, High on an over-limit gauge", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s50card", {
    unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", { max_value: "60" }]],
  });
  const [first, second, third] = [istLocal(90), istLocal(60), istLocal(30)];
  await logReadings(machine, [
    ["Run hours", "100", first], ["Oil temperature", "50", first],
    ["Run hours", "110", second], ["Oil temperature", "65", second],
    ["Run hours", "120", third],
  ]);
  await asPerson(page, "engineer", `/equipment/${machine.id}`);
  await card(page, "Meters").getByRole("link", { name: "Open register" }).click();
  await expect(page).toHaveURL(new RegExp(`/readings\\?tab=register&node=${machine.id}$`));
  await expect(page.getByTestId("register-node")).toContainText(`${machine.code} — ${machine.name}`);
  // The meters in the Meters card's order (by name); the time first
  await expect(registerHeaders(page)).toHaveText(["Time", "Oil temperature (°C)", "Run hours (h)"]);
  await expect(registerRows(page)).toHaveCount(3);
  await expect(registerRows(page).locator("th")).toHaveText([shownTime(third), shownTime(second), shownTime(first)]);
  const cells = (row) => registerRows(page).nth(row).locator("td");
  await expect(cells(0)).toHaveText(["", "120.0"]); // no oil reading at that minute: an empty cell
  await expect(cells(1).nth(0)).toHaveText(/^65\.0\s*High$/); // the number only: the unit is in the header
  await expect(cells(1).nth(0).locator(".badge")).toHaveText("High");
  await expect(cells(2)).toHaveText(["50.0", "100.0"]);
});

test("S050: unticking all but one meter leaves its column and the times it was read; the URL keeps it after a reload", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s50tick", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  const [first, second, third] = [istLocal(90), istLocal(60), istLocal(30)];
  await logReadings(machine, [
    ["Run hours", "100", first], ["Oil temperature", "50", first], ["Oil temperature", "52", second], ["Run hours", "120", third],
  ]);
  await asPerson(page, "engineer", `/readings?tab=register&node=${machine.id}`);
  await expect(registerRows(page)).toHaveCount(3);
  await expect(chooser(page)).toHaveText("Meters: All");
  await chooser(page).click();
  await page.getByRole("checkbox", { name: "Oil temperature (°C)" }).uncheck();
  await expect(registerHeaders(page)).toHaveText(["Time", "Run hours (h)"]);
  await expect(registerRows(page).locator("th")).toHaveText([shownTime(third), shownTime(first)]);
  await expect(page).toHaveURL(/&meters=\d+$/);
  // The last tick cannot be cleared
  await expect(page.getByRole("checkbox", { name: "Run hours (h)" })).toBeDisabled();

  await page.reload();
  await expect(registerHeaders(page)).toHaveText(["Time", "Run hours (h)"]);
  await expect(registerRows(page)).toHaveCount(2);
  await expect(chooser(page)).toHaveText("Meters: 1 of 2");
  await chooser(page).click();
  await page.getByRole("button", { name: "Show all" }).click();
  await expect(registerHeaders(page)).toHaveText(["Time", "Oil temperature (°C)", "Run hours (h)"]);
  await expect(page).not.toHaveURL(/meters=/);
});

test("S050: a value typed on the sheet is still there after a look at the Register tab (BR1-01)", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s50keep", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await openSheet(page, "supervisor");
  const hours = sheetRow(sheetCard(page, machine), "Run hours");
  await rowInput(hours).fill("123");
  await tabButton(page, "Register").click();
  await expect(picker(page)).toBeVisible();
  await expect(page.getByTestId("sheet-heading")).toBeHidden();
  await tabButton(page, "Sheet").click();
  await expect(rowInput(hours)).toHaveValue("123");
  await expect(page.getByTestId("filled-count")).toContainText("1 of");
});

test("S050: the search finds a component-unit by code, its row shows the full path, and the register shows its own meters", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s50part", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  const motor = await partOf(machine, `S050 motor ${testInfo.project.name}`, ["Energy"]);
  const taken = istLocal(30);
  await logReadings(motor, [["Energy", "4500.5", taken]]);
  await logReadings(machine, [["Run hours", "100", taken]]);
  await asPerson(page, "engineer", "/readings?tab=register");
  await expect(page.getByTestId("register-empty")).toHaveText("Find a machine or part to see its readings.");
  await picker(page).fill(motor.code);
  const result = page.getByRole("button", { name: new RegExp(`^${motor.code} — `) });
  await expect(result).toContainText(motor.full_path);
  await result.click();
  await expect(page.getByTestId("register-node")).toContainText(motor.full_path);
  await expect(registerHeaders(page)).toHaveText(["Time", "Energy (kWh)"]); // not the machine's Run hours (U2)
  await expect(registerRows(page)).toHaveCount(1);
  await expect(registerRows(page).first().locator("td")).toHaveText(["4,500.5"]);
});

test("S050: a link with a stale meters id opens the register with the remaining columns and no error", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s50stale", { unit: UNIT, ownMeters: [["Run hours", {}], ["Oil temperature", {}]] });
  await logReadings(machine, [["Run hours", "100", istLocal(60)], ["Oil temperature", "40", istLocal(30)]]);
  await asPerson(page, "engineer", `/readings?tab=register&node=${machine.id}&meters=999999999`);
  await expect(registerHeaders(page)).toHaveText(["Time", "Oil temperature (°C)", "Run hours (h)"]);
  await expect(registerRows(page)).toHaveCount(2);
  await expect(chooser(page)).toHaveText("Meters: All");
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("S050: Show more adds the next 30 rows with no row twice", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s50more", { unit: UNIT, ownMeters: [["Oil temperature", {}]] });
  const times = Array.from({ length: 32 }, (_, i) => istLocal(10 * (i + 1)));
  await logReadings(machine, times.map((taken, i) => ["Oil temperature", String(20 + i), taken]));
  await asPerson(page, "engineer", `/readings?tab=register&node=${machine.id}`);
  await expect(registerRows(page)).toHaveCount(30);
  // A reading logged meanwhile shifts the next page by one row: no time may show twice (§ 5.3.5)
  const newest = istLocal(5);
  await logReadings(machine, [["Oil temperature", "99", newest]]);
  await page.getByRole("button", { name: "Show more" }).click();
  await expect(registerRows(page)).toHaveCount(32);
  const shown = await registerRows(page).locator("th").allTextContents();
  expect(shown).toEqual(times.map(shownTime));
  // No third page: the reading logged meanwhile is newer than the first page, not after the last one
  await expect(page.getByRole("button", { name: "Show more" })).toHaveCount(0);
});

test("S050: the storekeeper sees Readings in the nav with only the Register tab, opens a machine's register, and ?tab=sheet opens Register", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s50store", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await logReadings(machine, [["Run hours", "250", istLocal(30)]]);
  await asPerson(page, "storekeeper", "/");
  await page.getByRole("button", { name: "Readings", exact: true }).filter({ visible: true }).click();
  await expect(page).toHaveURL(/\/readings$/);
  await expect(picker(page)).toBeVisible();
  await expect(tabButton(page, "Sheet")).toHaveCount(0);
  await expect(tabButton(page, "Register")).toHaveCount(0); // a single tab: no tab bar
  await pickInRegister(page, machine.code);
  await expect(registerRows(page)).toHaveCount(1);
  await expect(registerRows(page).first().locator("td")).toHaveText(["250.0"]);

  await page.goto("/readings?tab=sheet");
  await expect(picker(page)).toBeVisible();
  await expect(page.getByTestId("sheet-heading")).toHaveCount(0);
});

test("S050: after a pick the search hides and the node card shows; the X (Clear and choose another) brings the search back", async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, "s50change", { unit: UNIT, ownMeters: [["Run hours", {}]] });
  await asPerson(page, "engineer", "/readings?tab=register");
  await pickInRegister(page, machine.code);
  await expect(page.getByTestId("register-node")).toContainText(`${machine.code} — ${machine.name}`);
  await expect(picker(page)).toBeHidden();
  await expect(page.getByText("No readings yet.")).toBeVisible();
  await expect(page.getByTestId("register-node").getByRole("link", { name: "Open equipment page" }))
    .toHaveAttribute("href", `/equipment/${machine.id}`);
  await page.getByTestId("register-node").getByRole("button", { name: "Clear and choose another" }).click();
  await expect(picker(page)).toBeVisible();
  // The earlier search text and its matches are still there (S050 CR1-01)
  await expect(picker(page)).toHaveValue(machine.code);
  await expect(page.getByRole("button", { name: new RegExp(`^${machine.code} — `) })).toBeVisible();
  await expect(page).toHaveURL(/\/readings\?tab=register$/);
});

test("S050: a failed Show more shows its message and Try again under the table, where Show more was (CR1-02)", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/readings/register", 503); // the failure is the point of the test
  const machine = await meterMachine(testInfo, "s50morefail", { unit: UNIT, ownMeters: [["Oil temperature", {}]] });
  await logReadings(machine, Array.from({ length: 32 }, (_, i) => ["Oil temperature", String(20 + i), istLocal(10 * (i + 1))]));
  let failPage2 = true;
  await page.route(`**/api/equipment/${machine.id}/readings/register?*page=2*`, async (route) => {
    if (failPage2) await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: "down" }) });
    else await route.continue();
  });
  await asPerson(page, "engineer", `/readings?tab=register&node=${machine.id}`);
  await expect(registerRows(page)).toHaveCount(30);
  await page.getByRole("button", { name: "Show more" }).click();
  const failure = page.getByTestId("register-more-error");
  await expect(failure).toContainText("Readings could not be loaded. Try again in a minute.");
  await expect(failure).toBeInViewport(); // next to the table's foot, not above the node card
  await expect(page.getByRole("button", { name: "Show more" })).toHaveCount(0);
  failPage2 = false;
  await failure.getByRole("button", { name: "Try again" }).click();
  await expect(registerRows(page)).toHaveCount(32);
  await expect(failure).toHaveCount(0);
});

test("S050: a link to a machine that does not exist shows the not-found message with the search under it (CR1-06)", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/readings/register", 404); // the refusal is the point of the test
  await asPerson(page, "engineer", "/readings?tab=register&node=999999999");
  await expect(page.getByRole("alert")).toHaveText("This machine was not found, or you have no access to it. Find another machine.");
  await expect(picker(page)).toBeVisible();
  await expect(page.getByTestId("register-empty")).toHaveCount(0);
});

test("S050: the meter columns scroll sideways inside the table's frame, not the page, and the time column stays in view", { tag: "@device" }, async ({ page }, testInfo) => {
  // Every seed meter type and the Yes / No one: enough columns to overflow a 1366 px desktop too
  const names = ["Run hours", "Strokes", "Production counter", "Energy", "Odometer", "Oil temperature", "Fuel level",
    "Shift production", questionName];
  const machine = await meterMachine(testInfo, "s50wide", { unit: UNIT, ownMeters: names.map((n) => [n, {}]) });
  await logReadings(machine, [["Run hours", "100", istLocal(30)]]);
  await asPerson(page, "engineer", `/readings?tab=register&node=${machine.id}`);
  await expect(registerHeaders(page)).toHaveCount(names.length + 1);
  const frame = page.getByTestId("register-frame");
  const sizes = await frame.evaluate((el) => ({ scroll: el.scrollWidth, client: el.clientWidth }));
  expect(sizes.scroll, "the frame does not scroll sideways").toBeGreaterThan(sizes.client);
  await expectNoSidewaysScroll(page);
  const time = registerRows(page).first().locator("th");
  await expect(time).toBeInViewport();
  await frame.evaluate((el) => { el.scrollLeft = el.scrollWidth; });
  await expect(time).toBeInViewport();
  const frameBox = await frame.boundingBox();
  const timeBox = await time.boundingBox();
  expect(timeBox.x, "the time column moved with the meters").toBeLessThanOrEqual(frameBox.x + 2);
  await expectNoSidewaysScroll(page);
});
