/**
 * Ticket labels — pure display helpers for the ticket screens (S017, S018, S019). The backend's
 * tickets_core holds the rules; these only name the values.
 *
 * Intensity is ISO 14224's failure impact: critical (stopped: a breakdown), degraded
 * (running, reduced: a defect) or initial (early signs: a defect).
 */
import { formatDateTime } from "./datetime";

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
  scheduled: "Scheduled",
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
  ["scheduled", "Scheduled"],
  ["overdue", "Overdue"],
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
  scheduled: "Scheduled",
  rescheduled: "Plan changed",
  note: "Note", // S027: a work note
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

/** tickets_core.MAX_BACKDATE_DAYS; the server checks the limit, this only starts the hint below. */
export const MAX_BACKDATE_DAYS = 7;

/**
 * S028 § 4.5: how far back an entered time is, once it is more than MAX_BACKDATE_DAYS back:
 * "That was 412 days ago", so a wrong year or month is seen before saving.  `entered` is the
 * field's value ("YYYY-MM-DDTHH:MM", local), `now` a Date; "" for anything else (empty,
 * unparsable, in the future, or not far enough back).  Display only.
 */
export function daysAgoHint(entered, now) {
  if (!entered) return "";
  const at = new Date(entered);
  if (Number.isNaN(at.getTime())) return "";
  const days = Math.floor((now.getTime() - at.getTime()) / 86_400_000);
  return days > MAX_BACKDATE_DAYS ? `That was ${days} days ago` : "";
}

// ---------------------------------------------------------------------------
// Working the ticket (S018)
// ---------------------------------------------------------------------------

/** The moves set apart from the chain buttons, outline style (§ 1, BR3-02). */
export const SIGNIFICANT_MOVES = ["close", "not-a-fault", "send-back"];

/** The plan moves (S019): in outline beside Change severity, so the chain's next step stays the obvious tap (BR2-09). */
export const PLAN_MOVES = ["schedule", "reschedule"];

const MOVE_LABELS = {
  acknowledge: "Acknowledge",
  start: "Start work",
  restore: "Back in service",
  schedule: "Schedule",
  reschedule: "Change plan",
  "send-back": "Send back",
  close: "Close",
  "not-a-fault": "Not a fault",
};

// The dialog's one submit, labelled for what it does
const SAVE_LABELS = {
  acknowledge: "Acknowledge",
  start: "Start work",
  restore: "Back in service",
  schedule: "Schedule",
  reschedule: "Change plan",
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

const MINUTES_PER_DAY = 24 * 60;

/**
 * Minutes as "1 h 25 min", "45 min", "2 h"; from 24 h on in days, the minutes dropped as
 * ageText does: "2 d 20 h", "3 d" (S019 BR2-03). "—" when unknown (null). `days: false` keeps
 * hours ("26 h"): labour is man-hours, not time on the calendar.
 */
export function minutesText(minutes, { days = true } = {}) {
  if (minutes === null || minutes === undefined) return "—";
  if (days && minutes >= MINUTES_PER_DAY) {
    const wholeDays = Math.floor(minutes / MINUTES_PER_DAY);
    const dayHours = Math.floor((minutes % MINUTES_PER_DAY) / 60);
    return dayHours ? `${wholeDays} d ${dayHours} h` : `${wholeDays} d`;
  }
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

// ---------------------------------------------------------------------------
// Deferred work (S019)
// ---------------------------------------------------------------------------

/**
 * Why a scheduled ticket waits: the dialog's choices. A plain copy of tickets_core.WAITING_REASONS
 * (the server checks the codes); both test suites assert the same six codes.
 */
export const WAITING_REASON_LABELS = {
  parts: "Waiting for parts",
  vendor: "At or waiting for a vendor, garage or maker",
  expert: "Waiting for an expert",
  slot: "Waiting for a production slot or shutdown",
  approval: "Waiting for a decision or approval",
  other: "Other (remark required)",
};

/**
 * EN 13306's two delays: logistic (waiting for resources: parts, a vendor, an expert) and
 * administrative (a slot, a decision); "other" is in neither.
 */
export const WAITING_REASON_DELAYS = {
  parts: "logistic",
  vendor: "logistic",
  expert: "logistic",
  slot: "administrative",
  approval: "administrative",
  other: null,
};

export const OTHER_REASON = "other";

/** The planned date's limit after today (tickets_core.PLANNED_DATE_MAX_DAYS; the server checks it). */
export const PLANNED_DATE_MAX_DAYS = 365;

/** The reason inside a sentence: "waiting for parts"; Other reads "other reason". */
export function waitingText(reason) {
  if (reason === OTHER_REASON) return "other reason";
  const label = WAITING_REASON_LABELS[reason] ?? reason ?? "";
  return label.charAt(0).toLowerCase() + label.slice(1);
}

/**
 * The state badge's one word (BR1-13): a scheduled ticket reads Waiting when its machine is
 * down (critical), else Scheduled, and Overdue once past its planned date.
 */
export function stateLabel(ticket) {
  if (ticket.state === "scheduled") {
    if (ticket.overdue) return "Overdue";
    return isBreakdown(ticket.intensity) ? "Waiting" : "Scheduled";
  }
  return STATE_LABELS[ticket.state] ?? ticket.state;
}

/** A plan as a line: "for 25-10-2026 · waiting for parts". */
export function planText(plannedDate, reason) {
  return `for ${formatDateTime(plannedDate)} · ${waitingText(reason)}`;
}

/** The line under the ticket's header (BR2-08): the plan, or "Overdue since …" once past it. */
export function planLine(ticket) {
  if (ticket.state !== "scheduled") return "";
  if (ticket.overdue) return `Overdue since ${formatDateTime(ticket.planned_date)} · ${waitingText(ticket.waiting_reason)}`;
  return planText(ticket.planned_date, ticket.waiting_reason);
}

/** The list's red badge on an overdue row: "Overdue since 25-10". */
export function overdueBadge(plannedDate) {
  return `Overdue since ${formatDateTime(plannedDate).slice(0, 5)}`;
}

/**
 * The plan text of each timeline event (BR2-08), from the events' own plan columns:
 * scheduled "for 25-10-2026 · waiting for parts"; rescheduled the same with "(was …)", the
 * old plan read from the previous scheduled or rescheduled event; "" for any other event.
 */
export function planChanges(events) {
  let previous = null;
  return events.map((e) => {
    if (e.event !== "scheduled" && e.event !== "rescheduled") return "";
    const plan = `${formatDateTime(e.planned_date)} · ${waitingText(e.waiting_reason)}`;
    const was = e.event === "rescheduled" && previous ? ` (was ${previous})` : "";
    previous = plan;
    return `for ${plan}${was}`;
  });
}

/**
 * The waiting split of the times card: per reason, in the reasons' own words, then EN 13306's
 * logistic and administrative totals, summed from WAITING_REASON_DELAYS. -> {reasons:
 * [{reason, label, minutes}], logistic, administrative}; a total is null when no reason of its
 * kind was met.
 */
export function waitingSplit(byReason) {
  const reasons = Object.keys(WAITING_REASON_LABELS)
    .filter((code) => byReason?.[code] !== undefined)
    .map((code) => ({ reason: code, label: WAITING_REASON_LABELS[code], minutes: byReason[code] }));
  const total = (kind) => {
    const met = reasons.filter((r) => WAITING_REASON_DELAYS[r.reason] === kind);
    return met.length ? met.reduce((sum, r) => sum + r.minutes, 0) : null;
  };
  return { reasons, logistic: total("logistic"), administrative: total("administrative") };
}

/** Start and Back in service ask this when the move says so (S019 § 1.7, BR1-14). */
export function machineStoppedQuestion(move) {
  return move === "start" ? "Is the machine stopped for this work?" : "Was the machine stopped for this work?";
}

export const MACHINE_STOPPED_CHOICES = [
  { value: true, label: "Yes, machine stopped" },
  { value: false, label: "No, machine running" },
];

// --- S020: parts used ---------------------------------------------------------------------

/** The units a parts line is counted in (tickets_core.PART_UNITS; the API checks them). */
export const PART_UNITS = ["nos", "set", "m", "L", "kg"];

/** Where a part number comes from, worded for the floor (§ 1.3); generic first, the default. */
export const PART_KIND_CHOICES = [
  { value: "generic", label: "A standard number (6205-2RS, a filter spec)" },
  { value: "maker", label: "From the maker's drawing or quote" },
];
export const DEFAULT_PART_KIND = "generic";

/** The kind as the parts list shows it, after the number. */
export const PART_KIND_SHORT = { maker: "maker's number", generic: "standard number" };

/** "1.50" (as the API sends a quantity) -> "1.5"; "2.00" -> "2". */
export function quantityText(quantity) {
  return String(Number(quantity));
}

/** A suggestion or line as one row: "description · number · maker", the empty parts left out. */
export function partText(part) {
  return [part.description, part.part_number, part.maker].filter(Boolean).join(" · ");
}

/** The suggestions whose description, number or maker contains `typed` (any case); all when empty. */
export function matchingParts(parts, typed) {
  const needle = (typed ?? "").trim().toLowerCase();
  if (!needle) return parts;
  return parts.filter((p) => partText(p).toLowerCase().includes(needle));
}

// --- S029: the ticket light on the equipment list -----------------------------------------

/** The bulb's tooltip and accessible name per `ticket_light` of a list row (null: no ticket:read there). */
export const TICKET_LIGHT_LABELS = {
  down: "Down — breakdown open",
  open: "Open ticket",
  none: "No open ticket",
  hidden: "Tickets not shown",
};

/** The list's Tickets filter: the value in the URL (`tickets=`) and its text; "" = no filter. */
export const TICKET_FILTER_CHOICES = [
  ["", "All equipment"],
  ["down", "Down now"],
  ["open", "Any open ticket"],
];
