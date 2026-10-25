// Ticket helpers shared by the ticket flow tests (S017, S018).
import { expect } from "@playwright/test";
import { apiAs } from "./people.js";
import { expectDialogFits, openDialog } from "./dialogs.js";

/**
 * A time `minutesAgo` minutes before `base` (default now) as the screens and the API take it,
 * "YYYY-MM-DDTHH:MM" in IST (Asia/Kolkata), whatever the test machine's own time zone.
 */
export function istLocal(minutesAgo, base = new Date()) {
  const at = new Date(base.getTime() - minutesAgo * 60_000);
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(at).map((p) => [p.type, p.value]));
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

/** The start of the current minute: typed times are whole minutes, so differences are exact. */
export function thisMinute() {
  const now = new Date();
  now.setSeconds(0, 0);
  return now;
}

/** Raise a ticket through the API as a seed person (a test's own setup) -> the ticket. */
export async function raiseByApi(key, body) {
  const api = await apiAs(key);
  try {
    const res = await api.post("/api/tickets", { data: body });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/** POST `path` with `body` as a seed person, expecting 200 -> the ticket. */
async function postAs(key, path, body) {
  const api = await apiAs(key);
  try {
    const res = await api.post(path, { data: body });
    expect(res.status(), await res.text()).toBe(200);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/** A move through the API as a seed person (setup only; the flows use the screens). */
export function moveByApi(key, ticketId, move, body = {}) {
  return postAs(key, `/api/tickets/${ticketId}/moves/${move}`, body);
}

/** A re-grade through the API as a seed person (setup, or someone else acting meanwhile, S025). */
export function regradeByApi(key, ticketId, body) {
  return postAs(key, `/api/tickets/${ticketId}/regrade`, body);
}

/** The id of the row `code` in the failure-code list `list` ("failure-causes"), read as admin. */
async function codeId(list, code) {
  const api = await apiAs("admin");
  try {
    const res = await api.get(`/api/masters/${list}`);
    expect(res.ok(), `${list} look-up failed: ${res.status()}`).toBe(true);
    const body = await res.json();
    const row = body.items.find((c) => c.code === code);
    if (!row) throw new Error(`${list} ${code} not found`);
    return row.id;
  } finally {
    await api.dispose();
  }
}

/** The id of the failure cause `code` ("5.1"), read through the API as admin. */
export function causeId(code) {
  return codeId("failure-causes", code);
}

/** The id of the maintenance action `code` ("1" Replace), read through the API as admin (S020). */
export function actionId(code) {
  return codeId("maintenance-actions", code);
}

/** The ticket page's action bar button `name` (exact), clicked; the dialog opens and must fit. */
export async function openAction(page, name) {
  await page.getByRole("button", { name, exact: true }).first().click();
  await expectDialogFits(page);
  return openDialog(page);
}

/** The time field with a Now tick (S051) in `dialog`: untick Now, then set the time to `value` ("YYYY-MM-DDTHH:MM"). */
export async function setEventTime(dialog, value) {
  await dialog.getByRole("checkbox", { name: "Now", exact: true }).uncheck();
  await dialog.locator("input[type=datetime-local]").fill(value);
}

/** Save the open dialog with its submit button, named `label`, and wait for it to close. */
export async function saveDialog(page, label) {
  // not openDialog(): the dialog is open already, and the focus may be on <body> (a clicked button was removed)
  const dialog = page.locator(".modal.show .modal-dialog");
  const save = dialog.locator(".modal-footer button[type=submit]");
  await expect(save).toHaveText(label);
  await save.click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
}

/** The ticket page's state badge (beside the serial; red when overdue, S019). */
export function stateBadge(page) {
  return page.locator(".badge.state-badge");
}

/** The ticket page's card whose header starts with `title` ("Times", "Assigned", "Labour", "Timeline"). */
export function card(page, title) {
  return page.locator(".card").filter({ has: page.locator(".card-header", { hasText: new RegExp(`^\\s*${title}`) }) });
}

/** The Times card's value for `label` ("Response", "Repair (hands on)", "Downtime"). */
export function timeValue(page, label) {
  return card(page, "Times").locator("dt", { hasText: label }).locator("xpath=following-sibling::dd[1]");
}

/** The timeline's entries (one per event), newest first: the Raised line is the last. */
export function timeline(page) {
  return card(page, "Timeline").locator("li");
}

/** "21-10-2026 14:05"-style text of an IST "YYYY-MM-DDTHH:MM" value, as formatDateTime shows it. */
export function shownTime(value) {
  const [date, time] = value.split("T");
  return `${shownDay(date)} ${time}`;
}

/** The IST date `daysAhead` days from today, "YYYY-MM-DD" (a planned date, S019; negative is past). */
export function istDay(daysAhead) {
  return istLocal(-daysAhead * 24 * 60).slice(0, 10);
}

/** "25-10-2026" for "2026-10-25", as formatDateTime shows a date. */
export function shownDay(isoDate) {
  const [y, m, d] = isoDate.split("-");
  return `${d}-${m}-${y}`;
}
