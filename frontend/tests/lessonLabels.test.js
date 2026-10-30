import { describe, expect, it } from "vitest";
import { classBadgeText, classTickLabel, lessonDate, lessonTargetText } from "../src/utils/lessonLabels";

const machine = { id: 3, code: "HP003", name: "Hydraulic press 3" };
const cls = { id: 1, code: "HP", name: "Hydraulic press" };

describe("lessonTargetText", () => {
  it("names the machine and the class", () => {
    expect(lessonTargetText({ machine, class: cls })).toBe("HP003 — Hydraulic press 3 · for every Hydraulic press");
  });
  it("names only the class when the machine is outside the reader's units", () => {
    expect(lessonTargetText({ machine: null, class: cls })).toBe("For every Hydraulic press");
  });
  it("names only the machine for a machine lesson", () => {
    expect(lessonTargetText({ machine, class: null })).toBe("HP003 — Hydraulic press 3");
  });
});

describe("classBadgeText", () => {
  it("says every machine of the class", () => {
    expect(classBadgeText(cls)).toBe("Every Hydraulic press");
  });
});

describe("lessonDate", () => {
  it("is the date part, DD-MM-YYYY", () => {
    expect(lessonDate("2026-10-30T09:15:00+05:30")).toBe("30-10-2026");
    expect(lessonDate(null)).toBe("");
  });
});

describe("classTickLabel", () => {
  it("names the class, or says this machine's class when the name is unknown", () => {
    expect(classTickLabel("Hydraulic press")).toBe("Show on every machine of class Hydraulic press");
    expect(classTickLabel("")).toBe("Show on every machine of this machine's class");
  });
});
