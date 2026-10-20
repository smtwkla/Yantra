import { describe, expect, it } from "vitest";
import {
  ageText, INTENSITY_BADGE_CLASS, INTENSITY_CHOICES, INTENSITY_LABELS, isBreakdown, problemText, STATE_LABELS,
  toLocalInputValue,
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
