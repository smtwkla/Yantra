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

/** A move or re-grade through the API as a seed person (setup only; the flows use the screens). */
export async function moveByApi(key, ticketId, move, body = {}) {
  const api = await apiAs(key);
  try {
    const res = await api.post(`/api/tickets/${ticketId}/moves/${move}`, { data: body });
    expect(res.status(), await res.text()).toBe(200);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/** The ticket page's action bar button `name` (exact), clicked; the dialog opens and must fit. */
export async function openAction(page, name) {
  await page.getByRole("button", { name, exact: true }).first().click();
  await expectDialogFits(page);
  return openDialog(page);
}

/** "Now · Change" in a dialog: change the time to `value` ("YYYY-MM-DDTHH:MM"). */
export async function setEventTime(dialog, value) {
  await dialog.getByRole("button", { name: "Change", exact: true }).click();
  await dialog.locator("input[type=datetime-local]").fill(value);
}

/** Save the open dialog with its submit button, named `label`, and wait for it to close. */
export async function saveDialog(page, label) {
  const dialog = openDialog(page);
  const save = dialog.locator(".modal-footer button[type=submit]");
  await expect(save).toHaveText(label);
  await save.click();
  await expect(page.locator(".modal.show")).toHaveCount(0);
}

/** The ticket page's state badge (beside the serial). */
export function stateBadge(page) {
  return page.locator(".badge.text-bg-light");
}

/** The ticket page's card whose header starts with `title` ("Times", "Assigned", "Labour", "Timeline"). */
export function card(page, title) {
  return page.locator(".card").filter({ has: page.locator(".card-header", { hasText: new RegExp(`^\\s*${title}`) }) });
}

/** The Times card's value for `label` ("Response", "Repair (hands on)", "Downtime"). */
export function timeValue(page, label) {
  return card(page, "Times").locator("dt", { hasText: label }).locator("xpath=following-sibling::dd[1]");
}

/** The timeline's entries (one per event), in order. */
export function timeline(page) {
  return card(page, "Timeline").locator("li");
}

/** "21-10-2026 14:05"-style text of an IST "YYYY-MM-DDTHH:MM" value, as formatDateTime shows it. */
export function shownTime(value) {
  const [date, time] = value.split("T");
  const [y, m, d] = date.split("-");
  return `${d}-${m}-${y} ${time}`;
}
