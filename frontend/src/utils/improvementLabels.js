// Words and small helpers for the improvement screens (S068; the record is S067's).
import { formatDate } from "./datetime";
import { INTENSITY_LABELS, minutesText, toLocalDateValue } from "./ticketLabels";

// S072 D13: the floor reads the badge, so the closed states say what happened in plain words;
// ISO's terms (effective, not effective) stay in the API codes
export const IMPROVEMENT_STATE_LABELS = {
  analysing: "Analysing",
  actions_open: "Actions open",
  watching: "Watching",
  ready_to_verify: "Ready to verify",
  closed_effective: "Closed: it worked",
  closed_not_effective: "Closed: did not work",
  dropped: "Dropped",
};

/** The state's words; an unknown state (a later step's) is shown as it came. */
export function improvementStateLabel(state) {
  return IMPROVEMENT_STATE_LABELS[state] ?? state;
}

/** The list's State choices (the API's `state` argument). */
export const IMPROVEMENT_STATE_FILTERS = [
  ["open", "Open improvements"],
  ["closed", "Closed improvements"],
];

export const TITLE_MAX = 120;
export const PROBLEM_MAX = 2000;

const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;

/**
 * One loss text for the page and the list (BR1-12): "2 tickets, 1 breakdown · down 1 d 7 h",
 * "1 ticket, 0 breakdowns · no downtime". `loss` = {tickets, breakdowns, downtime_minutes}.
 */
export function lossText(loss) {
  const down = loss.downtime_minutes > 0 ? `down ${minutesText(loss.downtime_minutes)}` : "no downtime";
  return `${plural(loss.tickets, "ticket")}, ${plural(loss.breakdowns, "breakdown")} · ${down}`;
}

/** "HP003: Won't start": the machine and the symptom, else the first line of the description; at most 120 characters. */
export function defaultTitle(ticket) {
  const what = ticket.failure_mode?.label ?? (ticket.description ?? "").trim().split("\n")[0].trim();
  const text = what ? `${ticket.machine.code}: ${what}` : ticket.machine.code;
  return text.slice(0, TITLE_MAX);
}

// The why-why chain and the root cause (S069): the API's bounds, for the fields' maxlength
export const QUESTION_MAX = 300;
export const ANSWER_MAX = 1000;
export const EVIDENCE_MAX = 500;
// The body of an Add or Edit why. An edit sends the place only when the user changed it
// (S069 A1): on an out-of-date page the opened place may not be the why's place any more.
export function whyBody(form, isEdit, openedPosition) {
  const body = { question: form.question, answer: form.answer, evidence: form.evidence.trim() ? form.evidence : null };
  if (isEdit && Number(form.position) !== openedPosition) body.position = Number(form.position);
  return body;
}

export const ROOT_CAUSE_MAX = 500;
export const CONTRIBUTING_MAX = 2000;

/** A failure cause as one line: "4.2 Management error". */
export function causeText(cause) {
  return `${cause.code} ${cause.label}`;
}

/** The distinct causes of the linked tickets, in code order; a ticket with no cause yet adds nothing. */
export function ticketCauses(tickets) {
  const byId = new Map();
  for (const t of tickets) if (t.cause) byId.set(t.cause.id, t.cause);
  return [...byId.values()].sort((a, b) => a.code.localeCompare(b.code, undefined, { numeric: true }));
}

/** The root cause's first text: the last why's answer (TPM: the chain ends at the root cause), cut to 500. */
export function defaultRootCause(whys) {
  return (whys.at(-1)?.answer ?? "").slice(0, ROOT_CAUSE_MAX);
}

/** The ticket's description; with none, the symptom; with neither, empty. At most 2000 characters. */
export function defaultProblem(ticket) {
  const text = (ticket.description ?? "").trim() || ticket.failure_mode?.label || "";
  return text.slice(0, PROBLEM_MAX);
}

// Countermeasures (S071; the record and the rules are S070's)
export const ACTION_TEXT_MAX = 500;
export const DONE_TEXT_MAX = 1000;
export const CANCEL_REASON_MAX = 500;
export const DEFAULT_DUE_DAYS = 14;

/** The six kinds with the one plain sentence each: S070 § 2's words, shown where the kind is chosen and under the card. */
export const ACTION_KINDS = [
  { key: "correction", label: "Correction", sentence: "Fixes this failure now, often already done on the ticket." },
  { key: "corrective", label: "Corrective", sentence: "Removes the cause here, so this failure does not come back." },
  { key: "preventive", label: "Preventive", sentence: "Adds regular work that stops the failure before it happens." },
  { key: "design_out", label: "Design-out", sentence: "Changes the machine so this failure cannot happen." },
  { key: "lesson", label: "Lesson", sentence: "Teaches the team what was learned." },
  { key: "spread", label: "Spread", sentence: "Applies the fix to the similar machines." },
];

/** The kind's label; an unknown key is returned as it came. */
export function actionKindLabel(key) {
  return ACTION_KINDS.find((k) => k.key === key)?.label ?? key;
}

export const ACTION_STATE_LABELS = { open: "Open", done: "Done", cancelled: "Cancelled" };

/** "Overdue 1 day", "Overdue 2 days"; 0 or less is "". */
export function overdueText(days) {
  if (!(days > 0)) return "";
  return `Overdue ${days} ${days === 1 ? "day" : "days"}`;
}

/** "2 of 6 done" from the detail's `action_counts`; cancelled ones are in neither number; "" with none left. */
export function actionCountsText(counts) {
  const total = counts.open + counts.done;
  return total > 0 ? `${counts.done} of ${total} done` : "";
}

/** The first due date offered: `today` (a Date) plus two weeks, "YYYY-MM-DD"; "" without a date. */
export function defaultDueDate(today) {
  if (!today) return "";
  const due = new Date(today);
  due.setDate(due.getDate() + DEFAULT_DUE_DAYS);
  return toLocalDateValue(due);
}

// The watch, the closes and the timeline (S073; the rules and the API are S072's)
export const WATCH_DAYS_MIN = 30;
export const WATCH_DAYS_MAX = 365;
export const NOTE_MAX = 1000;
// Not REMARK_MAX: ticketLabels.REMARK_MAX is the ticket's 120
export const CLOSE_REMARK_MAX = 1000;

/** The state badge's colour (S073 § 5.1); the open states keep the plain light badge. */
export const IMPROVEMENT_STATE_BADGE = {
  ready_to_verify: "text-bg-warning",
  closed_effective: "text-bg-success",
  closed_not_effective: "text-bg-danger",
  dropped: "text-bg-secondary",
};

/** The class of the state badge. */
export function improvementStateBadgeClass(state) {
  return IMPROVEMENT_STATE_BADGE[state] ?? "text-bg-light border";
}

export const IMPROVEMENT_EVENT_LABELS = {
  started: "Started",
  edited: "Changed",
  ticket_linked: "Ticket added",
  ticket_removed: "Ticket removed",
  why_added: "Why added",
  why_changed: "Why changed",
  why_removed: "Why removed",
  root_cause_set: "Root cause set",
  root_cause_changed: "Root cause changed",
  action_added: "Countermeasure added",
  action_changed: "Countermeasure changed",
  action_done: "Countermeasure done",
  action_cancelled: "Countermeasure cancelled",
  state_changed: "State changed",
  note: "Note",
  closed_effective: "Closed: it worked",
  closed_not_effective: "Closed: did not work",
  dropped: "Dropped",
  watch_ended: "Watch ended — ready to verify",
};

/** The timeline event's words; an unknown event is shown as it came. */
export function eventLabel(event) {
  return IMPROVEMENT_EVENT_LABELS[event] ?? event;
}

/**
 * The day `days` after the date part of an IST string ("2026-11-20T15:30:00+05:30"), "YYYY-MM-DD".
 * Calendar arithmetic on the date part in UTC, so the browser's time zone and summer time never
 * move it (BR1-02); "" for anything that is not a date.
 */
export function watchEndDate(from, days) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(typeof from === "string" ? from : "");
  if (!m) return "";
  const end = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]) + Number(days)));
  return end.toISOString().slice(0, 10);
}

/** The header's line while the watch has not been closed: before it starts, running, or ready. */
export function watchLine(improvement) {
  const { watch, state } = improvement;
  if (state === "watching") return `Watching since ${formatDate(watch.from)} · until ${formatDate(watch.until)}`;
  if (state === "ready_to_verify") return `Watched ${watch.days} days, until ${formatDate(watch.until)} · ready to verify`;
  if (state === "analysing" || state === "actions_open") return `Watch: ${watch.days} days after the last countermeasure is done`;
  return "";
}

const CLOSED_WORDS = { closed_effective: ["Closed", ": it worked"], closed_not_effective: ["Closed", ": did not work"], dropped: ["Dropped", ""] };

/** "Closed 18-02-2027 by Arun (manager): it worked"; ", the lead" after the name when the lead closed it. */
export function closedLine(closed, state) {
  const [word, outcome] = CLOSED_WORDS[state] ?? ["Closed", ""];
  return `${word} ${formatDate(closed.at)} by ${closed.by_name}${closed.by_lead ? ", the lead" : ""}${outcome}`;
}

/** The watch's machines as one text: "MCC1, MCC2". */
export const machinesText = (figures) => figures.machines.map((m) => m.code).join(", ");

/** The watch's symptoms as one text: "Won't start or Trips". */
export const symptomsText = (figures) => figures.symptoms.map((s) => s.label).join(" or ");

const dayCount = (days, ending) => `${days} days ${ending}`;

/**
 * The figures table (S073 § 5.2): `{headers: ["", before, third], rows: [{label, before, after}]}`.
 * The third header is built from `after.days` in every case (BR2-01): "… days after" once the
 * improvement is closed or the watch has ended, else "… days so far".
 */
export function figureRows(figures, closed, ended = false) {
  const { before, after, symptoms } = figures;
  const rows = [{ label: "Breakdowns", before: String(before.breakdowns), after: String(after.breakdowns) }];
  if (symptoms.length) {
    rows.push({
      label: `Of them: ${symptomsText(figures)}`,
      before: String(before.symptom_breakdowns), after: String(after.symptom_breakdowns),
    });
  }
  rows.push({ label: "Downtime", before: minutesText(before.downtime_minutes), after: minutesText(after.downtime_minutes) });
  return {
    headers: ["", dayCount(before.days, "before"), dayCount(after.days, closed || ended ? "after" : "so far")],
    rows,
  };
}

/** A repeat after its serial: "on 05-01-2027 (Won't start, breakdown)", "after the watch" when past the end. */
export function repeatText(repeat) {
  const parts = [];
  if (repeat.symptom) parts.push(repeat.symptom.label);
  parts.push((INTENSITY_LABELS[repeat.intensity] ?? repeat.intensity).toLowerCase());
  if (!repeat.in_watch) parts.push("after the watch");
  return `on ${formatDate(repeat.occurred_at)} (${parts.join(", ")})`;
}
