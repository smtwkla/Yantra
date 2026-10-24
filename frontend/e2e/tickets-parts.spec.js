// Parts used on a ticket (S020 § 8) — in place of its manual checks.  Each test raises its own
// ticket on the seed's extruder through the API (setup), then works the parts on the screens;
// every dialog opened must fit (expectDialogFits, or openAction).  The three projects share one
// database, so earlier lines stay on the extruder: a line is found by a description unique to
// the run, and no test asserts the length of a list or that a list is empty.
import { test, expect } from "./support/test.js";
import { expectDialogFits, expectFieldMessage, openDialog } from "./support/dialogs.js";
import { apiAs, asPerson, personId, seedIds } from "./support/people.js";
import {
  actionId, card, causeId, istDay, moveByApi, openAction, raiseByApi, saveDialog, stateBadge,
} from "./support/tickets.js";

let seed;
let kannan; // the technician's Team record
let raised = []; // this test's tickets, closed after it

test.beforeAll(async () => {
  seed = await seedIds();
  kannan = await personId("technician");
});

/**
 * Close what the test left open, as IT admin through the API: its parts removed, then not a
 * fault (or a plain close from back in service).  The three projects share one database, and
 * the raise screen lists at most 50 open tickets of a machine (S017's test reads that list),
 * so these tickets must not pile up on the extruder.
 */
test.afterEach(async () => {
  const api = await apiAs("admin");
  try {
    for (const id of raised) {
      const ticket = await (await api.get(`/api/tickets/${id}`)).json();
      if (ticket.state === "closed") continue;
      let body = { cause_id: await causeId("5.1"), remark: "S020 test: tidy-up" };
      let move = "not-a-fault";
      if (ticket.state === "back_in_service") {
        const modes = (await (await api.get(`/api/tickets/modes?ticket_id=${id}`)).json()).items;
        body = { cause_id: await causeId("3.4"), action_id: await actionId("1"), failure_mode_id: modes[0].id };
        move = "close";
      } else {
        for (const part of ticket.parts) await api.delete(`/api/tickets/${id}/parts/${part.id}`);
      }
      const res = await api.post(`/api/tickets/${id}/moves/${move}`, { data: body });
      expect(res.status(), await res.text()).toBe(200);
    }
  } finally {
    raised = [];
    await api.dispose();
  }
});

/** POST `path` with `body` as a seed person, expecting 201 (setup) -> the ticket. */
async function createdAs(key, path, body) {
  const api = await apiAs(key);
  try {
    const res = await api.post(path, { data: body });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/** A labour row of 30 minutes by the technician, with his trade (setup: Close needs labour). */
async function labourByApi(ticketId) {
  const api = await apiAs("technician");
  let trade;
  try {
    const people = (await (await api.get(`/api/tickets/people?ticket_id=${ticketId}`)).json()).items;
    trade = people.find((p) => p.id === kannan).trades[0]?.id ?? null;
  } finally {
    await api.dispose();
  }
  return createdAs("technician", `/api/tickets/${ticketId}/labour`, {
    person_id: kannan, trade_id: trade, work_date: istDay(0), minutes: 30,
  });
}

/**
 * Type the description, then wait until "Fitted here before" has narrowed to the lines that
 * match it: the list collapsing moves the fields below it (a run-unique text matches nothing).
 */
async function typeDescription(dialog, text, { matches = false } = {}) {
  await dialog.getByLabel("Description").fill(text);
  if (!matches) await expect(dialog.locator(".fitted-before")).toHaveCount(0);
}

/** Fill a field and check it took the value. */
async function fillIn(field, value) {
  await field.fill(value);
  await expect(field).toHaveValue(value);
}

/** A parts line through the API as the technician (setup). */
function partByApi(ticketId, body) {
  return createdAs("technician", `/api/tickets/${ticketId}/parts`, {
    quantity: "1", node_id: seed.extruder.id, ...body,
  });
}

/** A defect on the extruder, raised by the operator; closed after the test. */
async function raiseDefect(description) {
  const ticket = await raiseByApi("operator", { equipment_id: seed.extruder.id, intensity: "degraded", description });
  raised.push(ticket.id);
  return ticket;
}

function partsCard(page) {
  return card(page, "Parts used");
}

/** The Parts used card's Add part, clicked; the dialog must fit -> the dialog. */
async function openAddPart(page) {
  await partsCard(page).getByRole("button", { name: "Add part" }).click();
  await expectDialogFits(page);
  const dialog = await openDialog(page);
  await expect(dialog.locator(".modal-title")).toHaveText("Add part");
  return dialog;
}

/** Cancel a dialog with typed input: Cancel, then Discard. */
async function discardDialog(page) {
  const dialog = await openDialog(page);
  await dialog.locator(".modal-footer").getByRole("button", { name: "Cancel" }).click();
  await dialog.getByRole("button", { name: "Discard" }).click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
}

test("S020: technician adds a part line the short way, fitted to a component; changes the quantity; removes it", async ({ page }) => {
  const ticket = await raiseDefect("S020 test: gearbox noise");
  await moveByApi("technician", ticket.id, "start");
  const description = `Ball bearing ${ticket.serial}`;
  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  await expect(stateBadge(page)).toHaveText("In progress");
  await expect(partsCard(page)).toContainText("No parts recorded");

  const dialog = await openAddPart(page);
  await typeDescription(dialog, description);
  await fillIn(dialog.getByLabel(/Part number/), "6205-2RS");
  // The kind shows once there is a number; the standard number is the default
  await expect(dialog.getByRole("button", { name: /A standard number/ })).toHaveAttribute("aria-pressed", "true");
  await expect(dialog.getByLabel("Quantity")).toHaveValue("1");
  await expect(dialog.getByLabel("Unit")).toHaveValue("nos");
  // Fitted to: the machine first and chosen (the ticket has no component); pick the gearbox
  await expect(dialog.getByLabel("Fitted to").locator("option:checked")).toHaveText(
    `${seed.extruder.code} ${seed.extruder.name}`);
  await dialog.getByLabel("Fitted to").selectOption({ label: `${seed.gearbox.code} ${seed.gearbox.name}` });
  await saveDialog(page, "Save");

  const line = partsCard(page).locator("li", { hasText: description });
  await expect(line).toContainText(`1 nos · ${description}`);
  await expect(line).toContainText("6205-2RS (standard number)");
  await expect(line).toContainText(`Fitted to ${seed.gearbox.code}`);

  await line.getByTitle("Change").click();
  await expectDialogFits(page);
  const change = await openDialog(page);
  await expect(change.locator(".modal-title")).toHaveText("Change part");
  await expect(change.getByText("Fitted here before")).toHaveCount(0);
  await change.getByLabel("Quantity").fill("2");
  await saveDialog(page, "Save");
  await expect(line).toContainText(`2 nos · ${description}`);

  // Remove asks first
  await line.getByTitle("Remove").click();
  await expect(line.getByText("Remove?")).toBeVisible();
  // Locate Yes afresh once the confirm shows (the line re-renders), then click (S045)
  const yes = partsCard(page).locator("li", { hasText: description }).getByRole("button", { name: "Yes", exact: true });
  await expect(yes).toBeVisible();
  await yes.click();
  await expect(partsCard(page)).toContainText("No parts recorded");
});

test("S020: a maker's part number without a maker, and a quantity of 0, are refused beside their fields", async ({ page, consoleWatch }) => {
  // The API decides both (§ 5.1): the browser logs the two 400s
  consoleWatch.allowFailedRequest("/parts", 400);
  const ticket = await raiseDefect("S020 test: cylinder leak");
  await asPerson(page, "technician", `/tickets/${ticket.id}`);

  const dialog = await openAddPart(page);
  await typeDescription(dialog, `Seal kit ${ticket.serial}`);
  await fillIn(dialog.getByLabel(/Part number/), "R900-123");
  await dialog.getByRole("button", { name: "From the maker's drawing or quote" }).click();
  // Maker is required now: its label drops "(optional)"
  await expect(dialog.locator("label[for=part-maker]")).not.toContainText("optional");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Name the maker of this part number");
  await expect(dialog.locator("#part-maker")).toHaveClass(/is-invalid/);

  await dialog.locator("#part-maker").fill("Rexroth");
  await dialog.getByLabel("Quantity").fill("0");
  await dialog.locator(".modal-footer button[type=submit]").click();
  await expectFieldMessage(dialog, "Enter a quantity, e.g. 2 or 1.5");
  await expect(dialog.getByLabel("Quantity")).toHaveClass(/is-invalid/);
  await discardDialog(page);
  await expect(partsCard(page)).toContainText("No parts recorded");
});

test("S020: a second ticket on the same machine offers the first one's line under Fitted here before; a tap fills it", async ({ page }) => {
  const first = await raiseDefect("S020 test: seal kit changed");
  const description = `Seal kit, main cylinder ${first.serial}`;
  await partByApi(first.id, {
    description, part_number: `SK-${first.serial}`, number_kind: "maker", maker: "Rexroth", node_id: seed.gearbox.id,
  });
  const second = await raiseDefect("S020 test: seal kit again");
  await asPerson(page, "technician", `/tickets/${second.id}`);

  const dialog = await openAddPart(page);
  // Typing in Description narrows the list to the line of this run
  await typeDescription(dialog, first.serial, { matches: true });
  const suggestion = dialog.locator(".fitted-before").getByRole("button", { name: description });
  await expect(suggestion).toHaveText(`${description} · SK-${first.serial} · Rexroth`);
  // The dialog still fits with the list showing
  await expectDialogFits(page);
  await suggestion.click();
  await expect(dialog.getByLabel("Description")).toHaveValue(description);
  await expect(dialog.getByLabel(/Part number/)).toHaveValue(`SK-${first.serial}`);
  await expect(dialog.getByRole("button", { name: "From the maker's drawing or quote" })).toHaveAttribute(
    "aria-pressed", "true");
  await expect(dialog.locator("#part-maker")).toHaveValue("Rexroth");
  await saveDialog(page, "Save");
  await expect(partsCard(page).locator("li", { hasText: description })).toContainText(
    `Fitted to ${seed.extruder.code} ${seed.extruder.name}`);
});

test("S020: Not a fault waits while parts are recorded; after removing them it is offered and succeeds", async ({ page }) => {
  const ticket = await raiseDefect("S020 test: looked, part fitted anyway");
  await partByApi(ticket.id, { description: `Fuse ${ticket.serial}` });
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);

  const waiting = page.locator(".action-bar").getByRole("button", { name: "Not a fault", exact: true });
  await expect(waiting).toBeDisabled();
  await expect(page.getByText("Remove the parts first")).toBeVisible();

  const line = partsCard(page).locator("li", { hasText: `Fuse ${ticket.serial}` });
  await line.getByTitle("Remove").click();
  await line.getByRole("button", { name: "Yes", exact: true }).click();
  await expect(page.getByText("Remove the parts first")).toHaveCount(0);

  const dialog = await openAction(page, "Not a fault");
  await dialog.locator("#move-not-a-fault-remark").fill("Ran fine; the fuse was a spare test");
  await saveDialog(page, "Close as not a fault");
  await expect(stateBadge(page)).toHaveText("Closed");
});

test("S020: the close dialog hints at parts for Replace or Overhaul with none recorded, and not once one is", async ({ page }) => {
  const ticket = await raiseDefect("S020 test: worn coupling");
  await moveByApi("technician", ticket.id, "restore", { person_id: kannan });
  await labourByApi(ticket.id);
  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  const HINT = "No parts recorded. If any were fitted, cancel and add them on the ticket first.";

  let dialog = await openAction(page, "Close");
  const action = dialog.locator("#move-action");
  await action.selectOption({ label: "1 Replace" });
  await expect(dialog.getByText(HINT)).toBeVisible();
  await action.selectOption({ label: "2 Repair" });
  await expect(dialog.getByText(HINT)).toHaveCount(0);
  await action.selectOption({ label: "10 Overhaul" });
  await expect(dialog.getByText(HINT)).toBeVisible();
  await discardDialog(page);

  await partByApi(ticket.id, { description: `Coupling insert ${ticket.serial}` });
  await page.reload();
  await expect(partsCard(page)).toContainText(`Coupling insert ${ticket.serial}`);
  dialog = await openAction(page, "Close");
  await dialog.locator("#move-action").selectOption({ label: "1 Replace" });
  await expect(dialog.getByText(HINT)).toHaveCount(0);
});

test("S020: a closed ticket's parts are read-only; an operator sees the lines but no Add, and no panel when there are none", async ({ page }) => {
  const ticket = await raiseDefect("S020 test: closed with a part");
  const description = `V-belt ${ticket.serial}`;
  await moveByApi("technician", ticket.id, "restore", { person_id: kannan });
  await labourByApi(ticket.id);
  await partByApi(ticket.id, { description, part_number: "B-42", number_kind: "generic", quantity: "2", qty_unit: "set" });
  const api = await apiAs("engineer");
  let modeId;
  try {
    modeId = (await (await api.get(`/api/tickets/modes?ticket_id=${ticket.id}`)).json()).items[0].id;
  } finally {
    await api.dispose();
  }
  await moveByApi("engineer", ticket.id, "close", {
    cause_id: await causeId("3.4"), action_id: await actionId("1"), failure_mode_id: modeId,
  });

  await asPerson(page, "engineer", `/tickets/${ticket.id}`);
  await expect(stateBadge(page)).toHaveText("Closed");
  const line = partsCard(page).locator("li", { hasText: description });
  await expect(line).toContainText(`2 set · ${description}`);
  await expect(partsCard(page).getByRole("button", { name: "Add part" })).toHaveCount(0);
  await expect(line.getByTitle("Change")).toHaveCount(0);
  await expect(line.getByTitle("Remove")).toHaveCount(0);

  const withLine = await raiseDefect("S020 test: open with a part");
  // An operator on an OPEN ticket with a line: reads it, with no Add part, Change or Remove (S020 CR1-01)
  const openDescription = `Gasket ${withLine.serial}`;
  await partByApi(withLine.id, { description: openDescription });
  await asPerson(page, "operator", `/tickets/${withLine.id}`);
  const openLine = partsCard(page).locator("li", { hasText: openDescription });
  await expect(openLine).toBeVisible();
  await expect(partsCard(page).getByRole("button", { name: "Add part" })).toHaveCount(0);
  await expect(openLine.getByTitle("Change")).toHaveCount(0);
  await expect(openLine.getByTitle("Remove")).toHaveCount(0);

  const bare = await raiseDefect("S020 test: no parts here");
  await asPerson(page, "operator", `/tickets/${bare.id}`);
  await expect(page.getByRole("heading", { name: bare.serial })).toBeVisible();
  await expect(partsCard(page)).toHaveCount(0);
});
