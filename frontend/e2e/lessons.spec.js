// The one-point lesson screens (S077; the record and API are S075's) — in place of the step's manual checks.
// Each test makes its own machines (two of class HP in the operator's unit) and its lessons through the API
// (setup), then works them on the screens, so no seed machine gains a lesson and no other spec's page
// changes (BR1-10). Every dialog opened must fit (expectDialogFits).
//
// A lesson ticked "for every machine of the class" shows on every HP machine of the database, the other
// tests' machines included. So a test looks for its own lesson's row (unique title or serial), never counts
// rows or expects no card on an HP machine; the test of the empty card uses the seed extruder, a class with no lesson.
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, openDialog } from "./support/dialogs.js";
import { addActionByApi, raiseFixed, startImprovementByApi, TEST_PHOTO } from "./support/improvements.js";
import { addLessonPhotoByApi, lessonMachines, retireLessonByApi, writeLessonByApi } from "./support/lessons.js";
import { asPerson, seedIds } from "./support/people.js";
import { raiseByApi, saveDialog } from "./support/tickets.js";

/** The Lessons card's row for the lesson with `serial`. */
const lessonRow = (page, serial) => page.locator(`[data-testid="lessons-card"] [data-lesson="${serial}"]`);

/**
 * Open the machine's page as `key` and wait for the card's list to arrive, so a test that expects no
 * card (or no row) is not passing before the answer is in.
 */
async function openMachineAs(page, key, machine) {
  await asPerson(page, key);
  const answered = page.waitForResponse((r) => r.url().includes(`/api/procedures?equipment_id=${machine.id}`));
  await page.goto(`/equipment/${machine.id}`);
  await answered;
  await expect(page.getByRole("heading", { name: `${machine.code} — ${machine.name}` })).toBeVisible();
}

test("S077: an engineer adds a lesson with a photo on a machine; the card and the page show it", async ({ page }, testInfo) => {
  const { a } = await lessonMachines(testInfo, "add");
  await asPerson(page, "engineer", `/equipment/${a.id}`);
  await page.getByRole("button", { name: "Add lesson", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Title").fill("S077 add: keep the panel door shut");
  await dialog.getByLabel("Lesson text").fill("Dust stops the press.\nKeep the panel door shut.");
  await dialog.locator("input[type=file]").setInputFiles(TEST_PHOTO);
  await expect(dialog.locator('li[data-photo="test-photo.jpg"]')).toBeVisible();
  await saveDialog(page, "Save lesson");

  // The writer lands on the lesson page, as the operator will read it
  await expect(page).toHaveURL(/\/equipment\/lessons\/\d+$/);
  await expect(page.getByTestId("lesson-target")).toContainText(`${a.code} — ${a.name}`);
  await expect(page.getByText(/^OPL-\d+ · \d{2}-\d{2}-\d{4} · /)).toBeVisible();
  await expect(page.getByRole("heading", { name: "S077 add: keep the panel door shut" })).toBeVisible();
  const photo = page.locator('figure[data-photo="test-photo"] img');
  await expect(photo).toBeVisible();
  await expect.poll(() => photo.evaluate((img) => img.naturalWidth)).toBeGreaterThan(0);
  const body = page.getByTestId("lesson-body");
  await expect(body).toContainText("Dust stops the press.");
  await expect(body).toContainText("Keep the panel door shut.");
  expect(await body.evaluate((el) => el.innerText), "the line break is kept").toContain("Dust stops the press.\nKeep the panel door shut.");

  // Back on the machine: the card's row has the title and the thumbnail
  await page.getByTestId("lesson-target").getByRole("link").click();
  const row = page.locator('[data-testid="lessons-card"] [data-lesson]', { hasText: "S077 add: keep the panel door shut" });
  await expect(row).toHaveCount(1);
  await expect.poll(() => row.locator("img.cover").evaluate((img) => img.naturalWidth)).toBeGreaterThan(0);
});

test("S077: a lesson for the class shows on another machine of the class with its badge", async ({ page }, testInfo) => {
  const { a, b, className } = await lessonMachines(testInfo, "class");
  const lesson = await writeLessonByApi(a, { title: "S077 class: keep the panel door shut", forClass: true });
  // Retired in a finally, so even a failed run leaves no other spec's HP machine with a Lessons card (D8)
  try {
    await openMachineAs(page, "operator", b);
    const row = lessonRow(page, lesson.serial);
    await expect(row).toContainText("S077 class: keep the panel door shut");
    await expect(row).toContainText(`Every ${className}`);
  } finally {
    await retireLessonByApi(lesson);
  }
});

test("S077: an operator reads a lesson and sees no Add, Change or Edit photos", async ({ page }, testInfo) => {
  const { a } = await lessonMachines(testInfo, "operator");
  const lesson = await writeLessonByApi(a, { title: "S077 operator: read me", body: "S077 operator: the text to read." });
  await asPerson(page, "operator", `/equipment/lessons/${lesson.id}`);
  await expect(page.getByRole("heading", { name: "S077 operator: read me" })).toBeVisible();
  await expect(page.getByText("S077 operator: the text to read.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Print lesson", exact: true })).toBeVisible();
  for (const name of ["Add lesson", "Change lesson", "Edit photos", "Retire lesson"]) {
    await expect(page.getByRole("button", { name })).toHaveCount(0);
  }
});

test("S077: an operator sees no Lessons card on a machine with no lessons", async ({ page }) => {
  // The seed extruder: no spec writes a lesson on it or for its class (every HP machine may carry a class lesson)
  const { extruder } = await seedIds();
  await openMachineAs(page, "operator", extruder);
  await expect(page.getByTestId("lessons-card")).toHaveCount(0);
});

test("S077: an engineer changes the title and unticks the class; the other machine no longer lists it", async ({ page }, testInfo) => {
  const { a, b, className } = await lessonMachines(testInfo, "change");
  // Written from a Lesson countermeasure, so a PUT that sent action_id would be refused (BR2-03)
  const improvement = await startImprovementByApi(await raiseFixed(a.id, "S077 change: contactor chatters"));
  const { action } = await addActionByApi(improvement, { kind: "lesson", text: "S077 change: write the lesson" });
  const lesson = await writeLessonByApi(a, { title: "S077 change: first title", forClass: true, actionId: action.id });
  const tick = `Show on every machine of class ${className}`;

  await openMachineAs(page, "operator", b);
  await expect(lessonRow(page, lesson.serial)).toBeVisible();
  await asPerson(page, "engineer", `/equipment/lessons/${lesson.id}`);
  await expect(page.getByTestId("lesson-target")).toContainText(`for every ${className}`);
  await page.getByRole("button", { name: "Change lesson", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.getByLabel("Title")).toHaveValue("S077 change: first title");
  await expect(dialog.getByLabel(tick)).toBeChecked();
  await dialog.getByLabel("Title").fill("S077 change: second title");
  await dialog.getByLabel(tick).uncheck();
  await saveDialog(page, "Save lesson");

  await expect(page.getByRole("heading", { name: "S077 change: second title" })).toBeVisible();
  await expect(page.getByTestId("lesson-target")).not.toContainText("for every");
  await expect(page.getByText(/Last changed\s+\d{2}-\d{2}-\d{4} \d{2}:\d{2}\s+by/)).toBeVisible();
  // A machine lesson has no class in its detail: the dialog reads the machine for the name (BR2-02)
  await page.getByRole("button", { name: "Change lesson", exact: true }).click();
  await expectDialogFits(page);
  const again = await openDialog(page);
  await expect(again.getByLabel(tick)).not.toBeChecked();

  await openMachineAs(page, "operator", b);
  await expect(lessonRow(page, lesson.serial)).toHaveCount(0);
});

test("S077: retire asks first, the card leaves the lesson, Retired lessons brings it back", async ({ page }, testInfo) => {
  const { a } = await lessonMachines(testInfo, "retire");
  const lesson = await writeLessonByApi(a, { title: "S077 retire: the lesson" });
  await asPerson(page, "engineer", `/equipment/lessons/${lesson.id}`);
  await page.getByRole("button", { name: "Retire lesson", exact: true }).click();
  // The question replaces the buttons: one "Retire lesson" button on screen
  await expect(page.getByText(`Retire ${lesson.serial}? It leaves the machine's page. You can bring it back.`)).toBeVisible();
  await expect(page.getByRole("button", { name: "Retire lesson", exact: true })).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Change lesson" })).toHaveCount(0);
  await page.getByRole("button", { name: "Retire lesson", exact: true }).click();
  await expect(page.getByTestId("retired-banner")).toContainText("Retired — this lesson is no longer shown on the machine's page.");

  // An operator no longer finds it on the machine
  await openMachineAs(page, "operator", a);
  await expect(lessonRow(page, lesson.serial)).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Retired lessons/ })).toHaveCount(0);

  // The writer finds it under Retired lessons (the count may include a retired class lesson of another test) and brings it back
  await openMachineAs(page, "engineer", a);
  await expect(lessonRow(page, lesson.serial)).toHaveCount(0);
  await page.getByRole("button", { name: /^Retired lessons \(\d+\)$/ }).click();
  const row = lessonRow(page, lesson.serial);
  await expect(row).toContainText("Retired");
  await row.click();
  await page.getByRole("button", { name: "Bring back lesson", exact: true }).click();
  await expect(page.getByTestId("retired-banner")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Retire lesson", exact: true })).toBeVisible();
});

test("S077: the server's refusal of an empty lesson text shows beside the field", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/api/procedures", 400);
  const { a } = await lessonMachines(testInfo, "refuse");
  await asPerson(page, "engineer", `/equipment/${a.id}`);
  await page.getByRole("button", { name: "Add lesson", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Title").fill("S077 refuse: a lesson with no text");
  await dialog.getByLabel("Lesson text").fill("   ");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Enter the lesson text");
  await expect(dialog.locator(".invalid-feedback.d-block")).toHaveCount(1);
});

test("S077: a photo the server refuses leaves the lesson saved; Close opens the lesson", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/api/procedures/", 400);
  const { a } = await lessonMachines(testInfo, "badphoto");
  await asPerson(page, "engineer", `/equipment/${a.id}`);
  await page.getByRole("button", { name: "Add lesson", exact: true }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await dialog.getByLabel("Title").fill("S077 badphoto: lesson with a bad photo");
  await dialog.getByLabel("Lesson text").fill("S077 badphoto: the text.");
  await dialog.locator("input[type=file]").setInputFiles({ name: "bad.jpg", mimeType: "image/jpeg", buffer: Buffer.from("not an image") });
  await dialog.locator(".modal-footer button[type=submit]").click();

  await expect(dialog.getByText("Lesson saved. A photo was not saved. Add it again, or close.")).toBeVisible();
  await expect(dialog.locator(".modal-footer button[type=submit]")).toHaveCount(0);
  await dialog.locator(".modal-footer").getByRole("button", { name: "Close", exact: true }).click();
  // The saved lesson reaches the page through the dialog's closed event
  await expect(page).toHaveURL(/\/equipment\/lessons\/\d+$/);
  await expect(page.getByRole("heading", { name: "S077 badphoto: lesson with a bad photo" })).toBeVisible();
});

test("S077: a lesson photo that cannot be loaded shows a short line to reload", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/api/procedures/", 503);
  const { a } = await lessonMachines(testInfo, "photofail");
  const lesson = await writeLessonByApi(a, { title: "S077 photofail: the lesson" });
  await addLessonPhotoByApi(lesson, "S077 photofail photo");
  await page.route(/\/api\/procedures\/\d+\/documents\/\d+\/file$/, (route) => route.fulfill({ status: 503, json: { error: "Service unavailable" } }));
  await asPerson(page, "operator", `/equipment/lessons/${lesson.id}`);
  const figure = page.locator('figure[data-photo="S077 photofail photo"]');
  await expect(figure.getByText("The photo could not be loaded. Reload the page.")).toBeVisible();
  await expect(figure.locator(".fa-spinner")).toHaveCount(0);
});

test("S077: a removed lesson photo is listed in Settings and restored", async ({ page }, testInfo) => {
  const { a } = await lessonMachines(testInfo, "removed");
  const lesson = await writeLessonByApi(a, { title: "S077 removed: the lesson" });
  await addLessonPhotoByApi(lesson, "S077 removed photo");
  await asPerson(page, "engineer", `/equipment/lessons/${lesson.id}`);
  await expect(page.locator('figure[data-photo="S077 removed photo"] img')).toBeVisible();
  await page.getByRole("button", { name: "Edit photos", exact: true }).click();
  await page.getByRole("button", { name: "S077 removed photo" }).click();
  const viewer = page.locator(".modal.show");
  await viewer.getByRole("button", { name: "Remove", exact: true }).click();
  await viewer.getByRole("button", { name: "Yes", exact: true }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(page.locator('figure[data-photo="S077 removed photo"]')).toHaveCount(0);

  await asPerson(page, "manager", "/settings");
  await page.getByRole("searchbox", { name: "Search removed documents" }).fill(lesson.serial);
  const removed = page.locator("tr", { hasText: "S077 removed photo" });
  await expect(removed).toContainText(`Lesson ${lesson.serial}`);
  await expect(removed).toContainText(`${a.code} · SMTW.MCC2`);
  await removed.getByRole("button", { name: "Restore" }).click();
  await expect(page.getByText("Restored 'S077 removed photo'.")).toBeVisible();
  await expect(removed).toHaveCount(0);

  await page.goto(`/equipment/lessons/${lesson.id}`);
  await expect(page.locator('figure[data-photo="S077 removed photo"] img')).toBeVisible();
});

test("S077: a Tamil title and text are shown as typed", async ({ page }, testInfo) => {
  const { a } = await lessonMachines(testInfo, "tamil");
  const title = "பேனல் கதவை மூடி வைக்கவும்";
  const lesson = await writeLessonByApi(a, { title, body: "பேனல் கதவை எப்போதும் மூடி வைக்கவும்.\nKeep the panel door shut." });
  await asPerson(page, "operator", `/equipment/lessons/${lesson.id}`);
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  await expect(page.getByTestId("lesson-body")).toContainText("பேனல் கதவை எப்போதும் மூடி வைக்கவும்.");
  await expect(page.getByTestId("lesson-body")).toContainText("Keep the panel door shut.");
  await page.getByTestId("lesson-target").getByRole("link").click();
  await expect(lessonRow(page, lesson.serial)).toContainText(title);
});

test(
  "S077: on a phone the Lessons card is in view after opening the machine by its QR link, with open tickets on it",
  { tag: "@device" },
  async ({ page }, testInfo) => {
    const { a } = await lessonMachines(testInfo, "qr");
    const lesson = await writeLessonByApi(a, { title: "S077 qr: keep the panel door shut" });
    for (const n of [1, 2, 3]) {
      await raiseByApi("operator", { equipment_id: a.id, intensity: "degraded", description: `S077 qr: open ticket ${n}` });
    }
    await asPerson(page, "operator", `/e/${a.code}`);
    await expect(page).toHaveURL(new RegExp(`/equipment/${a.id}$`));
    await expect(lessonRow(page, lesson.serial)).toBeInViewport();
    // The card comes before the open tickets
    const card = await page.getByTestId("lessons-card").boundingBox();
    const tickets = await page.locator(".card-header", { hasText: /^\s*Open tickets/ }).boundingBox();
    expect(card.y, "the Lessons card is below Open tickets").toBeLessThan(tickets.y);
  },
);

test("S077: the lesson page's title and first photo are on screen without scrolling", { tag: "@device" }, async ({ page }, testInfo) => {
  const { a } = await lessonMachines(testInfo, "fold");
  const lesson = await writeLessonByApi(a, { title: "S077 fold: keep the panel door shut" });
  await addLessonPhotoByApi(lesson, "S077 fold photo");
  await asPerson(page, "operator", `/equipment/lessons/${lesson.id}`);
  await expect(page.getByRole("heading", { name: "S077 fold: keep the panel door shut" })).toBeInViewport({ ratio: 1 });
  const photo = page.locator('figure[data-photo="S077 fold photo"] img');
  await expect(photo).toBeVisible();
  await expect(photo).toBeInViewport({ ratio: 0.5 });
});
