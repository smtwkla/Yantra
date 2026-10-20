/**
 * Ticket labels — pure display helpers for the ticket screens (S017). The backend's
 * tickets_core holds the rules; these only name the values.
 *
 * Intensity is ISO 14224's failure impact: critical (stopped: a breakdown), degraded
 * (running, reduced: a defect) or initial (early signs: a defect).
 */

export const BREAKDOWN_INTENSITY = "critical";

export const INTENSITY_LABELS = {
  critical: "Breakdown",
  degraded: "Defect",
  initial: "Defect · initial",
};

export const INTENSITY_BADGE_CLASS = {
  critical: "text-bg-danger",
  degraded: "text-bg-warning",
  initial: "text-bg-secondary",
};

/** The raise screen's three buttons: what the operator sees, in plain words. */
export const INTENSITY_CHOICES = [
  { value: "critical", label: "Stopped", hint: "Breakdown: it cannot run" },
  { value: "degraded", label: "Running, reduced", hint: "Defect: slow, poor quality, needs care" },
  { value: "initial", label: "Early signs", hint: "Defect: noise, smell, small leak" },
];

export const STATE_LABELS = {
  raised: "Raised",
  acknowledged: "Acknowledged",
  in_progress: "In progress",
  back_in_service: "Back in service",
  closed: "Closed",
};

/** The list's filters (the API's intensity and state arguments). */
export const INTENSITY_FILTERS = [
  ["", "Breakdowns and defects"],
  ["breakdown", "Breakdowns"],
  ["defect", "Defects"],
];
export const STATE_FILTERS = [
  ["open", "Open"],
  ["closed", "Closed"],
  ["all", "All"],
];

/** The timeline's event names; S018 adds its own. */
export const EVENT_LABELS = {
  raised: "Raised",
};

export function isBreakdown(intensity) {
  return intensity === BREAKDOWN_INTENSITY;
}

const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

/**
 * How long ago the event happened, short: "12 min", "3 h", "2 d". Whole units, rounded
 * down; a time a few minutes ahead (a fast phone clock) reads "0 min". "" for a value that
 * is not a date. `now` is passed in so the result can be tested.
 */
export function ageText(occurredAt, now = new Date()) {
  const at = new Date(occurredAt);
  if (typeof occurredAt !== "string" || Number.isNaN(at.getTime())) return "";
  const ms = Math.max(0, now.getTime() - at.getTime());
  if (ms < HOUR_MS) return `${Math.floor(ms / MINUTE_MS)} min`;
  if (ms < DAY_MS) return `${Math.floor(ms / HOUR_MS)} h`;
  return `${Math.floor(ms / DAY_MS)} d`;
}

/** What the list shows of a ticket's problem: the symptom, else the start of the description. */
export function problemText(ticket, max = 80) {
  if (ticket.failure_mode) return ticket.failure_mode.label;
  const text = ticket.description ?? "";
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

/**
 * The value for <input type="datetime-local"> from a Date, in the phone's local time:
 * "2026-10-20T14:05". The plant and its phones are in IST, and the server reads it as IST.
 */
export function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
