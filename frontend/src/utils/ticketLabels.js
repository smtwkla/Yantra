/**
 * Ticket labels — pure display helpers for the ticket screens (S017, S018). The backend's
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

/** The timeline's event names (S017 raised; S018 the rest). */
export const EVENT_LABELS = {
  raised: "Raised",
  acknowledged: "Acknowledged",
  started: "Work started",
  back_in_service: "Back in service",
  sent_back: "Sent back",
  closed: "Closed",
  closed_not_a_fault: "Closed — not a fault",
  regraded: "Severity changed",
  edited: "Edited",
  assigned: "Assigned",
  unassigned: "Unassigned",
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

// ---------------------------------------------------------------------------
// Working the ticket (S018)
// ---------------------------------------------------------------------------

/** The moves set apart from the chain buttons, outline style (§ 1, BR3-02). */
export const SIGNIFICANT_MOVES = ["close", "not-a-fault", "send-back"];

const MOVE_LABELS = {
  acknowledge: "Acknowledge",
  start: "Start work",
  restore: "Back in service",
  "send-back": "Send back",
  close: "Close",
  "not-a-fault": "Not a fault",
};

// The dialog's one submit, labelled for what it does
const SAVE_LABELS = {
  acknowledge: "Acknowledge",
  start: "Start work",
  restore: "Back in service",
  "send-back": "Send back",
  close: "Close ticket",
  "not-a-fault": "Close as not a fault",
};

/** A move's button: on a defect the machine never stopped, so back in service reads "Fixed". */
export function moveLabel(move, intensity) {
  if (move === "restore" && !isBreakdown(intensity)) return "Fixed";
  return MOVE_LABELS[move] ?? move;
}

export function moveSaveLabel(move, intensity) {
  if (move === "restore" && !isBreakdown(intensity)) return "Fixed";
  return SAVE_LABELS[move] ?? move;
}

/** The back-in-service time's label, by intensity as the move's button (S018 § 1; the raise's Already fixed, A1). */
export function restoreTimeLabel(intensity) {
  return isBreakdown(intensity) ? "Back in service at" : "Fixed at";
}

/** The raise screen's Save: with *Already fixed* ticked it also marks the ticket back in service (A1). */
export function raiseSaveLabel(alreadyFixed, intensity) {
  if (!alreadyFixed) return "Save ticket";
  return `Raise and mark ${moveSaveLabel("restore", intensity).toLowerCase()}`;
}

/** The line above Save for the moves that end or undo something (BR3-02). */
export function moveConsequence(move, serial) {
  if (move === "close" || move === "not-a-fault") return `${serial} becomes read-only.`;
  return "";
}

/** Send back asks whether the machine is down, worded for the ticket's intensity (BR3-10). */
export function sendBackQuestion(intensity) {
  return isBreakdown(intensity) ? "Machine down again?" : "Has the machine stopped?";
}

/** The two answers with their consequence (the rule is tickets_core.send_back_intensity). */
export function sendBackChoices(intensity) {
  const breakdown = isBreakdown(intensity);
  return [
    { value: true, label: breakdown ? "Yes — downtime runs again from now" : "Yes — it becomes a breakdown; downtime runs from now" },
    { value: false, label: breakdown ? "No — the machine runs; downtime stops" : "No — the machine runs" },
  ];
}

export const SEND_BACK_HELP =
  "Send back when the work is not finished or not accepted. If the machine ran and the same fault came back, use Not fixed — raise again.";

/** Whether `to` is a lower severity than `from` (the INTENSITY_CHOICES order: critical first). */
export function isLowering(from, to) {
  const order = INTENSITY_CHOICES.map((c) => c.value);
  return order.indexOf(to) > order.indexOf(from);
}

/**
 * The intensity text of each timeline event, from the events' own `intensity` column: the
 * first one ("Breakdown"), then each change as "Defect → Breakdown"; "" where the event did
 * not change it.
 */
export function intensityChanges(events) {
  let current = null;
  return events.map((e) => {
    if (!e.intensity) return "";
    const text = current && current !== e.intensity
      ? `${INTENSITY_LABELS[current]} → ${INTENSITY_LABELS[e.intensity]}`
      : INTENSITY_LABELS[e.intensity];
    current = e.intensity;
    return text;
  });
}

/** Minutes as "1 h 25 min", "45 min", "2 h"; "—" when unknown (null). */
export function minutesText(minutes) {
  if (minutes === null || minutes === undefined) return "—";
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `${rest} min`;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

export function firstName(name) {
  return (name ?? "").trim().split(/\s+/)[0];
}

/**
 * The people picker's groups (§ 5.8, BR3-07, BR4-03): the user's own person first, then the
 * ticket's assignees, then the maintenance ladder (assignable), then everyone else the field
 * allows; filtered by `filter` (part of the name, any case). `excludeIds` are left out (the
 * Assign dialog leaves out who is assigned); `assignableOnly` keeps the ladder only.
 * -> [{label, people}], empty groups left out.
 */
export function groupPeople(people, { ownId = null, assigneeIds = [], excludeIds = [], assignableOnly = false, filter = "" } = {}) {
  const needle = filter.trim().toLowerCase();
  const shown = people.filter((p) => !excludeIds.includes(p.id)
    && (!assignableOnly || p.assignable)
    && (!needle || p.name.toLowerCase().includes(needle)));
  const groups = [
    { label: "You", people: shown.filter((p) => p.id === ownId) },
    { label: "Assigned", people: shown.filter((p) => p.id !== ownId && assigneeIds.includes(p.id)) },
    { label: "Maintenance", people: shown.filter((p) => p.id !== ownId && !assigneeIds.includes(p.id) && p.assignable) },
    { label: "Others at the site", people: shown.filter((p) => p.id !== ownId && !assigneeIds.includes(p.id) && !p.assignable) },
  ];
  return groups.filter((g) => g.people.length);
}

/** A local date for <input type="date">: "2026-10-20". */
export function toLocalDateValue(date) {
  return toLocalInputValue(date).slice(0, 10);
}
