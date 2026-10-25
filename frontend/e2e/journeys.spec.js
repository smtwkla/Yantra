// The journeys (S047 § 1.4): the Basic level's smoke tests.  Each test walks one real piece of
// work from start to end through the screens and checks what each person sees at each stage.
// They repeat checks the other specs make in detail; that is their purpose: one run shows the app
// works end to end.  Tagged @smoke (tooling/run-e2e-tests.bat --level=basic) and not @device, so
// at Normal and at Full they run on phone-chromium only (S055).  Names carry the project and a
// run-unique suffix: projects may share a lane's database.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "./support/test.js";
import { expectDialogFits, openDialog } from "./support/dialogs.js";
import { meterMachine } from "./support/meters.js";
import { apiAs, asPerson } from "./support/people.js";
import { card, istLocal, openAction, saveDialog, setEventTime, stateBadge, thisMinute, timeline } from "./support/tickets.js";

const MANUAL = path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", "test-manual.pdf");
const SMOKE = { tag: "@smoke" };
const OPERATOR_UNIT = "MCC2"; // the seed operator's unit (seed_e2e.PEOPLE)

let added; // journey 1's equipment item {id, code, name}, raised on in journey 2

const unique = (testInfo, what) => `E2E journey ${what} ${testInfo.project.name} ${Date.now().toString(36)}`;

/** Choose the option of `select` whose text contains `text` (labels carry more than the name). */
async function chooseOption(select, text) {
  const value = await select.locator("option", { hasText: text }).first().getAttribute("value");
  await select.selectOption(value);
}

/** A dialog opened by clicking `button`; it must fit -> the dialog. */
async function dialogFrom(page, button) {
  await button.click();
  await expectDialogFits(page);
  return openDialog(page);
}

/** The equipment page's "<code> — <name>" heading -> the code. */
async function shownCode(page, name) {
  const heading = page.getByRole("heading", { name: new RegExp(` — ${name}$`) });
  await expect(heading).toBeVisible();
  return (await heading.textContent()).split(" — ")[0].trim();
}

/** An equipment item at the operator's unit, through the API (journey 2 run alone, without journey 1). */
async function equipmentByApi(name) {
  const api = await apiAs("admin");
  try {
    const items = async (url) => (await (await api.get(url)).json()).items;
    const [units, models] = await Promise.all([items("/api/masters/units"), items("/api/masters/equipment-models")]);
    const res = await api.post("/api/equipment", {
      data: { level: "equipment", unit_id: units.find((u) => u.full_code === `SMTW.${OPERATOR_UNIT}`).id,
              model_id: models.find((m) => m.designation === "GA37").id, name },
    });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/** The Add equipment dialog from the equipment list, filled and saved; the new page opens. */
async function addEquipment(page, { name, unit, model }) {
  await page.goto("/equipment");
  const dialog = await dialogFrom(page, page.getByRole("button", { name: "Add equipment" }));
  await dialog.getByLabel("Site").selectOption({ label: "SMTW" });
  await chooseOption(dialog.getByLabel("Unit"), new RegExp(`^${unit} — `));
  await chooseOption(dialog.getByLabel("Model"), model);
  await dialog.getByLabel("Name").fill(name);
  await saveDialog(page, "Save");
  return shownCode(page, name);
}

test("S047 journey 1: the engineer adds an equipment item, uploads its manual and prints its QR label", SMOKE, async ({ page }, testInfo) => {
  const name = unique(testInfo, "compressor");
  await asPerson(page, "engineer", "/equipment");
  const code = await addEquipment(page, { name, unit: OPERATOR_UNIT, model: "Atlas Copco GA37" });
  await expect(page.getByText(`SMTW.${OPERATOR_UNIT}`).first()).toBeVisible();
  added = { id: Number(page.url().match(/\/equipment\/(\d+)/)[1]), code, name };

  const upload = await dialogFrom(page, page.getByRole("button", { name: "Add document" }));
  await upload.getByLabel("File").setInputFiles(MANUAL);
  await upload.getByLabel("Title").fill("Service manual");
  await saveDialog(page, "Upload");
  await expect(card(page, "Documents")).toContainText("Service manual");
  await expect(card(page, "Documents")).toContainText("test-manual.pdf");

  await page.getByRole("button", { name: /Print label/ }).click();
  const [labels] = await Promise.all([
    page.context().waitForEvent("page"),
    page.getByRole("button", { name: "This node only" }).click(),
  ]);
  await expect(labels.getByText("1 label on 1 sheet")).toBeVisible();
  await expect(labels.locator(".label-code")).toHaveText([code]);
  await expect(labels.locator(".sheet .label .qr svg")).toBeVisible();
  await labels.close();
});

test("S047 journey 2: a breakdown from raise to close: assigned, worked with labour, a part and a note, back in service, closed", SMOKE, async ({ page }, testInfo) => {
  const machine = added ?? await equipmentByApi(unique(testInfo, "breakdown machine"));
  const problem = unique(testInfo, "breakdown: motor stopped");

  // The operator raises it from the equipment page
  await asPerson(page, "operator", `/equipment/${machine.id}`);
  await page.getByRole("link", { name: "Raise ticket" }).click();
  await page.getByRole("button", { name: /Stopped/ }).click();
  await page.getByLabel(/What is wrong\?/).fill(problem);
  await page.locator("form button[type=submit]").click();
  const saved = page.locator(".alert-success");
  await expect(saved).toContainText(/Ticket TK-\S+ saved\./);
  const serial = (await saved.locator("strong").textContent()).trim();
  await page.getByRole("button", { name: "Done" }).click();
  await expect(page.getByRole("heading", { name: serial })).toBeVisible();
  await expect(stateBadge(page)).toHaveText("Raised");
  const ticketPath = new URL(page.url()).pathname;

  // The engineer assigns the technician
  await asPerson(page, "engineer", ticketPath);
  const assign = await dialogFrom(page, page.getByRole("button", { name: "Assign" }));
  await assign.getByRole("button", { name: /Kannan \(technician\)/ }).click();
  await saveDialog(page, "Assign");
  await expect(card(page, "Assigned")).toContainText("Kannan (technician)");

  // The technician works it
  await asPerson(page, "technician", ticketPath);
  await openAction(page, "Acknowledge");
  await saveDialog(page, "Acknowledge");
  await expect(stateBadge(page)).toHaveText("Acknowledged");
  await openAction(page, "Start work");
  await saveDialog(page, "Start work");
  await expect(stateBadge(page)).toHaveText("In progress");

  const labour = await dialogFrom(page, card(page, "Labour").getByRole("button", { name: "Add labour" }));
  await expect(labour.locator(".fw-semibold", { hasText: "Kannan (technician)" })).toBeVisible();
  await labour.getByLabel("Minutes").fill("45");
  await saveDialog(page, "Save");
  await expect(card(page, "Labour")).toContainText("Kannan (technician)");

  const part = `Contactor ${serial}`;
  const parts = card(page, "Parts used");
  const addPart = await dialogFrom(page, parts.getByRole("button", { name: "Add part" }));
  await addPart.getByLabel("Description").fill(part);
  await expect(addPart.locator(".fitted-before")).toHaveCount(0); // a run-unique text matches no earlier line
  await saveDialog(page, "Save");
  await expect(parts.locator("li", { hasText: part })).toContainText(`1 nos · ${part}`);

  const note = await openAction(page, "Add note");
  await note.getByLabel("Note").fill("Contactor coil burnt; replaced");
  await saveDialog(page, "Save note");
  await expect(timeline(page).first()).toContainText("Contactor coil burnt; replaced");

  await openAction(page, "Back in service");
  await saveDialog(page, "Back in service");
  await expect(stateBadge(page)).toHaveText("Back in service");

  // The engineer closes it
  await asPerson(page, "engineer", ticketPath);
  const close = await openAction(page, "Close");
  await close.locator("#move-close-mode").selectOption({ index: 1 });
  await close.locator("#move-cause").selectOption({ index: 1 });
  await close.locator("#move-action").selectOption({ index: 1 });
  await saveDialog(page, "Close ticket");
  await expect(stateBadge(page)).toHaveText("Closed");

  // The operator's Me screen lists it under Closed
  await asPerson(page, "operator", "/equipment");
  await page.getByRole("button", { name: "Me", exact: true }).click();
  await expect(page.getByRole("button", { name: "Raised by me", exact: true })).toHaveAttribute("aria-current", "page");
  await page.getByRole("combobox", { name: "State" }).selectOption("closed");
  await expect(page.locator(".list-group-item").filter({ hasText: serial })).toContainText("Closed");
});

test("S047 journey 3: a supervisor logs a counter on the equipment page, then a higher one on the readings sheet; the history shows both", SMOKE, async ({ page }, testInfo) => {
  const machine = await meterMachine(testInfo, `journey ${Date.now().toString(36)}`, {
    unit: "SMTW.MCC1", ownMeters: [["Run hours", {}]],
  });
  // Two readings of one meter at the same minute are refused, and a counter must go up (S039, S040)
  const base = thisMinute();
  const first = istLocal(2, base);
  const second = istLocal(1, base);
  const meterRow = card(page, "Meters").getByTestId("node-meter").filter({ hasText: "Run hours" });

  await asPerson(page, "supervisor", `/equipment/${machine.id}`);
  const log = await dialogFrom(page, meterRow.getByRole("button", { name: "Log reading" }));
  await log.getByLabel("Value", { exact: true }).fill("500");
  await setEventTime(log, first);
  await saveDialog(page, "Save");
  await expect(meterRow.getByTestId("last-reading")).toContainText("500.0 h ·");

  await page.goto("/readings");
  await expect(page.getByTestId("sheet-heading")).toContainText("SMTW — ");
  const row = page.getByTestId("sheet-machine").filter({ hasText: machine.name })
    .getByTestId("sheet-meter").filter({ hasText: "Run hours" });
  await setEventTime(page, second);
  await row.locator("input.form-control").fill("508");
  await page.getByRole("button", { name: "Save readings" }).click();
  await expect(row.getByRole("status")).toHaveText("Saved");

  await page.goto(`/equipment/${machine.id}`);
  await expect(meterRow.getByTestId("last-reading")).toContainText("508.0 h ·");
  await meterRow.getByTestId("last-reading").click();
  const history = await openDialog(page);
  await expect(history.locator(".modal-title")).toHaveText("History · Run hours");
  await expect(history.getByTestId("reading-row")).toHaveCount(2);
  await expect(history.getByTestId("reading-row").filter({ hasText: "508.0 h" })).toHaveCount(1);
  await expect(history.getByTestId("reading-row").filter({ hasText: "500.0 h" })).toHaveCount(1);
});

test("S047 journey 4: IT admin adds a manufacturer and a model with a meter; an equipment item of the model shows the meter", SMOKE, async ({ page }, testInfo) => {
  const maker = unique(testInfo, "maker");
  const designation = `JX-${Date.now().toString(36)}`;
  await asPerson(page, "it_admin", "/masters");

  await page.getByRole("button", { name: "Manufacturers", exact: true }).click();
  const addMaker = await dialogFrom(page, page.getByRole("button", { name: "Add manufacturer" }));
  await addMaker.getByLabel("Name").fill(maker);
  await saveDialog(page, "Save");
  await expect(page.getByRole("row", { name: new RegExp(maker) })).toBeVisible();

  await page.getByRole("button", { name: "Models", exact: true }).click();
  const addModel = await dialogFrom(page, page.getByRole("button", { name: "Add model" }));
  await addModel.getByLabel("Manufacturer").selectOption({ label: maker });
  await addModel.locator("#model-class").selectOption({ index: 1 });
  await addModel.getByLabel("Designation").fill(designation);
  await saveDialog(page, "Save");
  const modelRow = page.getByRole("row", { name: new RegExp(`${maker} ${designation}`) });
  await expect(modelRow).toBeVisible();

  await modelRow.getByTitle("Meters").click();
  const header = page.locator(".card-header").filter({ hasText: "· Meters" });
  const addMeter = await dialogFrom(page, header.getByRole("button", { name: "Add meter" }));
  await chooseOption(addMeter.getByLabel("Meter type"), "Run hours");
  await saveDialog(page, "Save");
  await expect(page.getByTestId("model-meter").filter({ hasText: "Run hours" })).toBeVisible();

  const name = unique(testInfo, "machine of the new model");
  await addEquipment(page, { name, unit: "MCC1", model: `${maker} ${designation}` });
  const meterRow = card(page, "Meters").getByTestId("node-meter").filter({ hasText: "Run hours" });
  await expect(meterRow).toContainText("No readings yet");
});
