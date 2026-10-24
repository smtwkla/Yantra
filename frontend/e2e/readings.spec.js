// Meter readings from the equipment page (S039 § 1.3, § 1.4, § 8).
//
// Set-up (BR1-09, BR2-04, BS1-03): the three projects share one database, so no test reads or
// writes a seed node.  Each test makes its own machine at SMTW.MCC2 (the operator's unit) with
// S038's meterMachine, of a press model of its own, so no seed model is touched and no test
// depends on another's readings or order.  The Yes / No meter type is made once per project in
// beforeAll (no Yes / No seed, S037 decision 8).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, openDialog } from "./support/dialogs.js";
import { logByApi, meterMachine } from "./support/meters.js";
import { apiAs, asPerson } from "./support/people.js";
import { card, istLocal, saveDialog, shownTime } from "./support/tickets.js";

const UNIT = "SMTW.MCC2";
const MIN_TOUCH_PX = 48; // the Yes / No buttons on a phone (U3)
const NOW_TIME = /\d{2}-\d{2}-\d{4} \d{2}:\d{2}/;

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
  await expect(dialog).toContainText("Time taken");
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
