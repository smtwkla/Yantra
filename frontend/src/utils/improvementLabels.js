// Words and small helpers for the improvement screens (S068; the record is S067's).
import { minutesText, toLocalDateValue } from "./ticketLabels";

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
