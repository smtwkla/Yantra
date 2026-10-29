// Words and small helpers for the improvement screens (S068; the record is S067's).
import { minutesText } from "./ticketLabels";

export const IMPROVEMENT_STATE_LABELS = {
  analysing: "Analysing",
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

/** The ticket's description; with none, the symptom; with neither, empty. At most 2000 characters. */
export function defaultProblem(ticket) {
  const text = (ticket.description ?? "").trim() || ticket.failure_mode?.label || "";
  return text.slice(0, PROBLEM_MAX);
}
