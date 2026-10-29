import { describe, expect, it } from "vitest";
import {
  ACTION_KINDS, actionCountsText, actionKindLabel, causeText, closedLine, defaultDueDate, eventLabel, figureRows,
  IMPROVEMENT_EVENT_LABELS, improvementStateBadgeClass, repeatText, machinesText, symptomsText, watchEndDate, watchLine, defaultProblem, defaultRootCause, defaultTitle,
  IMPROVEMENT_STATE_LABELS, improvementStateLabel, lossText, overdueText, PROBLEM_MAX, ROOT_CAUSE_MAX,
  ticketCauses, TITLE_MAX, whyBody,
} from "../src/utils/improvementLabels";

const ticket = (extra = {}) => ({ machine: { code: "HP003" }, failure_mode: null, description: "", ...extra });

describe("improvementStateLabel", () => {
  it("names a known state", () => expect(improvementStateLabel("analysing")).toBe("Analysing"));
  it("names the seven states in plain words (S072 D13)", () => {
    expect(Object.fromEntries(Object.keys(IMPROVEMENT_STATE_LABELS).map((s) => [s, improvementStateLabel(s)]))).toEqual({
      analysing: "Analysing",
      actions_open: "Actions open",
      watching: "Watching",
      ready_to_verify: "Ready to verify",
      closed_effective: "Closed: it worked",
      closed_not_effective: "Closed: did not work",
      dropped: "Dropped",
    });
  });
  it("shows an unknown state as it came", () => expect(improvementStateLabel("verifying")).toBe("verifying"));
});

describe("lossText", () => {
  it("reads one ticket", () => {
    expect(lossText({ tickets: 1, breakdowns: 1, downtime_minutes: 145 })).toBe("1 ticket, 1 breakdown · down 2 h 25 min");
  });
  it("reads several tickets, in days from 24 h", () => {
    expect(lossText({ tickets: 2, breakdowns: 1, downtime_minutes: 31 * 60 })).toBe("2 tickets, 1 breakdown · down 1 d 7 h");
  });
  it("says no downtime for 0", () => {
    expect(lossText({ tickets: 1, breakdowns: 0, downtime_minutes: 0 })).toBe("1 ticket, 0 breakdowns · no downtime");
  });
});

describe("defaultTitle", () => {
  it("joins the machine and the symptom", () => {
    expect(defaultTitle(ticket({ failure_mode: { label: "Won't start" } }))).toBe("HP003: Won't start");
  });
  it("uses the first line of the description without a symptom", () => {
    expect(defaultTitle(ticket({ description: "Oil seeping\nfrom the seal" }))).toBe("HP003: Oil seeping");
  });
  it("cuts a long description at 120 characters", () => {
    const title = defaultTitle(ticket({ description: "x".repeat(300) }));
    expect(title).toHaveLength(TITLE_MAX);
    expect(title.startsWith("HP003: xxx")).toBe(true);
  });
  it("is the machine code alone with neither", () => expect(defaultTitle(ticket())).toBe("HP003"));
});

describe("defaultProblem", () => {
  it("is the description", () => {
    expect(defaultProblem(ticket({ description: "Motor trips", failure_mode: { label: "Won't start" } }))).toBe("Motor trips");
  });
  it("is the symptom when there is no description", () => {
    expect(defaultProblem(ticket({ failure_mode: { label: "Won't start" } }))).toBe("Won't start");
  });
  it("is empty with neither", () => expect(defaultProblem(ticket())).toBe(""));
  it("cuts at 2000 characters", () => expect(defaultProblem(ticket({ description: "y".repeat(2500) }))).toHaveLength(PROBLEM_MAX));
});

// S069: the why-why chain and the root cause
const cause = (id, code, label) => ({ id, code, label });

describe("causeText", () => {
  it("reads code and label", () => expect(causeText(cause(1, "4.2", "Management error"))).toBe("4.2 Management error"));
});

describe("ticketCauses", () => {
  it("lists each cause once, in code order", () => {
    const tickets = [
      { cause: cause(9, "4.2", "Management error") },
      { cause: cause(3, "3.4", "Expected wear and tear") },
      { cause: cause(9, "4.2", "Management error") },
      { cause: cause(5, "3.10", "Other") },
    ];
    expect(ticketCauses(tickets).map((c) => c.code)).toEqual(["3.4", "3.10", "4.2"]);
  });
  it("skips a ticket with no cause yet", () => {
    expect(ticketCauses([{ cause: null }, { cause: cause(3, "3.4", "Wear") }]).map((c) => c.id)).toEqual([3]);
    expect(ticketCauses([{ cause: null }])).toEqual([]);
  });
});

describe("defaultRootCause", () => {
  it("is the last why's answer", () => {
    expect(defaultRootCause([{ answer: "Dust" }, { answer: "The presses have no PM plan" }])).toBe("The presses have no PM plan");
  });
  it("is empty with no whys", () => expect(defaultRootCause([])).toBe(""));
  it("cuts at 500 characters", () => expect(defaultRootCause([{ answer: "z".repeat(900) }])).toHaveLength(ROOT_CAUSE_MAX));
});

describe("whyBody", () => {
  const form = { question: "Why?", answer: "Because", evidence: "  ", position: 3 };
  it("sends no position when adding", () => {
    expect(whyBody(form, false, null)).toEqual({ question: "Why?", answer: "Because", evidence: null });
  });
  it("sends no position on an edit when the place was not changed (CR1-01)", () => {
    expect(whyBody(form, true, 3)).not.toHaveProperty("position");
  });
  it("sends the place on an edit when the user changed it", () => {
    expect(whyBody({ ...form, position: "1" }, true, 3)).toMatchObject({ position: 1 });
  });
  it("keeps the evidence text when it is not blank", () => {
    expect(whyBody({ ...form, evidence: "photo" }, true, 3).evidence).toBe("photo");
  });
});

// S071: countermeasures
describe("ACTION_KINDS", () => {
  it("holds the six kinds with S070's sentences, word for word", () => {
    expect(ACTION_KINDS.map((k) => [k.key, k.label, k.sentence])).toEqual([
      ["correction", "Correction", "Fixes this failure now, often already done on the ticket."],
      ["corrective", "Corrective", "Removes the cause here, so this failure does not come back."],
      ["preventive", "Preventive", "Adds regular work that stops the failure before it happens."],
      ["design_out", "Design-out", "Changes the machine so this failure cannot happen."],
      ["lesson", "Lesson", "Teaches the team what was learned."],
      ["spread", "Spread", "Applies the fix to the similar machines."],
    ]);
  });
});

describe("actionKindLabel", () => {
  it("names a kind", () => expect(actionKindLabel("design_out")).toBe("Design-out"));
  it("returns an unknown key as it is", () => expect(actionKindLabel("audit")).toBe("audit"));
});

describe("overdueText", () => {
  it("reads 1 day", () => expect(overdueText(1)).toBe("Overdue 1 day"));
  it("reads 2 days", () => expect(overdueText(2)).toBe("Overdue 2 days"));
  it("is empty for 0", () => expect(overdueText(0)).toBe(""));
});

describe("actionCountsText", () => {
  it("is empty with none", () => expect(actionCountsText({ open: 0, done: 0, cancelled: 0, overdue: 0 })).toBe(""));
  it("reads done of all", () => expect(actionCountsText({ open: 4, done: 2, cancelled: 0, overdue: 1 })).toBe("2 of 6 done"));
  it("leaves cancelled ones out of both numbers", () => {
    expect(actionCountsText({ open: 0, done: 0, cancelled: 2, overdue: 0 })).toBe("");
    expect(actionCountsText({ open: 1, done: 0, cancelled: 1, overdue: 0 })).toBe("0 of 1 done");
  });
});

describe("defaultDueDate", () => {
  it("is 14 days ahead", () => expect(defaultDueDate(new Date(2026, 9, 30, 10, 0))).toBe("2026-11-13"));
  it("crosses a month end", () => expect(defaultDueDate(new Date(2026, 0, 25))).toBe("2026-02-08"));
  it("is empty without a date", () => expect(defaultDueDate(undefined)).toBe(""));
});

describe("eventLabel", () => {
  it("names every event of the timeline", () => {
    expect(Object.keys(IMPROVEMENT_EVENT_LABELS)).toHaveLength(19);
    expect(eventLabel("started")).toBe("Started");
    expect(eventLabel("edited")).toBe("Changed");
    expect(eventLabel("ticket_linked")).toBe("Ticket added");
    expect(eventLabel("ticket_removed")).toBe("Ticket removed");
    expect(eventLabel("why_added")).toBe("Why added");
    expect(eventLabel("why_changed")).toBe("Why changed");
    expect(eventLabel("why_removed")).toBe("Why removed");
    expect(eventLabel("root_cause_set")).toBe("Root cause set");
    expect(eventLabel("root_cause_changed")).toBe("Root cause changed");
    expect(eventLabel("action_added")).toBe("Countermeasure added");
    expect(eventLabel("action_changed")).toBe("Countermeasure changed");
    expect(eventLabel("action_done")).toBe("Countermeasure done");
    expect(eventLabel("action_cancelled")).toBe("Countermeasure cancelled");
    expect(eventLabel("state_changed")).toBe("State changed");
    expect(eventLabel("note")).toBe("Note");
    expect(eventLabel("closed_effective")).toBe("Closed: it worked");
    expect(eventLabel("closed_not_effective")).toBe("Closed: did not work");
    expect(eventLabel("dropped")).toBe("Dropped");
    expect(eventLabel("watch_ended")).toBe("Watch ended — ready to verify");
  });
  it("shows an unknown event as it came", () => expect(eventLabel("audited")).toBe("audited"));
});

describe("improvementStateBadgeClass", () => {
  it("colours the closing states and keeps the open ones plain", () => {
    expect(improvementStateBadgeClass("ready_to_verify")).toBe("text-bg-warning");
    expect(improvementStateBadgeClass("closed_effective")).toBe("text-bg-success");
    expect(improvementStateBadgeClass("closed_not_effective")).toBe("text-bg-danger");
    expect(improvementStateBadgeClass("dropped")).toBe("text-bg-secondary");
    expect(improvementStateBadgeClass("watching")).toBe("text-bg-light border");
  });
});

describe("watchLine", () => {
  const watch = { days: 90, from: "2026-11-20T15:30:00+05:30", until: "2027-02-18T15:30:00+05:30" };
  it("says how long the watch will be before it starts", () => {
    expect(watchLine({ state: "actions_open", watch: { days: 90, from: null, until: null } }))
      .toBe("Watch: 90 days after the last countermeasure is done");
    expect(watchLine({ state: "analysing", watch: { days: 120, from: null, until: null } }))
      .toBe("Watch: 120 days after the last countermeasure is done");
  });
  it("gives the dates while watching", () => {
    expect(watchLine({ state: "watching", watch })).toBe("Watching since 20-11-2026 · until 18-02-2027");
  });
  it("says ready to verify when the watch has ended", () => {
    expect(watchLine({ state: "ready_to_verify", watch })).toBe("Watched 90 days, until 18-02-2027 · ready to verify");
  });
  it("gives no line for a closed state (closedLine does)", () => {
    expect(watchLine({ state: "closed_effective", watch })).toBe("");
  });
});

describe("closedLine", () => {
  const closed = (extra = {}) => ({ at: "2027-02-18T15:30:00+05:30", by_name: "Arun (manager)", by_lead: false, remark: null, ...extra });
  it("reads each closed state", () => {
    expect(closedLine(closed(), "closed_effective")).toBe("Closed 18-02-2027 by Arun (manager): it worked");
    expect(closedLine(closed(), "closed_not_effective")).toBe("Closed 18-02-2027 by Arun (manager): did not work");
    expect(closedLine(closed(), "dropped")).toBe("Dropped 18-02-2027 by Arun (manager)");
  });
  it("marks the lead who closed their own improvement", () => {
    expect(closedLine(closed({ by_name: "Priya (engineer)", by_lead: true }), "closed_not_effective"))
      .toBe("Closed 18-02-2027 by Priya (engineer), the lead: did not work");
    expect(closedLine(closed({ by_lead: true }), "dropped")).toBe("Dropped 18-02-2027 by Arun (manager), the lead");
  });
});

describe("figureRows", () => {
  const symptom = { id: 1, code: "1", label: "Won't start" };
  const figures = (after, symptoms = [symptom]) => ({
    symptoms,
    before: { days: 90, breakdowns: 3, symptom_breakdowns: symptoms.length ? 2 : null, downtime_minutes: 300 },
    after: { symptom_breakdowns: symptoms.length ? 0 : null, breakdowns: 0, downtime_minutes: 0, ...after },
  });
  it("builds the rows and a 'so far' header while the watch runs", () => {
    const table = figureRows(figures({ days: 41 }), null);
    expect(table.headers).toEqual(["", "90 days before", "41 days so far"]);
    expect(table.rows).toEqual([
      { label: "Breakdowns", before: "3", after: "0" },
      { label: "Of them: Won't start", before: "2", after: "0" },
      { label: "Downtime", before: "5 h", after: "0 min" },
    ]);
  });
  it("leaves out the symptom row when there are no symptoms", () => {
    const table = figureRows(figures({ days: 41 }, []), null);
    expect(table.rows.map((r) => r.label)).toEqual(["Breakdowns", "Downtime"]);
  });
  it("joins several symptoms with 'or'", () => {
    const two = [symptom, { id: 2, code: "2", label: "Jams" }];
    expect(figureRows(figures({ days: 5 }, two), null).rows[1].label).toBe("Of them: Won't start or Jams");
  });
  it("reads '90 days after' when the watch has ended, or the improvement is closed effective", () => {
    expect(figureRows(figures({ days: 90 }), null, true).headers[2]).toBe("90 days after");
    expect(figureRows(figures({ days: 90 }), { at: "x" }).headers[2]).toBe("90 days after");
  });
  it("reads '20 days after' for a record dropped 20 days into its watch", () => {
    expect(figureRows(figures({ days: 20 }), { at: "x" }).headers[2]).toBe("20 days after");
  });
});

describe("repeatText", () => {
  const repeat = { occurred_at: "2027-01-05T09:10:00+05:30", intensity: "critical", symptom: { label: "Won't start" }, in_watch: true };
  it("gives the date, the symptom and the severity", () => {
    expect(repeatText(repeat)).toBe("on 05-01-2027 (Won't start, breakdown)");
  });
  it("says so when the repeat is after the watch", () => {
    expect(repeatText({ ...repeat, intensity: "degraded", in_watch: false })).toBe("on 05-01-2027 (Won't start, defect, after the watch)");
  });
});

describe("watchEndDate", () => {
  it("adds 90 days across a year end", () => expect(watchEndDate("2026-11-20T15:30:00+05:30", 90)).toBe("2027-02-18"));
  it("uses the date part whatever the time zone", () => {
    expect(watchEndDate("2026-11-20T23:59:00", 1)).toBe("2026-11-21");
    expect(watchEndDate("2026-11-20T00:01:00+05:30", 0)).toBe("2026-11-20");
  });
  it("gives empty for no date", () => {
    expect(watchEndDate(null, 90)).toBe("");
    expect(watchEndDate("soon", 90)).toBe("");
  });
});

describe("machinesText and symptomsText", () => {
  const figures = { machines: [{ code: "MCC1" }, { code: "MCC2" }], symptoms: [{ label: "Won't start" }, { label: "Trips" }] };
  it("joins the machine codes with commas", () => {
    expect(machinesText(figures)).toBe("MCC1, MCC2");
    expect(machinesText({ machines: [] })).toBe("");
  });
  it("joins the symptom labels with 'or'", () => {
    expect(symptomsText(figures)).toBe("Won't start or Trips");
    expect(symptomsText({ symptoms: [] })).toBe("");
  });
});
