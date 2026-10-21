import { describe, expect, it } from "vitest";
import {
  ageText, EVENT_LABELS, firstName, groupPeople, INTENSITY_BADGE_CLASS, INTENSITY_CHOICES, INTENSITY_LABELS,
  intensityChanges, isBreakdown, isLowering, minutesText, moveConsequence, moveLabel, moveSaveLabel, problemText,
  raiseSaveLabel, restoreTimeLabel, sendBackChoices, sendBackQuestion, STATE_LABELS, toLocalDateValue, toLocalInputValue,
} from "../src/utils/ticketLabels.js";

describe("ticket labels (S017)", () => {
  it("names each intensity, breakdown or defect", () => {
    expect(INTENSITY_LABELS).toEqual({ critical: "Breakdown", degraded: "Defect", initial: "Defect · initial" });
    expect(Object.keys(INTENSITY_BADGE_CLASS)).toEqual(["critical", "degraded", "initial"]);
    expect(INTENSITY_CHOICES.map((c) => c.value)).toEqual(["critical", "degraded", "initial"]);
  });

  it("names every state", () => {
    expect(Object.keys(STATE_LABELS)).toEqual(["raised", "acknowledged", "in_progress", "back_in_service", "closed"]);
    expect(STATE_LABELS.back_in_service).toBe("Back in service");
  });

  it("only critical is a breakdown", () => {
    expect(isBreakdown("critical")).toBe(true);
    expect(isBreakdown("degraded")).toBe(false);
    expect(isBreakdown("initial")).toBe(false);
  });
});

describe("ageText", () => {
  const now = new Date("2026-10-20T14:30:00+05:30");

  it("minutes, hours and days, rounded down", () => {
    expect(ageText("2026-10-20T14:30:00+05:30", now)).toBe("0 min");
    expect(ageText("2026-10-20T14:18:00+05:30", now)).toBe("12 min");
    expect(ageText("2026-10-20T13:31:00+05:30", now)).toBe("59 min");
    expect(ageText("2026-10-20T13:30:00+05:30", now)).toBe("1 h");
    expect(ageText("2026-10-19T14:31:00+05:30", now)).toBe("23 h");
    expect(ageText("2026-10-19T14:30:00+05:30", now)).toBe("1 d");
    expect(ageText("2026-10-13T09:00:00+05:30", now)).toBe("7 d");
  });

  it("a time slightly ahead reads 0 min; not a date reads nothing", () => {
    expect(ageText("2026-10-20T14:33:00+05:30", now)).toBe("0 min");
    expect(ageText("yesterday", now)).toBe("");
    expect(ageText(null, now)).toBe("");
  });
});

describe("problemText", () => {
  it("the symptom first, else the start of the description", () => {
    expect(problemText({ failure_mode: { label: "Abnormal noise" }, description: "Grinding" })).toBe("Abnormal noise");
    expect(problemText({ failure_mode: null, description: "Oil on the floor" })).toBe("Oil on the floor");
    expect(problemText({ failure_mode: null, description: "x".repeat(100) }, 10)).toBe(`${"x".repeat(9)}…`);
    expect(problemText({ failure_mode: null, description: null })).toBe("");
  });
});

describe("toLocalInputValue", () => {
  it("formats a local date for datetime-local", () => {
    expect(toLocalInputValue(new Date(2026, 9, 5, 7, 3))).toBe("2026-10-05T07:03");
  });
});

describe("move labels (S018)", () => {
  it("back in service reads Fixed on a defect", () => {
    expect(moveLabel("restore", "critical")).toBe("Back in service");
    expect(moveLabel("restore", "degraded")).toBe("Fixed");
    expect(moveSaveLabel("restore", "initial")).toBe("Fixed");
    expect(moveLabel("start", "critical")).toBe("Start work");
  });

  it("Save says what it does; close and not a fault say the ticket becomes read-only", () => {
    expect(moveSaveLabel("close", "critical")).toBe("Close ticket");
    expect(moveSaveLabel("not-a-fault", "critical")).toBe("Close as not a fault");
    expect(moveSaveLabel("send-back", "critical")).toBe("Send back");
    expect(moveConsequence("close", "TK-2026-10-014")).toBe("TK-2026-10-014 becomes read-only.");
    expect(moveConsequence("not-a-fault", "TK-2026-10-014")).toBe("TK-2026-10-014 becomes read-only.");
    expect(moveConsequence("acknowledge", "TK-2026-10-014")).toBe("");
  });

  it("send back asks per intensity; No on a breakdown says downtime stops", () => {
    expect(sendBackQuestion("critical")).toBe("Machine down again?");
    expect(sendBackQuestion("degraded")).toBe("Has the machine stopped?");
    expect(sendBackChoices("critical").map((c) => c.value)).toEqual([true, false]);
    expect(sendBackChoices("critical")[1].label).toContain("downtime stops");
    expect(sendBackChoices("degraded")[0].label).toContain("becomes a breakdown");
  });

  it("the back-in-service time and the raise's Save follow the intensity (A1)", () => {
    expect(restoreTimeLabel("critical")).toBe("Back in service at");
    expect(restoreTimeLabel("degraded")).toBe("Fixed at");
    expect(raiseSaveLabel(false, "critical")).toBe("Save ticket");
    expect(raiseSaveLabel(true, "critical")).toBe("Raise and mark back in service");
    expect(raiseSaveLabel(true, "initial")).toBe("Raise and mark fixed");
  });

  it("names every S018 event", () => {
    for (const event of ["acknowledged", "started", "back_in_service", "sent_back", "closed", "closed_not_a_fault",
      "regraded", "edited", "assigned", "unassigned"]) {
      expect(EVENT_LABELS[event]).toBeTruthy();
    }
  });
});

describe("intensity changes on the timeline", () => {
  it("the first grade, then each change from the events' own intensity", () => {
    const events = [
      { event: "raised", intensity: "degraded" }, { event: "acknowledged", intensity: null },
      { event: "regraded", intensity: "critical" }, { event: "sent_back", intensity: "degraded" },
    ];
    expect(intensityChanges(events)).toEqual(["Defect", "", "Defect → Breakdown", "Breakdown → Defect"]);
  });

  it("lowering follows the choices' order", () => {
    expect(isLowering("critical", "degraded")).toBe(true);
    expect(isLowering("initial", "critical")).toBe(false);
  });
});

describe("minutesText", () => {
  it("hours and minutes; unknown is a dash", () => {
    expect(minutesText(85)).toBe("1 h 25 min");
    expect(minutesText(45)).toBe("45 min");
    expect(minutesText(120)).toBe("2 h");
    expect(minutesText(0)).toBe("0 min");
    expect(minutesText(null)).toBe("—");
  });
});

describe("firstName and dates", () => {
  it("the first word of a name", () => {
    expect(firstName("Murugan K")).toBe("Murugan");
    expect(firstName("  Ravi  ")).toBe("Ravi");
  });

  it("a local date for a date input", () => {
    expect(toLocalDateValue(new Date(2026, 9, 5, 23, 40))).toBe("2026-10-05");
  });
});

describe("groupPeople", () => {
  const people = [
    { id: 1, name: "Anand", assignable: true },
    { id: 2, name: "Bala", assignable: true },
    { id: 3, name: "Chitra", assignable: false },
    { id: 4, name: "Devi", assignable: true },
  ];
  const ids = (groups) => groups.map((g) => [g.label, g.people.map((p) => p.id)]);

  it("own person first, then assignees, the ladder, the others", () => {
    expect(ids(groupPeople(people, { ownId: 3, assigneeIds: [2] }))).toEqual([
      ["You", [3]], ["Assigned", [2]], ["Maintenance", [1, 4]],
    ]);
    expect(ids(groupPeople(people))).toEqual([["Maintenance", [1, 2, 4]], ["Others at the site", [3]]]);
  });

  it("the Assign dialog: assigned left out, the ladder only", () => {
    expect(ids(groupPeople(people, { excludeIds: [2], assignableOnly: true }))).toEqual([["Maintenance", [1, 4]]]);
  });

  it("filters by part of the name, any case", () => {
    expect(ids(groupPeople(people, { filter: "AL" }))).toEqual([["Maintenance", [2]]]);
    expect(groupPeople(people, { filter: "zz" })).toEqual([]);
  });
});
