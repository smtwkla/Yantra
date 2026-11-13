/**
 * PM — the labels and the request bodies of the PM screens. S104 (docs/steps/S104-pm-templates-one-path/1-brief.md
 * § 5.10): the work is written once on a PM template (Masters › PM templates, the template page, the item dialog); a
 * machine's plan holds only its own settings (the plan page, the PM card, the attach dialog). Display and plain
 * conversion only: every rule is the backend's (pm_templates_core, pm_plans_core), which judges each save.
 */
import { formatDate, formatDateTime } from "./datetime";
import { formatReading } from "./meterLabels";
import { roleLabel } from "./siteRoles";

export const ITEM_TYPES = [
  { value: "task", label: "Task", badge: "text-bg-secondary", legend: "Task: done or not done." },
  { value: "check", label: "Check", badge: "text-bg-light border", legend: "Check: OK, Not OK or NA." },
  {
    value: "reading",
    label: "Reading",
    badge: "text-bg-info",
    legend: "Reading: a measurement with its own limits, or a reading of the machine's meter.",
  },
];

// pm_templates_core.READING_KINDS, with the words of mock-up 14
export const READING_KINDS = [
  { value: "measurement", label: "Measurement", help: "A value with its own unit and limits. It stays on the job only." },
  {
    value: "meter",
    label: "Meter reading",
    // S104 A1.6.7: the machine's own meter or a linked one
    help: "Saved as a reading of the machine's meter of this type, its own or a linked one, as if logged on the "
      + "Readings sheet.",
  },
];

export const PHOTO_SETTINGS = [
  { value: "none", label: "No photo" },
  { value: "optional", label: "Optional" },
  { value: "required", label: "Required" },
];

export const PERFORMERS = [
  { value: "maintenance", label: "Maintenance" },
  { value: "operator", label: "Operator" },
];

// pm_schedule_core.CALENDAR_UNITS, in its order, with the word the "every N …" line shows
export const CALENDAR_UNITS = [
  { value: "day", label: "days" },
  { value: "week", label: "weeks" },
  { value: "month", label: "months" },
  { value: "year", label: "years" },
];

const byValue = (list, value) => list.find((entry) => entry.value === value);

export const itemType = (value) => byValue(ITEM_TYPES, value) ?? ITEM_TYPES[1];
export const photoLabel = (value) => byValue(PHOTO_SETTINGS, value)?.label ?? value;
export const performerLabel = (value) => byValue(PERFORMERS, value)?.label ?? value;
export const readingKind = (value) => byValue(READING_KINDS, value) ?? null;

/** The two ticks → the template's trigger_kind; neither is null, which the API refuses with its own words. */
export function kindFromTicks(calendarOn, meterOn) {
  if (calendarOn && meterOn) return "both";
  if (calendarOn) return "calendar";
  if (meterOn) return "meter";
  return null;
}

/** A person in the assignee select and on the card: "Kannan (Technician)", "Ravi (Technician) · Atlas Copco". */
export function personLabel(person) {
  const name = person.role ? `${person.name} (${roleLabel(person.role)})` : person.name;
  return person.vendor_name ? `${name} · ${person.vendor_name}` : name;
}

const textOrNull = (value) => (typeof value === "string" && value.trim() ? value.trim() : null);
const idOrNull = (value) => (value === "" || value == null ? null : Number(value));

// A whole number as typed: a number when it is digits only, else the text, so the API refuses it in its words
function wholeOrRaw(value) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  return /^\d+$/.test(text) ? Number(text) : text;
}

/** A template item as the page holds it (the API's item shape) → the body the template save and the check take. */
export function savedItemBody(item) {
  return {
    id: item.id ?? null,
    item_type: item.item_type,
    text: item.text,
    help_text: item.help_text ?? null,
    photo: item.photo,
    reading_kind: item.reading_kind ?? null,
    unit: item.unit ?? null,
    min_value: item.min_value ?? null,
    max_value: item.max_value ?? null,
    meter_type_id: item.meter_type?.id ?? null,
  };
}

/**
 * The item dialog's form → the body of the check route (§ 5.2). Fields the item's type or reading kind hides are
 * sent as null: a Task or Check sends no reading field; a Measurement its unit and limits; a Meter reading its meter
 * type (S104 A1: no parent tick; a part uses a node above's meter through a link on its Meters card).
 */
export function itemBody(form) {
  const reading = form.item_type === "reading";
  const measurement = reading && form.reading_kind === "measurement";
  const meter = reading && form.reading_kind === "meter";
  return {
    id: form.id ?? null,
    item_type: form.item_type,
    text: form.text,
    help_text: textOrNull(form.help_text),
    photo: form.photo,
    reading_kind: reading ? form.reading_kind || null : null,
    unit: measurement ? textOrNull(form.unit) : null,
    min_value: measurement ? textOrNull(form.min_value) : null,
    max_value: measurement ? textOrNull(form.max_value) : null,
    meter_type_id: meter ? idOrNull(form.meter_type_id) : null,
  };
}

/** A blank item form (S096 § 5.10: a Check with an optional photo; the one-tap path). */
export function blankItemForm() {
  return { id: null, item_type: "check", text: "", help_text: "", photo: "optional", reading_kind: "", unit: "",
    min_value: "", max_value: "", meter_type_id: "" };
}

/** An item of the page → the dialog's form. */
export function itemForm(item) {
  return {
    id: item.id ?? null,
    item_type: item.item_type,
    text: item.text,
    help_text: item.help_text ?? "",
    photo: item.photo,
    reading_kind: item.reading_kind ?? "",
    unit: item.unit ?? "",
    min_value: item.min_value ?? "",
    max_value: item.max_value ?? "",
    meter_type_id: item.meter_type?.id ?? "",
  };
}

/** The template page's form for a new template: unticked triggers, every 1 month ready for the tick. */
export function newTemplateForm() {
  return { name: "", performer: "maintenance", needs_verification: true, calendarOn: false, calendar_every: "1",
    calendar_unit: "month", meterOn: false, meter_type_id: "", meter_every: "" };
}

/** A template of the API → the page's form. */
export function templateForm(template) {
  const calendarOn = template.trigger_kind === "calendar" || template.trigger_kind === "both";
  const meterOn = template.trigger_kind === "meter" || template.trigger_kind === "both";
  return {
    name: template.name,
    performer: template.performer,
    needs_verification: template.needs_verification,
    calendarOn,
    calendar_every: calendarOn ? String(template.calendar_every) : "1",
    calendar_unit: template.calendar_unit ?? "month",
    meterOn,
    meter_type_id: template.meter_type?.id ?? "",
    meter_every: template.meter_every ?? "",
  };
}

/**
 * The page's form and its items → the body of a template save (§ 5.1): every field, `null` for an unticked
 * trigger's fields (their typed values stay in the form); the items in their order, each with its id when it has
 * one.
 */
export function templateBody(form, items) {
  return {
    name: form.name,
    performer: form.performer,
    needs_verification: Boolean(form.needs_verification),
    trigger_kind: kindFromTicks(form.calendarOn, form.meterOn),
    calendar_every: form.calendarOn ? wholeOrRaw(form.calendar_every) : null,
    calendar_unit: form.calendarOn ? form.calendar_unit : null,
    meter_type_id: form.meterOn ? idOrNull(form.meter_type_id) : null,
    meter_every: form.meterOn ? textOrNull(String(form.meter_every ?? "")) : null,
    items: items.map(savedItemBody),
  };
}

// pm_templates_core.SCHEDULE_FIELDS: a save that changes one moves the jobs of every machine (§ 5.6, BR1-08)
const SCHEDULE_FIELDS = ["trigger_kind", "calendar_every", "calendar_unit", "meter_type_id", "meter_every"];

/** Does the body change the stored template's schedule? (`template`: the API's detail; null for a new one.) */
export function scheduleChanged(template, body) {
  if (!template) return false;
  const stored = templateBody(templateForm(template), []);
  return SCHEDULE_FIELDS.some((field) => String(stored[field] ?? "") !== String(body[field] ?? ""));
}

/** The confirmation before a schedule change on several machines (§ 5.6, BR1-08). */
export function scheduleChangeQuestion(count) {
  return `Change the schedule for ${count} machines? Their jobs move to the new interval. Jobs already started are not changed.`;
}

/** "3 machines", "1 machine". */
export function machinesText(count) {
  return `${count} ${count === 1 ? "machine" : "machines"}`;
}

/** "Used on 3 machines", "Used on 1 machine", "Not used on any machine yet". */
export function usedOnText(count) {
  if (!count) return "Not used on any machine yet";
  return `Used on ${machinesText(count)}`;
}

/** The confirmation before a template is deactivated (§ 5.6): what happens to its machines, by their count. */
export function deactivateQuestion(count) {
  if (!count) return "Deactivate this template? No machine uses it yet.";
  const stop = count === 1 ? "stops" : "stop";
  return `Deactivate this template? Its ${machinesText(count)} ${stop} getting jobs. Jobs already started can be finished.`;
}

/** The note after a template save: "Saved.", or, when some machines were not settled, how many update at the daily run. */
export function savedNoteText(plansFailed) {
  return plansFailed > 0 ? `Saved. ${machinesText(plansFailed)} will update at the next daily run.` : "Saved.";
}

/** "7 items", "1 item". */
export function itemCountText(count) {
  return `${count} ${count === 1 ? "item" : "items"}`;
}

/** A template's summary on the plan page: "7 items · Maintenance · an engineer verifies". */
export function templateSummary(template) {
  return [itemCountText(template.item_count), performerLabel(template.performer),
    template.needs_verification ? "an engineer verifies" : "no verification"].join(" · ");
}

/** A template row of Masters › PM templates: "Every month or 250 h, whichever comes first · 7 items · 3 machines". */
export function templateRowText(template) {
  return [template.trigger_text, itemCountText(template.item_count), machinesText(template.plan_count)].join(" · ");
}

/** The list with the item at `index` moved by `step` (−1 up, +1 down); a move past either end changes nothing. */
export function moveItem(items, index, step) {
  const target = index + step;
  if (target < 0 || target >= items.length) return items;
  const moved = [...items];
  [moved[index], moved[target]] = [moved[target], moved[index]];
  return moved;
}

/** The item number an items refusal names: "Item 3: …" → 3; anything else → null. */
export function refusedItemNumber(message) {
  const match = /^Item (\d+)[: ]/.exec(message ?? "");
  return match ? Number(match[1]) : null;
}

/**
 * One meter a plan uses on its machine (§ 5.10, A1.6.7): "HP003's own Run hours", "PR-07's Run hours (linked
 * meter)" (a node above's, through the part's meter link); null for a type the machine lacks (the plan's stop remark
 * says so).
 */
export function meterUseText(meter) {
  if (!meter.equipment) return null;
  const name = meter.meter_type.name;
  return meter.from_link ? `${meter.equipment.code}'s ${name} (linked meter)` : `${meter.equipment.code}'s own ${name}`;
}

/** The card's small line: "7 items · Kannan (Technician)", "1 item · No one yet", "7 items · Operator". */
export function planSubline(plan) {
  let who = "Operator";
  if (plan.performer !== "operator") who = plan.assignee ? personLabel(plan.assignee) : "No one yet";
  return [itemCountText(plan.item_count), who].join(" · ");
}

/** The card's first line: "Press — monthly hydraulic check", a part's plan with the part first ("MOT014 · …"). */
export function planTitle(plan) {
  return plan.own ? plan.template.name : `${plan.equipment.code} · ${plan.template.name}`;
}

/**
 * The plan page's form from the plan's detail (the machine's own settings, § 5.5).  The API answers a stored meter
 * value only while the plan uses the meter it was entered for (S104 A1.6.3); otherwise `last_done_meter` is null and
 * the field starts empty.
 */
export function planSettingsForm(plan) {
  return {
    assignee_id: plan.assignee?.id ?? null,
    last_done_on: plan.last_done_on ?? "",
    last_done_meter: plan.last_done_meter ?? "",
  };
}

/**
 * The plan page's form → the body of `PUT /api/pm/plans/<id>`: the assignee (null on an operator template, § 5.5),
 * the date, and the meter value only on a template with a meter trigger and only when it differs from what the page
 * loaded (A1.6.3): an untouched field sends nothing, so a save of the assignee keeps a stored value the plan does not
 * use now; an emptied field sends null and clears it; a typed one is stored for the meter the plan uses now.
 */
export function planSettingsBody(form, plan) {
  const body = {
    assignee_id: plan.template.performer === "operator" ? null : form.assignee_id ?? null,
    last_done_on: form.last_done_on || null,
  };
  if (plan.template.meter_type) {
    const value = textOrNull(String(form.last_done_meter ?? ""));
    if (value !== (plan.last_done_meter ?? null)) body.last_done_meter = value;
  }
  return body;
}

/** The hint under the Last done fields. */
export function lastDoneHint() {
  return "When was this work last done on this machine, before Yantra? Leave it empty if you do not know.";
}

// ---------------------------------------------------------------------------
// PM jobs (docs/steps/S097-pm-jobs-due/1-brief.md § 5.9, § 5.10): the PM list and the card's job line. The
// standing comes from the server (pm_schedule_core.job_state); these only put it in words.
// ---------------------------------------------------------------------------

// pm_schedule_core's four states; the badge is the judgement (Due inside the grace, Overdue after it)
export const STANDING_LABELS = { overdue: "Overdue", due: "Due", upcoming: "Upcoming", not_yet: "Not yet due" };
export const STANDING_BADGES = {
  overdue: "text-bg-danger",
  due: "text-bg-warning",
  upcoming: "text-bg-info",
  not_yet: "text-bg-light border",
};

/** A due point is a target, not a measurement: the places it has, at most the type's decimals ("1,250 h"). */
function dueValueText(value, meterType) {
  const number = Number(value).toLocaleString("en-IN", { maximumFractionDigits: meterType.decimals });
  return meterType.unit ? `${number} ${meterType.unit}` : number;
}

/** The due point in words: "24-10-2026", "at 5,000 h", "24-10-2026 or at 3,250 h"; "" with neither. */
export function dueText(dueOn, dueMeter, meterType) {
  const date = dueOn ? formatDate(dueOn) : "";
  const meter = dueMeter != null && meterType ? `at ${dueValueText(dueMeter, meterType)}` : "";
  return [date, meter].filter(Boolean).join(" or ");
}

/** The days since the due date, after the due text: " · 1 day ago", " · 3 days ago"; "" when not past it. */
export function daysPastText(days) {
  if (!days) return "";
  return ` · ${days} ${days === 1 ? "day" : "days"} ago`;
}

/**
 * The plan's meter now: "Run hours now 5,006.5 h", "Run hours now 120.0 h · 5,120.0 h counted across a reset"
 * (the usage carried across a counter reset), or "Run hours: no reading yet"; "" for a plan without a meter.
 */
export function meterNowText(meter) {
  if (!meter) return "";
  const type = meter.meter_type;
  if (meter.value_now == null) return `${type.name}: no reading yet`;
  const now = `${type.name} now ${formatReading(meter.value_now, type)}`;
  if (!Number(meter.offset)) return now;
  return `${now} · ${formatReading(meter.value_counted, type)} counted across a reset`;
}

/** Who does the job: the assignee's name, "No one yet", or "Operator" for an operator plan. */
export function assigneeText(job) {
  if (job.plan?.performer === "operator") return "Operator";
  return job.assignee ? job.assignee.name : "No one yet";
}

/** The card's line for a plan with no open job (§ 5.10): "Next due 02-12-2026 or at 3,250 h", … */
export function nextDueText(nextDue, meter) {
  const type = meter?.meter_type;
  const due = dueText(nextDue.due_on, nextDue.due_meter, type);
  if (!nextDue.no_reading) return `Next due ${due}`;
  if (nextDue.due_on) return `Next due ${due} · ${type.name}: no reading yet`;
  return `Next due when ${type.name} has a reading`;
}

/**
 * The count line above the rows: on Due "4 due · 1 overdue · 2 in progress" (a zero part left out), on Upcoming
 * "3 upcoming", on Done "12 done" (S098: the Done tab's `total`, its pages included), on To verify "3 to verify"
 * (S099: the paged `total` too). S101: on Done the skipped jobs apart, "10 done · 2 skipped" (`totalSkipped` of
 * the `total`; a zero part left out), so a skip is never counted as done.
 */
export function countText(tab, counts, total = 0, totalSkipped = 0) {
  if (tab === "upcoming") return counts.upcoming ? `${counts.upcoming} upcoming` : "";
  if (tab === "done") {
    const doneCount = total - totalSkipped;
    return [doneCount && `${doneCount} done`, totalSkipped && `${totalSkipped} skipped`].filter(Boolean).join(" · ");
  }
  if (tab === "to_verify") return total ? `${total} to verify` : "";
  return [counts.due && `${counts.due} due`, counts.overdue && `${counts.overdue} overdue`,
    counts.in_progress && `${counts.in_progress} in progress`].filter(Boolean).join(" · ");
}

// The tabs in the mock-up's order (S099: To verify between Upcoming and Done); the paged ones
export const PM_TABS = ["due", "upcoming", "to_verify", "done"];
export const PAGED_TABS = ["to_verify", "done"];

/** The PM list's URL query → the API's query string: the tab (Due is the default), the unit, Assigned to me, the page. */
export function jobsQuery(query) {
  const params = new URLSearchParams();
  if (PM_TABS.includes(query.tab) && query.tab !== "due") params.set("tab", query.tab);
  if (query.unit_id) params.set("unit_id", query.unit_id);
  if (query.assigned === "me") params.set("assigned", "me");
  if (PAGED_TABS.includes(query.tab) && Number(query.page) > 1) params.set("page", query.page);
  return params.toString();
}

// ---------------------------------------------------------------------------
// Doing a PM job (docs/steps/S098-pm-job-phone/1-brief.md § 5.10): the job page, its row and its badges. The
// rules (what is filled, the limit state stored, who may do what) are the server's (pm_work_core).
// ---------------------------------------------------------------------------

// pm_work_core.OUTCOMES in words, and their badges on a read-only row
export const RESULT_LABELS = { ok: "OK", not_ok: "Not OK", na: "NA", done: "Done", not_done: "Not done" };
export const RESULT_BADGES = {
  ok: "text-bg-success", not_ok: "text-bg-danger", na: "text-bg-secondary", done: "text-bg-success",
  not_done: "text-bg-danger",
};
// The buttons of a check and a task, in order, with the outline colour of each
export const OUTCOME_BUTTONS = {
  check: [["ok", "success"], ["not_ok", "danger"], ["na", "secondary"]],
  task: [["done", "success"], ["not_done", "danger"]],
};
// The answers that need a remark, and the remark field's label (pm_work_core.REMARK_NEEDED)
export const REMARK_PROMPTS = { not_ok: "What is wrong?", not_done: "Why was it not done?", na: "Why is there no reading?" };
export const TIMELINESS_LABELS = { on_time: "On time", late: "Late" };
export const LIMIT_FLAG_LABELS = { high: "High", low: "Low" };

// The job's timeline (S097's events and S098's)
export const PM_EVENT_LABELS = {
  created: "Created",
  due_changed: "Due point changed",
  assignee_changed: "Assignee changed",
  cancelled: "Cancelled",
  started: "Started",
  performer_changed: "Performed by changed",
  done: "Done",
  verified: "Verified", // S099
  sent_back: "Sent back",
  rescheduled: "Rescheduled", // S101
  skipped: "Skipped",
};
// S099: said after a verify line, the verified card and the dialog when the verifier is the job's Performed by
export const SELF_VERIFIED_TEXT = "the person who did the work";
export const RUN_ACTOR = "pm_generate"; // pm_jobs_core.RUN_ACTOR: the daily run's rows

/** Who recorded a timeline line: "by Priya", or "by the daily PM run". */
export function recordedByText(event) {
  return event.created_by_name === RUN_ACTOR ? "by the daily PM run" : `by ${event.created_by_name}`;
}

/**
 * A job's badges, in order, as `[{label, badge}]`: a started job *In progress* before its standing, and *Sent
 * back* after it when an engineer sent it back (S099); a done one *Done*, a waiting one *To verify*, a verified one
 * *Verified*, each with *On time* or *Late*; a cancelled one *Cancelled*; a due one its standing. S101: a skipped one
 * *Skipped*; a due or started one that was rescheduled *Rescheduled* after its other badges.
 */
export function jobBadges(job) {
  const standing = job.standing
    ? [{ label: STANDING_LABELS[job.standing.state], badge: STANDING_BADGES[job.standing.state] }] : [];
  const moved = job.rescheduled ? [{ label: "Rescheduled", badge: "text-bg-light border" }] : [];
  if (job.state === "in_progress") {
    const sentBack = job.sent_back ? [{ label: "Sent back", badge: "text-bg-danger" }] : [];
    return [{ label: "In progress", badge: "text-bg-primary" }, ...sentBack, ...standing, ...moved];
  }
  if (job.state === "done" || job.state === "verified") {
    const judged = job.timeliness
      ? [{ label: TIMELINESS_LABELS[job.timeliness],
        badge: job.timeliness === "late" ? "text-bg-danger" : "text-bg-light border" }] : [];
    if (job.state === "verified") return [{ label: "Verified", badge: "text-bg-success" }, ...judged];
    if (job.awaits_verification) return [{ label: "To verify", badge: "text-bg-warning" }, ...judged];
    return [{ label: "Done", badge: "text-bg-success" }, ...judged];
  }
  if (job.state === "skipped") return [{ label: "Skipped", badge: "text-bg-secondary" }];
  if (job.state === "cancelled") return [{ label: "Cancelled", badge: "text-bg-secondary" }];
  return [...standing, ...moved];
}

/** What is typed in a reading against its limits, as it is typed: "high", "low", or null (inside, empty, not a number). */
export function limitFlag(raw, min, max) {
  const text = String(raw ?? "").trim();
  if (!/^-?\d+(\.\d+)?$/.test(text)) return null;
  const value = Number(text);
  if (max != null && max !== "" && value > Number(max)) return "high";
  if (min != null && min !== "" && value < Number(min)) return "low";
  return null;
}

/** A save that got no answer (no connection, or the server failed): "Not saved. <message>" (api.js says what to do). */
export function notSavedText(message) {
  return `Not saved. ${message}`;
}

/** "3 of 7 filled". */
export function filledText(filled, total) {
  return `${filled} of ${total} filled`;
}

/**
 * One item's save body (§ 5.4) from what was tapped or typed: `{outcome}` for a button, `{value, isReset}` for a
 * reading's Save, with `remark` for an answer that needs one. The remark goes only with the answer it explains
 * (BR1-02): OK, Done, a check's NA and a reading's value send `remark: null`.
 */
export function resultBody(item, choice) {
  const needsRemark = choice.outcome && choice.outcome in REMARK_PROMPTS
    && (choice.outcome !== "na" || item.item_type === "reading");
  const remark = needsRemark ? choice.remark ?? "" : null;
  if (item.item_type === "reading" && !choice.outcome) {
    return { outcome: null, value: String(choice.value ?? "").trim(), remark: null, is_reset: Boolean(choice.isReset) };
  }
  return { outcome: choice.outcome, value: null, remark, is_reset: false };
}

/** A filled result as text on a read-only row: "OK", "48.5 °C", "212 °C"; "" when not filled. */
export function resultText(item) {
  if (item.outcome) return RESULT_LABELS[item.outcome] ?? item.outcome;
  if (item.value == null) return "";
  if (item.meter) return formatReading(item.value, item.meter.meter_type); // the house's grouping, as the Meters card
  return item.unit ? `${item.value} ${item.unit}` : item.value;
}

/** The unit beside a reading's input: the meter type's, else the item's own. */
export const readingUnit = (item) => item.meter?.meter_type?.unit ?? item.unit ?? "";

// ---------------------------------------------------------------------------
// Verify and send back (docs/steps/S099-pm-verify/1-brief.md § 5.7, § 5.8). Who may verify, and when, is the
// server's (pm_work_core.verify_error, can_verify, can_send_back).
// ---------------------------------------------------------------------------

/** A finished job's findings: "All OK", or "2 Not OK · 1 Not done · 1 out of limits" (a zero part left out). */
export function findingsText(findings) {
  if (!findings) return "";
  const parts = [findings.not_ok && `${findings.not_ok} Not OK`, findings.not_done && `${findings.not_done} Not done`,
    findings.out_of_limits && `${findings.out_of_limits} out of limits`].filter(Boolean);
  return parts.length ? parts.join(" · ") : "All OK";
}

/** "Verified by Arun, 28-10-2026 10:00", plus " · the person who did the work" when self-verified; "" without one. */
export function verifiedText(verification) {
  if (!verification) return "";
  const text = `Verified by ${verification.by_name}, ${formatDateTime(verification.at)}`;
  return verification.self_verified ? `${text} · ${SELF_VERIFIED_TEXT}` : text;
}

/** "Sent back by Arun, 28-10-2026 10:00: Re-tighten the left rod seal and check again."; "" without one. */
export function sentBackText(sentBack) {
  if (!sentBack) return "";
  return `Sent back by ${sentBack.by_name}, ${formatDateTime(sentBack.at)}: ${sentBack.remark}`;
}

/**
 * Why *Send back* is disabled on a job waiting for verification (the reason under the button), or "": the plan's
 * open job started, or the machine scrapped (pm_work_core.SCRAPPED_NO_SEND_BACK).
 */
export function sendBackBlockedText(job) {
  if (job.can_send_back || !job.can_verify) return "";
  if (job.equipment?.lifecycle === "scrapped") return "This machine is scrapped. The job cannot be sent back.";
  if (job.open_job?.state === "in_progress") {
    return `The plan's open job ${job.open_job.serial} has been started, so this job cannot be sent back.`;
  }
  return "";
}

// ---------------------------------------------------------------------------
// Reschedule and skip (docs/steps/S101-pm-reschedule-skip/1-brief.md § 5.7, § 5.8). Who may, and the bounds of a
// move, are the server's (pm_work_core.move_error, reschedule_override, can_reschedule, can_skip).
// ---------------------------------------------------------------------------

/**
 * The line under a moved job's due line, from the page's `reschedule` ({count, was_due_on, was_due_meter}):
 * "Moved from 08-11-2026.", "Moved from 10,040 h.", "Moved from 08-11-2026 or 10,040 h.", "Moved 2 times, first
 * from 08-11-2026."; "" without a move.
 */
export function movedFromText(reschedule, meterType) {
  if (!reschedule) return "";
  const date = reschedule.was_due_on ? formatDate(reschedule.was_due_on) : "";
  const meter = reschedule.was_due_meter != null && meterType ? dueValueText(reschedule.was_due_meter, meterType) : "";
  const from = [date, meter].filter(Boolean).join(" or ");
  if (reschedule.count === 1) return from ? `Moved from ${from}.` : "Moved.";
  return from ? `Moved ${reschedule.count} times, first from ${from}.` : `Moved ${reschedule.count} times.`;
}

/** "Skipped 05-11-2026 14:20 by Priya: Machine idle all month"; "" without a skip. */
export function jobSkippedText(skipped) {
  if (!skipped) return "";
  return `Skipped ${formatDateTime(skipped.at)} by ${skipped.by_name}: ${skipped.remark}`;
}
