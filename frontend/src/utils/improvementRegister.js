// Pure helpers of the improvement register's print page (S076). The figures come from the API
// (improvement_register_core.py); this file only words them and builds the page's link.
import { formatDate } from "./datetime";
import { improvementStateLabel } from "./improvementLabels";

// The age columns of the open table, by the API's band keys (D7)
export const AGE_BAND_LABELS = {
  "0_30": "0–30 days",
  "31_90": "31–90 days",
  "91_180": "91–180 days",
  over_180: "Over 180 days",
};

/** The address of the register page; empty values are left out. `query` = {site_id, from, to}. */
export function registerPath(query = {}) {
  const params = new URLSearchParams();
  for (const key of ["site_id", "from", "to"]) {
    const value = query[key];
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const text = params.toString();
  return text ? `/tickets/improvements/register?${text}` : "/tickets/improvements/register";
}

const pad = (n) => String(n).padStart(2, "0");

/**
 * The month `monthsBack` months before the month of `todayIso` ("YYYY-MM-DD", the server's IST date):
 * `{from, to}` as "YYYY-MM-DD". Works on the string's year and month only, never through `new Date()`
 * and the browser's zone, so a laptop west of UTC does not shift the month (BR1-13).
 */
export function monthPeriod(todayIso, monthsBack) {
  const [year, month] = todayIso.split("-").map(Number);
  const index = year * 12 + (month - 1) - monthsBack;
  const y = Math.floor(index / 12);
  const m = (index % 12) + 1;
  // Day 0 of the next month is this month's last day; UTC arithmetic on plain numbers, no zone involved
  const lastDay = new Date(Date.UTC(y, m, 0)).getUTCDate();
  return { from: `${y}-${pad(m)}-01`, to: `${y}-${pad(m)}-${pad(lastDay)}` };
}

/** "01-10-2026 to 31-10-2026" for `{from, to}` ("YYYY-MM-DD"). */
export function periodText(period) {
  return `${formatDate(period.from)} to ${formatDate(period.to)}`;
}

/** The closed section's line: the three counts, then the share that worked, or why there is none. */
export function workedShareText(closed) {
  const counts = [
    `${improvementStateLabel("closed_effective")} ${closed.it_worked}`,
    `${improvementStateLabel("closed_not_effective")} ${closed.did_not_work}`,
    `${improvementStateLabel("dropped")} ${closed.dropped}`,
  ].join(" · ");
  if (closed.worked_share === null || closed.worked_share === undefined) {
    return `${counts} · No improvement was verified in this period.`;
  }
  return `${counts} · it worked in ${closed.worked_share} % of the verified closes`;
}

/** An open improvement's countermeasures: "2 open, 1 overdue", "2 open", or "None open". */
export function actionsText(item) {
  if (item.actions_open === 0) return "None open";
  const open = `${item.actions_open} open`;
  return item.actions_overdue > 0 ? `${open}, ${item.actions_overdue} overdue` : open;
}
