// Work notes on a ticket (S027 § 8 Automated) — in place of its manual checks.  Each test raises its
// own ticket on the seed's extruder through the API (setup), then works the notes on the screens;
// every dialog opened must fit (openAction, or expectDialogFits).  The tickets are closed after
// each test, so they do not pile up on the extruder (S017's raise screen lists at most 50).
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, openDialog } from "./support/dialogs.js";
import { apiAs, asPerson, seedIds } from "./support/people.js";
import { card, causeId, moveByApi, openAction, raiseByApi, saveDialog, timeline } from "./support/tickets.js";

let seed;
let raised = []; // this test's tickets, closed after it

test.beforeAll(async () => {
  seed = await seedIds();
});

// Not a fault, as IT admin through the API, for what the test left open
test.afterEach(async () => {
  const api = await apiAs("admin");
  try {
    for (const id of raised) {
      const ticket = await (await api.get(`/api/tickets/${id}`)).json();
      if (ticket.state === "closed") continue;
      const res = await api.post(`/api/tickets/${id}/moves/not-a-fault`, {
        data: { cause_id: await causeId("5.1"), remark: "S027 test: tidy-up" },
      });
      expect(res.status(), await res.text()).toBe(200);
    }
  } finally {
    raised = [];
    await api.dispose();
  }
});

/** A defect on the extruder, raised by the operator with `description` (setup) -> the ticket. */
async function raiseDefect(description) {
  const ticket = await raiseByApi("operator", { equipment_id: seed.extruder.id, intensity: "degraded", description });
  raised.push(ticket.id);
  return ticket;
}

/** A note by a seed person through the API (setup), expecting 201. */
async function noteByApi(key, ticketId, remark) {
  const api = await apiAs(key);
  try {
    const res = await api.post(`/api/tickets/${ticketId}/notes`, { data: { remark } });
    expect(res.status(), await res.text()).toBe(201);
  } finally {
    await api.dispose();
  }
}

/** The text of a timeline entry's note as shown, line breaks included (pre-wrap). */
function shownText(locator) {
  return locator.evaluate((el) => el.innerText);
}

test("S027: technician adds a two-line note from the action bar; the cursor starts in the field; the timeline shows it", async ({ page }) => {
  const ticket = await raiseDefect("Notes test: pilot line pressure low");
  await asPerson(page, "technician", `/tickets/${ticket.id}`);

  const dialog = await openAction(page, "Add note");
  const field = dialog.getByLabel("Note");
  await expect(field).toBeFocused();
  await field.fill("Pressure not reached in Pilot line.\nReason not known yet");
  await saveDialog(page, "Save note");

  const entry = timeline(page).first();
  await expect(entry.locator(".fw-semibold")).toHaveText("Note by e2e_technician");
  expect(await shownText(entry.locator(".note-text"))).toBe("Pressure not reached in Pilot line.\nReason not known yet");
  await expect(timeline(page)).toHaveCount(2);
});

test("S027: engineer corrects a note: the hint shows; then Edited by, and Show earlier text gives the old text", async ({ page }) => {
  const ticket = await raiseDefect("Notes test: borewell pump");
  await noteByApi("technician", ticket.id, "No amps, no movment");
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);

  const entry = timeline(page).first();
  await entry.getByRole("button", { name: "Edit note" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog).toContainText("Fix a typo or wrong information here. To record new findings, add a note.");
  const field = dialog.getByLabel("Note");
  await expect(field).toHaveValue("No amps, no movment");
  await field.fill("No amps, no movement");
  await saveDialog(page, "Save changes");

  await expect(entry.locator(".note-text").first()).toHaveText("No amps, no movement");
  await expect(entry).toContainText("Edited by e2e_engineer");
  // The note keeps its author
  await expect(entry).toContainText("e2e_technician");
  await entry.getByRole("button", { name: "Show earlier text" }).click();
  await expect(entry.locator(".earlier")).toContainText("No amps, no movment");
  await expect(entry.locator(".earlier")).toContainText("Replaced by e2e_engineer");
});

test("S027: the Raised line shows the raise's What is wrong? text, and the page has no Description card", async ({ page }) => {
  const ticket = await raiseDefect("Notes test: fan belt squeals at start");
  await asPerson(page, "technician", `/tickets/${ticket.id}`);

  const raisedLine = timeline(page).last();
  await expect(raisedLine.locator(".fw-semibold").first()).toHaveText("Raised");
  await expect(raisedLine.locator(".note-text")).toHaveText("Notes test: fan belt squeals at start");
  await expect(card(page, "Description")).toHaveCount(0);
});

test("S027: Save note with an empty field shows Enter a note under the field, in view; nothing is added", { tag: "@device" }, async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/notes", 400);
  const ticket = await raiseDefect("Notes test: empty note");
  await asPerson(page, "technician", `/tickets/${ticket.id}`);

  const dialog = await openAction(page, "Add note");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Enter a note");
  await expect(dialog.getByLabel("Note")).toBeFocused();
  await dialog.locator(".modal-footer").getByRole("button", { name: "Cancel" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
  await expect(timeline(page)).toHaveCount(1);
});

test("S027: an operator adds a note and sees no pencil; a technician sees none either; on a closed ticket nobody adds or edits", async ({ page }) => {
  const ticket = await raiseDefect("Notes test: noise is back");
  await asPerson(page, "operator", `/tickets/${ticket.id}`);
  const dialog = await openAction(page, "Add note");
  await dialog.getByLabel("Note").fill("The noise is back at 3 pm");
  await saveDialog(page, "Save note");
  const entry = timeline(page).first();
  await expect(entry.locator(".note-text")).toHaveText("The noise is back at 3 pm");
  await expect(entry).toContainText("e2e_operator");
  await expect(page.getByRole("button", { name: "Edit note" })).toHaveCount(0);

  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  await expect(timeline(page).first()).toContainText("The noise is back at 3 pm");
  await expect(page.getByRole("button", { name: "Add note", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Edit note" })).toHaveCount(0);

  await moveByApi("engineer", ticket.id, "not-a-fault", { cause_id: await causeId("5.1"), remark: "Notes test: closed" });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  // Newest first: the Not a fault line, then the note
  await expect(timeline(page).nth(1)).toContainText("The noise is back at 3 pm");
  await expect(page.getByRole("button", { name: "Add note", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Edit note" })).toHaveCount(0);
});
