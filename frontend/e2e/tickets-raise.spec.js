// Raising tickets (S017) and S018 A1's *Already fixed* — in place of their manual checks.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, expectNoSidewaysScroll } from "./support/dialogs.js";
import { asPerson, seedIds } from "./support/people.js";
import {
  istLocal, raiseByApi, saveDialog, shownTime, stateBadge, thisMinute, timeline, timeValue,
} from "./support/tickets.js";

const PHOTO = path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", "test-photo.jpg");

let seed;

test.beforeAll(async () => {
  seed = await seedIds();
});

/** The raise form's Save button (its text follows Already fixed). */
const saveButton = (page) => page.locator("form button[type=submit]");

test("S017: raise from the equipment page, with a symptom and a photo; the ticket page shows them", async ({ page }) => {
  await asPerson(page, "operator", `/equipment/${seed.extruder.id}`);
  await page.getByRole("link", { name: "Raise ticket" }).click();
  await expect(page.getByText(`${seed.extruder.code} — ${seed.extruder.name}`)).toBeVisible();
  await expectNoSidewaysScroll(page);

  await page.getByRole("button", { name: /Stopped/ }).click();
  const symptom = page.getByLabel(/Symptom/);
  await symptom.selectOption({ index: 1 });
  const symptomLabel = (await symptom.locator("option:checked").textContent()).trim();
  await expect(saveButton(page)).toHaveText("Save ticket");
  await saveButton(page).click();

  const saved = page.locator(".alert-success");
  await expect(saved).toContainText(/Ticket TK-\S+ saved\./);
  const serial = (await saved.locator("strong").textContent()).trim();
  // The photo step: a file from the "gallery" (a real camera is a device check)
  await page.locator("input[type=file]").setInputFiles(PHOTO);
  await expect(page.locator(".list-group-item", { hasText: "test-photo.jpg" }).locator(".fa-check")).toBeVisible();
  await page.getByRole("button", { name: "Done" }).click();

  await expect(page.getByRole("heading", { name: serial })).toBeVisible();
  await expect(page.getByText("Breakdown", { exact: true }).first()).toBeVisible();
  await expect(stateBadge(page)).toHaveText("Raised");
  await expect(page.locator("dd", { hasText: symptomLabel })).toBeVisible();
  await expect(page.getByRole("img", { name: "test-photo" })).toBeVisible();
  await expect(timeline(page).last()).toContainText("Raised");
  await expect(timeline(page).last()).toContainText("e2e_operator");
});

test("S017: raise from the Tickets list naming a person with no login; the open ticket is listed first", async ({ page }) => {
  const earlier = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "initial", description: "Raise test: already open",
  });
  await asPerson(page, "supervisor", "/tickets");
  await page.getByRole("link", { name: "Raise ticket" }).click();
  await page.getByLabel("Which equipment?").fill(seed.extruder.name);
  await page.getByRole("button", { name: new RegExp(`^${seed.extruder.code} — `) }).click();

  // The machine's open tickets are listed before Save: a warning, not a block
  await expect(page.getByText("Already reported on this machine:")).toBeVisible();
  await expect(page.getByRole("link", { name: earlier.serial })).toBeVisible();

  await page.getByRole("button", { name: /Running, reduced/ }).click();
  await page.getByLabel(/What is wrong\?/).fill("Raise test: vibration at the cutter");
  await page.getByLabel(/Found by/).selectOption({ label: "Ramesh (operator, no phone) (Operator)" });
  await saveButton(page).click();
  await page.getByRole("button", { name: "Done" }).click();

  await expect(stateBadge(page)).toHaveText("Raised");
  await expect(page.locator("dt", { hasText: "Found by" }).locator("xpath=following-sibling::dd[1]"))
    .toHaveText("Ramesh (operator, no phone)");
  await expect(page.getByText("Raise test: vibration at the cutter")).toBeVisible();
});

test("S017: with no symptom and no description, the description is asked for", async ({ page }) => {
  await asPerson(page, "supervisor", "/tickets");
  await page.getByRole("link", { name: "Raise ticket" }).click();
  await page.getByLabel("Which equipment?").fill(seed.extruder.name);
  await page.getByRole("button", { name: new RegExp(`^${seed.extruder.code} — `) }).click();
  await page.getByRole("button", { name: /Running, reduced/ }).click();
  await saveButton(page).click();
  await expect(page.getByText("Describe the problem, or pick a symptom")).toBeVisible({ timeout: 3_000 });
});

test("S026: Save with nothing chosen scrolls the raise form to the first message", { tag: "@device" }, async ({ page }) => {
  await asPerson(page, "supervisor", "/tickets");
  await page.getByRole("link", { name: "Raise ticket" }).click();
  await page.getByLabel("Which equipment?").fill(seed.extruder.name);
  await page.getByRole("button", { name: new RegExp(`^${seed.extruder.code} — `) }).click();
  await expect(page.getByLabel(/What is wrong\?/)).toBeVisible();
  await saveButton(page).click();
  // "How bad is it?" is at the top of a long form; Save is at the bottom
  await expectFieldMessage(page, "Choose how bad it is");
  await page.getByRole("button", { name: /Running, reduced/ }).click();
  await saveButton(page).click();
  await expectFieldMessage(page, "Describe the problem, or pick a symptom");
  await expect(page.getByLabel(/What is wrong\?/)).toBeFocused();
});

test("S017: an operator sees only their unit's tickets; another unit's ticket is not found", async ({ page, consoleWatch }) => {
  const elsewhere = await raiseByApi("supervisor", {
    equipment_id: seed.mcc1Mill.id, intensity: "degraded", description: "Raise test: at MCC1",
  });
  const own = await raiseByApi("operator", {
    equipment_id: seed.extruder.id, intensity: "degraded", description: "Raise test: at MCC2",
  });
  await asPerson(page, "operator", "/tickets?state=all");
  await expect(page.getByText(own.serial)).toBeVisible();
  await expect(page.getByText(elsewhere.serial)).toHaveCount(0);

  consoleWatch.allowFailedRequest(`/api/tickets/${elsewhere.id}`, 404);
  await page.goto(`/tickets/${elsewhere.id}`);
  await expect(page.getByText("Ticket not found, or not at your units.")).toBeVisible();
});

test("S017: a back-dated ticket shows that time in the timeline", async ({ page }) => {
  const twoDaysAgo = istLocal(2 * 24 * 60);
  await asPerson(page, "operator", `/tickets/new?equipment=${seed.extruder.id}`);
  await page.getByRole("button", { name: /Early signs/ }).click();
  await page.getByLabel(/What is wrong\?/).fill("Raise test: back-dated");
  await page.getByLabel("When did it happen?").fill(twoDaysAgo);
  await saveButton(page).click();
  await page.getByRole("button", { name: "Done" }).click();
  await expect(timeline(page).last()).toContainText(shownTime(twoDaysAgo));
});

test("S028: admin raises a ticket 30 days back; the timeline shows that time and the hint says how far", async ({ page }) => {
  const thirtyDaysAgo = istLocal(30 * 24 * 60);
  await asPerson(page, "admin", `/tickets/new?equipment=${seed.extruder.id}`);
  await page.getByRole("button", { name: /Early signs/ }).click();
  await page.getByLabel(/What is wrong\?/).fill("S028 test: admin back-dated");
  await page.getByLabel("When did it happen?").fill(thirtyDaysAgo);
  await expect(page.getByText("That was 30 days ago")).toBeVisible();
  await saveButton(page).click();
  await page.getByRole("button", { name: "Done" }).click();
  await expect(timeline(page).last()).toContainText(shownTime(thirtyDaysAgo));
});

test("S018 A1: Already fixed with a start time; the fields fit and the ticket is back in service", { tag: "@device" }, async ({ page }) => {
  const base = thisMinute();
  const stopped = istLocal(60, base);
  const started = istLocal(40, base);
  const restored = istLocal(10, base);
  await asPerson(page, "technician", `/tickets/new?equipment=${seed.extruder.id}`);
  await page.getByRole("button", { name: /Stopped/ }).click();
  await page.getByLabel(/What is wrong\?/).fill("A1 test: belt off, refitted");
  await page.getByLabel("When did it happen?").fill(stopped);
  await page.getByText("Already fixed — back in service").click();
  await expect(saveButton(page)).toHaveText("Raise and mark back in service");

  // Who did the work: pre-filled with the technician's own person
  await expect(page.locator(".fw-semibold", { hasText: "Kannan (technician)" })).toBeVisible();
  await page.locator("form").getByRole("button", { name: "Change", exact: true }).click();
  await page.locator("#raise-restore-time").fill(restored);
  await page.getByLabel("Start date").fill(started.slice(0, 10));
  await page.locator("#raise-restore-started-time").fill(started.slice(11));
  await expectNoSidewaysScroll(page);
  await saveButton(page).scrollIntoViewIfNeeded();
  await expect(saveButton(page)).toBeInViewport();
  await saveButton(page).click();

  await expect(page.locator(".alert-success")).toContainText("and marked back in service");
  await page.getByRole("button", { name: "Done" }).click();
  await expect(stateBadge(page)).toHaveText("Back in service");
  await expect(timeline(page).filter({ hasText: "Back in service" })).toContainText("Kannan (technician)");
  await expect(timeValue(page, "Response")).toHaveText("20 min");
  await expect(timeValue(page, "Repair (hands on)")).toHaveText("30 min");
  await expect(timeValue(page, "Downtime")).toHaveText("50 min");
});

test("S018 A1: Already fixed without a start time shows response and repair as —", async ({ page }) => {
  await asPerson(page, "technician", `/tickets/new?equipment=${seed.extruder.id}`);
  await page.getByRole("button", { name: /Running, reduced/ }).click();
  await page.getByLabel(/What is wrong\?/).fill("A1 test: guard bolt tightened");
  await page.getByText("Already fixed — back in service").click();
  await expect(saveButton(page)).toHaveText("Raise and mark fixed");
  await saveButton(page).click();
  await page.getByRole("button", { name: "Done" }).click();
  await expect(stateBadge(page)).toHaveText("Back in service");
  await expect(timeValue(page, "Response")).toHaveText("—");
  await expect(timeValue(page, "Repair (hands on)")).toHaveText("—");
});

test("S017: IT admin gives a person with no login an Operator row; a supervisor names them on a ticket", async ({ page }, testInfo) => {
  const name = `Walk-in ${testInfo.project.name}`;
  await asPerson(page, "it_admin", "/masters");
  await page.getByRole("button", { name: "Team" }).click();
  await page.getByRole("button", { name: "Add person" }).click();
  await expectDialogFits(page);
  await page.getByLabel("Name").fill(name);
  await saveDialog(page, "Save");

  await page.getByRole("row", { name: new RegExp(name) }).getByTitle("Edit").click();
  await expectDialogFits(page);
  await page.getByLabel("Site to add").selectOption({ label: "SMTW — Main factory, Pavoorchatram" });
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await page.getByLabel("Role at SMTW").selectOption({ label: "Operator" });
  await page.getByLabel("All units").check();
  await saveDialog(page, "Save");
  await expect(page.getByRole("row", { name: new RegExp(name) })).toContainText("SMTW Operator");

  await asPerson(page, "supervisor", `/tickets/new?equipment=${seed.extruder.id}`);
  await page.getByRole("button", { name: /Early signs/ }).click();
  await page.getByLabel(/What is wrong\?/).fill("Raise test: reported by a walk-in");
  await page.getByLabel(/Found by/).selectOption({ label: `${name} (Operator)` });
  await saveButton(page).click();
  await page.getByRole("button", { name: "Done" }).click();
  await expect(page.locator("dt", { hasText: "Found by" }).locator("xpath=following-sibling::dd[1]")).toHaveText(name);
});
