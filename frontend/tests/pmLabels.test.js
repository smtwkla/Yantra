import { describe, expect, it } from "vitest";
import {
  STANDING_BADGES, STANDING_LABELS, assigneeText, blankItemForm, countText, daysPastText, dueText,
  itemBody, itemForm, jobsQuery, kindFromTicks, meterNowText, moveItem, newTemplateForm,
  nextDueText, personLabel, planSubline, refusedItemNumber, savedItemBody,
  filledText, jobBadges, limitFlag, notSavedText, recordedByText, resultBody, resultText,
  PM_TABS, findingsText, sendBackBlockedText, sentBackText, verifiedText,
  PM_EVENT_LABELS, jobSkippedText, movedFromText,
  lastDoneHint,
  READING_KINDS, deactivateQuestion, machinesText, meterUseText, planSettingsBody, planSettingsForm, planTitle,
  savedNoteText, scheduleChangeQuestion, scheduleChanged, templateBody, templateForm, templateRowText,
  templateSummary, usedOnText,
} from "../src/utils/pmLabels";

const OIL = { id: 7, name: "Oil temperature", unit: "°C", kind: "gauge", decimals: 1 };
const SAVED = {
  id: 4, position: 2, item_type: "reading", text: "Power-pack oil temperature", help_text: null, photo: "optional",
  reading_kind: "meter", unit: null, min_value: null, max_value: null, meter_type: OIL,
};

describe("kindFromTicks", () => {
  it("gives the trigger of the two ticks", () => {
    expect(kindFromTicks(true, true)).toBe("both");
    expect(kindFromTicks(true, false)).toBe("calendar");
    expect(kindFromTicks(false, true)).toBe("meter");
    expect(kindFromTicks(false, false)).toBeNull();
  });
});

describe("labels", () => {
  it("names a person with the role and the vendor", () => {
    expect(personLabel({ name: "Kannan", role: "maint_technician" })).toBe("Kannan (Technician)");
    expect(personLabel({ name: "Ravi", role: "maint_technician", vendor_name: "Atlas Copco" }))
      .toBe("Ravi (Technician) · Atlas Copco");
    expect(personLabel({ name: "Selvam", role: null })).toBe("Selvam");
  });
  it("gives the card's lines (S104)", () => {
    const plan = { item_count: 7, performer: "maintenance", assignee: { name: "Kannan", role: "maint_technician" },
      own: true, template: { name: "Press — monthly hydraulic check" }, equipment: { code: "MOT014" } };
    expect(planSubline(plan)).toBe("7 items · Kannan (Technician)");
    expect(planSubline({ ...plan, assignee: null, item_count: 1 })).toBe("1 item · No one yet");
    expect(planSubline({ ...plan, performer: "operator" })).toBe("7 items · Operator");
    expect(planTitle(plan)).toBe("Press — monthly hydraulic check");
    expect(planTitle({ ...plan, own: false })).toBe("MOT014 · Press — monthly hydraulic check");
  });
  it("reads the item number of an items refusal", () => {
    expect(refusedItemNumber("Item 3: Enter what to do or check.")).toBe(3);
    expect(refusedItemNumber("Item 12 appears twice. Reload the page.")).toBe(12);
    expect(refusedItemNumber("Add at least one item.")).toBeNull();
  });
  it("words a template (S104)", () => {
    const template = { trigger_text: "Every month or 250 h, whichever comes first", item_count: 7, plan_count: 3,
      performer: "maintenance", needs_verification: true };
    expect(templateRowText(template)).toBe("Every month or 250 h, whichever comes first · 7 items · 3 machines");
    expect(templateRowText({ ...template, item_count: 1, plan_count: 1 })).toContain("1 item · 1 machine");
    expect(templateSummary(template)).toBe("7 items · Maintenance · an engineer verifies");
    expect(usedOnText(3)).toBe("Used on 3 machines");
    expect(usedOnText(1)).toBe("Used on 1 machine");
    expect(usedOnText(0)).toBe("Not used on any machine yet");
    expect(scheduleChangeQuestion(4)).toBe(
      "Change the schedule for 4 machines? Their jobs move to the new interval. Jobs already started are not changed.");
  });
  it("words the template page's counts by the number of machines (CR1-09)", () => {
    expect(machinesText(1)).toBe("1 machine");
    expect(machinesText(3)).toBe("3 machines");
    expect(savedNoteText(0)).toBe("Saved.");
    expect(savedNoteText(1)).toBe("Saved. 1 machine will update at the next daily run.");
    expect(savedNoteText(2)).toBe("Saved. 2 machines will update at the next daily run.");
    expect(deactivateQuestion(0)).toBe("Deactivate this template? No machine uses it yet.");
    expect(deactivateQuestion(1)).toBe(
      "Deactivate this template? Its 1 machine stops getting jobs. Jobs already started can be finished.");
    expect(deactivateQuestion(3)).toBe(
      "Deactivate this template? Its 3 machines stop getting jobs. Jobs already started can be finished.");
  });
  it("names the meters a plan uses (S104 A1: a linked meter)", () => {
    const hours = { id: 3, name: "Run hours" };
    expect(meterUseText({ meter_type: hours, equipment: { code: "HP003" }, from_link: false }))
      .toBe("HP003's own Run hours");
    expect(meterUseText({ meter_type: hours, equipment: { code: "PR-07" }, from_link: true }))
      .toBe("PR-07's Run hours (linked meter)");
    expect(meterUseText({ meter_type: hours, equipment: null, from_link: false })).toBeNull();
  });
});

describe("itemBody (S104: the two reading kinds)", () => {
  it("sends a check with the reading fields cleared", () => {
    const form = { ...blankItemForm(), text: "No leaks", unit: "mm", min_value: "1", meter_type_id: 7,
      reading_kind: "meter" };
    expect(itemBody(form)).toEqual({
      id: null, item_type: "check", text: "No leaks", help_text: null, photo: "optional", reading_kind: null,
      unit: null, min_value: null, max_value: null, meter_type_id: null,
    });
  });
  it("sends a meter reading's type, and no unit, limits or tick (S104 A1)", () => {
    const form = { ...itemForm(SAVED), unit: "°C", min_value: "30" };
    expect(itemBody(form)).toMatchObject({ id: 4, reading_kind: "meter", unit: null, min_value: null,
      meter_type_id: 7 });
    expect("meter_from_parent" in itemBody(form)).toBe(false);
    expect("meter_from_parent" in blankItemForm()).toBe(false);
  });
  it("sends a measurement's unit and limits, and no meter type", () => {
    const form = { ...blankItemForm(), item_type: "reading", reading_kind: "measurement", text: "Gap", unit: " mm ",
      min_value: "", max_value: "2", meter_type_id: 7 };
    expect(itemBody(form)).toMatchObject({ unit: "mm", min_value: null, max_value: "2", meter_type_id: null });
  });
  it("sends a reading without its kind as null, for the API's own words", () => {
    expect(itemBody({ ...blankItemForm(), item_type: "reading" }).reading_kind).toBeNull();
  });
  it("names the two kinds", () => {
    expect(READING_KINDS.map((k) => k.label)).toEqual(["Measurement", "Meter reading"]);
  });
});

describe("savedItemBody", () => {
  it("turns the API's item back into a body", () => {
    expect(savedItemBody(SAVED)).toEqual({
      id: 4, item_type: "reading", text: "Power-pack oil temperature", help_text: null, photo: "optional",
      reading_kind: "meter", unit: null, min_value: null, max_value: null, meter_type_id: 7,
    });
  });
});

describe("templateBody", () => {
  it("sends null for an unticked trigger and keeps its typed values in the form", () => {
    const form = { ...newTemplateForm(), name: "Monthly check", calendarOn: true, meter_type_id: 5,
      meter_every: "250" };
    const body = templateBody(form, [SAVED]);
    expect(body).toMatchObject({ trigger_kind: "calendar", calendar_every: 1, calendar_unit: "month",
      meter_type_id: null, meter_every: null });
    expect(body.items).toEqual([savedItemBody(SAVED)]);
    expect(form.meter_every).toBe("250");
  });
  it("sends both triggers with the meter type, and no parent tick (S104 A1)", () => {
    const form = { ...newTemplateForm(), calendarOn: true, meterOn: true, meter_type_id: "5", meter_every: "250" };
    const body = templateBody(form, []);
    expect(body).toMatchObject({ trigger_kind: "both", meter_type_id: 5, meter_every: "250" });
    expect("meter_from_parent" in body).toBe(false);
    expect("meter_from_parent" in newTemplateForm()).toBe(false);
  });
  it("sends no trigger with neither tick, and a typed non-number as it is", () => {
    expect(templateBody({ ...newTemplateForm(), calendarOn: true, calendar_every: "3x" }, []).calendar_every)
      .toBe("3x");
    expect(templateBody(newTemplateForm(), []).trigger_kind).toBeNull();
  });
  it("fills the form from a template, and knows a schedule change", () => {
    const template = { name: "T", performer: "maintenance", needs_verification: true, trigger_kind: "both",
      calendar_every: 1, calendar_unit: "month", meter_type: { id: 5 }, meter_every: "250" };
    const form = templateForm(template);
    expect(form).toMatchObject({ calendarOn: true, calendar_every: "1", meterOn: true, meter_type_id: 5,
      meter_every: "250" });
    expect(scheduleChanged(template, templateBody({ ...form, name: "New name" }, []))).toBe(false);
    expect(scheduleChanged(template, templateBody({ ...form, calendar_every: "2" }, []))).toBe(true);
    expect(scheduleChanged(template, templateBody({ ...form, meter_every: "300" }, []))).toBe(true);
    expect(scheduleChanged(null, templateBody(form, []))).toBe(false);
  });
});

describe("the plan settings (S104 § 5.5)", () => {
  const plan = { assignee: { id: 3 }, last_done_on: "2026-10-02", last_done_meter: "1840",
    template: { performer: "maintenance", meter_type: { id: 5 } } };
  it("sends the assignee, the date and a changed meter value", () => {
    const form = { ...planSettingsForm(plan), last_done_meter: "1900" };
    expect(planSettingsBody(form, plan)).toEqual({ assignee_id: 3, last_done_on: "2026-10-02",
      last_done_meter: "1900" });
  });
  it("sends no assignee on an operator template, and no meter value without a meter trigger", () => {
    const calendar = { ...plan, template: { performer: "operator", meter_type: null } };
    expect(planSettingsBody(planSettingsForm(calendar), calendar)).toEqual({ assignee_id: null,
      last_done_on: "2026-10-02" });
  });
  it("sends an empty date as null", () => {
    expect(planSettingsBody({ ...planSettingsForm(plan), last_done_on: "" }, plan).last_done_on).toBeNull();
  });
  // S104 A1.6.3: the API answers a stored meter value only while the plan uses its meter (else null, hidden); the
  // page sends the value only when it differs from what it loaded, so an assignee save never touches a hidden one
  const hidden = { ...plan, last_done_meter: null };
  it("leaves an unchanged meter value out of the save", () => {
    const body = planSettingsBody({ ...planSettingsForm(plan), assignee_id: 4 }, plan);
    expect(body).toEqual({ assignee_id: 4, last_done_on: "2026-10-02" });
    expect(planSettingsForm(hidden).last_done_meter).toBe("");
    expect("last_done_meter" in planSettingsBody({ ...planSettingsForm(hidden), assignee_id: 4 }, hidden)).toBe(false);
  });
  it("sends a typed meter value, and null for an emptied one", () => {
    expect(planSettingsBody({ ...planSettingsForm(hidden), last_done_meter: "1000" }, hidden).last_done_meter)
      .toBe("1000");
    expect(planSettingsBody({ ...planSettingsForm(plan), last_done_meter: " " }, plan).last_done_meter).toBeNull();
  });
  it("gives the plain hint, with no old-meter note (S104 A1)", () => {
    expect(lastDoneHint(plan)).toBe("When was this work last done on this machine, before Yantra? "
      + "Leave it empty if you do not know.");
    expect(lastDoneHint({ ...hidden, seed_note: "anything" })).toBe(lastDoneHint(plan));
  });
});

describe("moveItem", () => {
  it("moves an item up or down and nowhere past the ends", () => {
    expect(moveItem(["a", "b", "c"], 1, -1)).toEqual(["b", "a", "c"]);
    expect(moveItem(["a", "b", "c"], 1, 1)).toEqual(["a", "c", "b"]);
    const items = ["a", "b"];
    expect(moveItem(items, 0, -1)).toBe(items);
    expect(moveItem(items, 1, 1)).toBe(items);
  });
});

// S097: the PM list and the card's job line
const HOURS = { id: 3, name: "Run hours", unit: "h", kind: "counter", decimals: 1 };

describe("the standing", () => {
  it("names and colours each of the four states", () => {
    expect(STANDING_LABELS).toEqual({ overdue: "Overdue", due: "Due", upcoming: "Upcoming", not_yet: "Not yet due" });
    expect(STANDING_BADGES.overdue).toBe("text-bg-danger");
    expect(STANDING_BADGES.not_yet).toBe("text-bg-light border");
  });
});

describe("dueText and daysPastText", () => {
  it("gives the date, the meter value or both", () => {
    expect(dueText("2026-10-24", null, null)).toBe("24-10-2026");
    expect(dueText(null, "5000", HOURS)).toBe("at 5,000 h");
    expect(dueText("2026-10-24", "3250", HOURS)).toBe("24-10-2026 or at 3,250 h");
    expect(dueText(null, null, HOURS)).toBe("");
  });
  it("counts the days past the due date", () => {
    expect(daysPastText(1)).toBe(" · 1 day ago");
    expect(daysPastText(3)).toBe(" · 3 days ago");
    expect(daysPastText(null)).toBe("");
  });
});

describe("meterNowText", () => {
  it("gives the meter now, across a reset, or no reading", () => {
    const meter = { meter_type: HOURS, value_now: "5006.5", value_counted: "5006.5", offset: "0" };
    expect(meterNowText(meter)).toBe("Run hours now 5,006.5 h");
    expect(meterNowText({ ...meter, value_now: "120", value_counted: "5120", offset: "5000" }))
      .toBe("Run hours now 120.0 h · 5,120.0 h counted across a reset");
    expect(meterNowText({ ...meter, value_now: null, value_counted: null })).toBe("Run hours: no reading yet");
    expect(meterNowText(null)).toBe("");
  });
});

describe("assigneeText", () => {
  it("names the assignee, nobody, or the operator", () => {
    expect(assigneeText({ plan: { performer: "maintenance" }, assignee: { id: 4, name: "Kannan" } })).toBe("Kannan");
    expect(assigneeText({ plan: { performer: "maintenance" }, assignee: null })).toBe("No one yet");
    expect(assigneeText({ plan: { performer: "operator" }, assignee: null })).toBe("Operator");
  });
});

describe("nextDueText", () => {
  const meter = { meter_type: HOURS };
  it("gives the next due point", () => {
    expect(nextDueText({ due_on: "2026-12-02", due_meter: "3250", no_reading: false }, meter))
      .toBe("Next due 02-12-2026 or at 3,250 h");
    expect(nextDueText({ due_on: "2026-12-02", due_meter: null, no_reading: false }, null)).toBe("Next due 02-12-2026");
  });
  it("says when the meter has no base yet", () => {
    expect(nextDueText({ due_on: "2026-12-02", due_meter: null, no_reading: true }, meter))
      .toBe("Next due 02-12-2026 · Run hours: no reading yet");
    expect(nextDueText({ due_on: null, due_meter: null, no_reading: true }, meter))
      .toBe("Next due when Run hours has a reading");
  });
});

describe("countText", () => {
  it("adds up to the tab's rows, a zero part left out", () => {
    expect(countText("due", { due: 4, overdue: 1, upcoming: 3 })).toBe("4 due · 1 overdue");
    expect(countText("due", { due: 0, overdue: 2, upcoming: 3 })).toBe("2 overdue");
    expect(countText("due", { due: 0, overdue: 0, upcoming: 3 })).toBe("");
    expect(countText("upcoming", { due: 4, overdue: 1, upcoming: 3 })).toBe("3 upcoming");
    expect(countText("upcoming", { due: 4, overdue: 1, upcoming: 0 })).toBe("");
  });
});

describe("jobsQuery", () => {
  it("sends only what is set; Due is the default tab", () => {
    expect(jobsQuery({})).toBe("");
    expect(jobsQuery({ tab: "upcoming", unit_id: "5", assigned: "me" })).toBe("tab=upcoming&unit_id=5&assigned=me");
    expect(jobsQuery({ tab: "due", assigned: "x" })).toBe("");
  });
});

// ---------------------------------------------------------------------------
// S098: doing a PM job
// ---------------------------------------------------------------------------

describe("countText, S098", () => {
  it("adds the started jobs on Due and the total on Done", () => {
    expect(countText("due", { due: 4, overdue: 1, upcoming: 0, in_progress: 2 })).toBe("4 due · 1 overdue · 2 in progress");
    expect(countText("due", { due: 0, overdue: 0, upcoming: 0, in_progress: 1 })).toBe("1 in progress");
    expect(countText("done", { due: 4, overdue: 1, upcoming: 0, in_progress: 0 }, 12)).toBe("12 done");
    expect(countText("done", { due: 0, overdue: 0, upcoming: 0, in_progress: 0 }, 0)).toBe("");
  });
});

describe("jobsQuery, S098", () => {
  it("takes the Done tab and its page", () => {
    expect(jobsQuery({ tab: "done", page: "3" })).toBe("tab=done&page=3");
    expect(jobsQuery({ tab: "done", page: "1" })).toBe("tab=done");
    expect(jobsQuery({ tab: "due", page: "3" })).toBe("");
  });
});

describe("limitFlag", () => {
  it("flags a typed value outside the item's limits", () => {
    expect(limitFlag("212", null, "200")).toBe("high");
    expect(limitFlag("29.9", "30", "60")).toBe("low");
    expect(limitFlag("", "30", "60")).toBeNull();
    expect(limitFlag("abc", "30", "60")).toBeNull();
    expect(limitFlag("45", null, null)).toBeNull();
    expect(limitFlag("60", "30", "60")).toBeNull();
    expect(limitFlag("30", "30", "60")).toBeNull();
  });
});

describe("filledText and notSavedText", () => {
  it("say how far the job is and what failed", () => {
    expect(filledText(3, 7)).toBe("3 of 7 filled");
    expect(notSavedText("No connection. Check Wi-Fi or mobile data and try again.")).toBe(
      "Not saved. No connection. Check Wi-Fi or mobile data and try again.");
  });
});

describe("jobBadges", () => {
  const standing = { state: "overdue" };
  it("gives the badges of each state", () => {
    expect(jobBadges({ state: "in_progress", standing }).map((b) => b.label)).toEqual(["In progress", "Overdue"]);
    expect(jobBadges({ state: "done", standing: null, timeliness: "on_time" })).toEqual([
      { label: "Done", badge: "text-bg-success" }, { label: "On time", badge: "text-bg-light border" }]);
    expect(jobBadges({ state: "done", standing: null, timeliness: "late" })).toEqual([
      { label: "Done", badge: "text-bg-success" }, { label: "Late", badge: "text-bg-danger" }]);
    expect(jobBadges({ state: "due", standing })).toEqual([{ label: "Overdue", badge: "text-bg-danger" }]);
    expect(jobBadges({ state: "cancelled", standing: null }).map((b) => b.label)).toEqual(["Cancelled"]);
  });
});

describe("resultBody", () => {
  const check = { item_type: "check" };
  const task = { item_type: "task" };
  const reading = { item_type: "reading" };
  it("sends the remark only with the answer it explains (BR1-02)", () => {
    expect(resultBody(check, { outcome: "ok", remark: "old" })).toEqual(
      { outcome: "ok", value: null, remark: null, is_reset: false });
    expect(resultBody(check, { outcome: "na", remark: "x" })).toEqual(
      { outcome: "na", value: null, remark: null, is_reset: false });
    expect(resultBody(check, { outcome: "not_ok", remark: "Oil seeping" })).toEqual(
      { outcome: "not_ok", value: null, remark: "Oil seeping", is_reset: false });
    expect(resultBody(task, { outcome: "not_done", remark: "No grease" })).toEqual(
      { outcome: "not_done", value: null, remark: "No grease", is_reset: false });
    expect(resultBody(task, { outcome: "done" }).remark).toBeNull();
  });
  it("sends a reading's value, or its NA with the remark", () => {
    expect(resultBody(reading, { value: " 48.5 ", isReset: false })).toEqual(
      { outcome: null, value: "48.5", remark: null, is_reset: false });
    expect(resultBody(reading, { value: "1200", isReset: true }).is_reset).toBe(true);
    expect(resultBody(reading, { outcome: "na", remark: "Gauge broken" })).toEqual(
      { outcome: "na", value: null, remark: "Gauge broken", is_reset: false });
  });
});

describe("resultText and recordedByText", () => {
  it("words a result and who recorded a line", () => {
    expect(resultText({ outcome: "not_ok" })).toBe("Not OK");
    expect(resultText({ outcome: null, value: "48.5", unit: "°C", meter: null })).toBe("48.5 °C");
    expect(resultText({ outcome: null, value: "1270", unit: null, meter: { meter_type: { unit: "h", kind: "counter", decimals: 0 } } }))
      .toBe("1,270 h");
    expect(resultText({ outcome: null, value: null })).toBe("");
    expect(recordedByText({ created_by_name: "pm_generate" })).toBe("by the daily PM run");
    expect(recordedByText({ created_by_name: "Priya" })).toBe("by Priya");
  });
});

// ---------------------------------------------------------------------------
// S099: verify and send back
// ---------------------------------------------------------------------------

describe("the To verify tab, S099", () => {
  it("sits between Upcoming and Done, with its page and its count line", () => {
    expect(PM_TABS).toEqual(["due", "upcoming", "to_verify", "done"]);
    expect(jobsQuery({ tab: "to_verify", page: "2", assigned: "me" })).toBe("tab=to_verify&assigned=me&page=2");
    expect(jobsQuery({ tab: "to_verify", page: "1" })).toBe("tab=to_verify");
    expect(countText("to_verify", { due: 1, overdue: 0, upcoming: 0, in_progress: 0, to_verify: 3 }, 3))
      .toBe("3 to verify");
    expect(countText("to_verify", { due: 0, overdue: 0, upcoming: 0, in_progress: 0, to_verify: 0 }, 0)).toBe("");
  });
});

describe("findingsText, verifiedText, sentBackText", () => {
  it("say what the job found, who verified it and why it came back", () => {
    expect(findingsText({ not_ok: 0, not_done: 0, out_of_limits: 0 })).toBe("All OK");
    expect(findingsText({ not_ok: 2, not_done: 1, out_of_limits: 0 })).toBe("2 Not OK · 1 Not done");
    expect(findingsText({ not_ok: 0, not_done: 0, out_of_limits: 1 })).toBe("1 out of limits");
    expect(findingsText(null)).toBe("");
    const at = "2026-10-28T10:00:00+05:30";
    expect(verifiedText({ by_name: "Arun", at, self_verified: false })).toBe("Verified by Arun, 28-10-2026 10:00");
    expect(verifiedText({ by_name: "Arun", at, self_verified: true })).toBe(
      "Verified by Arun, 28-10-2026 10:00 · the person who did the work");
    expect(verifiedText(null)).toBe("");
    expect(sentBackText({ by_name: "Arun", at, remark: "Re-tighten the left rod seal and check again." })).toBe(
      "Sent back by Arun, 28-10-2026 10:00: Re-tighten the left rod seal and check again.");
    expect(sentBackText(null)).toBe("");
  });

  it("says why Send back is off", () => {
    const waiting = { can_verify: true, can_send_back: false, equipment: { lifecycle: "in_service" } };
    expect(sendBackBlockedText({ ...waiting, open_job: { serial: "PM-2026-11-004", state: "in_progress" } })).toBe(
      "The plan's open job PM-2026-11-004 has been started, so this job cannot be sent back.");
    expect(sendBackBlockedText({ ...waiting, equipment: { lifecycle: "scrapped" }, open_job: null })).toBe(
      "This machine is scrapped. The job cannot be sent back.");
    expect(sendBackBlockedText({ ...waiting, can_send_back: true })).toBe("");
    expect(sendBackBlockedText({ ...waiting, can_verify: false })).toBe("");
  });
});

describe("jobBadges, S099", () => {
  it("gives To verify, Verified and Sent back", () => {
    expect(jobBadges({ state: "done", awaits_verification: true, timeliness: "on_time" }).map((b) => b.label))
      .toEqual(["To verify", "On time"]);
    expect(jobBadges({ state: "done", awaits_verification: true, timeliness: null })[0]).toEqual(
      { label: "To verify", badge: "text-bg-warning" });
    expect(jobBadges({ state: "verified", awaits_verification: false, timeliness: "late" })).toEqual([
      { label: "Verified", badge: "text-bg-success" }, { label: "Late", badge: "text-bg-danger" }]);
    expect(jobBadges({ state: "done", awaits_verification: false, timeliness: null }).map((b) => b.label))
      .toEqual(["Done"]);
    expect(jobBadges({ state: "in_progress", standing: { state: "overdue" }, sent_back: { remark: "x" } }))
      .toEqual([{ label: "In progress", badge: "text-bg-primary" }, { label: "Sent back", badge: "text-bg-danger" },
        { label: "Overdue", badge: "text-bg-danger" }]);
  });
});

// S101: reschedule and skip
describe("jobBadges, S101", () => {
  const rescheduled = { label: "Rescheduled", badge: "text-bg-light border" };
  it("gives Rescheduled after the other badges of a due or started job", () => {
    expect(jobBadges({ state: "due", standing: { state: "not_yet" }, rescheduled: true })).toEqual([
      { label: "Not yet due", badge: "text-bg-light border" }, rescheduled]);
    expect(jobBadges({ state: "in_progress", standing: { state: "due" }, rescheduled: true }).map((b) => b.label))
      .toEqual(["In progress", "Due", "Rescheduled"]);
    expect(jobBadges({ state: "done", timeliness: "on_time", rescheduled: true }).map((b) => b.label))
      .toEqual(["Done", "On time"]);
  });
  it("gives Skipped to a skipped job, and Cancelled to a cancelled one only", () => {
    expect(jobBadges({ state: "skipped", standing: null, rescheduled: true })).toEqual([
      { label: "Skipped", badge: "text-bg-secondary" }]);
    expect(jobBadges({ state: "cancelled", standing: null })).toEqual([
      { label: "Cancelled", badge: "text-bg-secondary" }]);
  });
  it("names the two new history lines", () => {
    expect([PM_EVENT_LABELS.rescheduled, PM_EVENT_LABELS.skipped]).toEqual(["Rescheduled", "Skipped"]);
  });
});

describe("countText, S101", () => {
  const counts = { due: 0, overdue: 0, upcoming: 0, in_progress: 0 };
  it("says the done and the skipped jobs apart, a zero part left out", () => {
    expect(countText("done", counts, 12, 2)).toBe("10 done · 2 skipped");
    expect(countText("done", counts, 2, 2)).toBe("2 skipped");
    expect(countText("done", counts, 10, 0)).toBe("10 done");
    expect(countText("done", counts, 10)).toBe("10 done");
    expect(countText("to_verify", counts, 3, 2)).toBe("3 to verify");
  });
});

describe("movedFromText", () => {
  it("says where the job was moved from", () => {
    expect(movedFromText({ count: 1, was_due_on: "2026-11-08", was_due_meter: null }, null))
      .toBe("Moved from 08-11-2026.");
    expect(movedFromText({ count: 1, was_due_on: null, was_due_meter: "10040" }, HOURS)).toBe("Moved from 10,040 h.");
    expect(movedFromText({ count: 1, was_due_on: "2026-11-08", was_due_meter: "10040" }, HOURS))
      .toBe("Moved from 08-11-2026 or 10,040 h.");
    expect(movedFromText({ count: 2, was_due_on: "2026-11-08", was_due_meter: null }, null))
      .toBe("Moved 2 times, first from 08-11-2026.");
  });
  it("says only the move when the old due point is not known, and nothing without a move", () => {
    expect(movedFromText({ count: 1, was_due_on: null, was_due_meter: null }, null)).toBe("Moved.");
    expect(movedFromText({ count: 3, was_due_on: null, was_due_meter: null }, null)).toBe("Moved 3 times.");
    expect(movedFromText(null, null)).toBe("");
  });
});

describe("jobSkippedText", () => {
  it("says when, who and why", () => {
    expect(jobSkippedText({ at: "2026-11-05T14:20:00", by_name: "Priya", remark: "Machine idle all month" }))
      .toBe("Skipped 05-11-2026 14:20 by Priya: Machine idle all month");
    expect(jobSkippedText(null)).toBe("");
  });
});
