import { describe, expect, it } from "vitest";
import {
  defaultProblem, defaultTitle, improvementStateLabel, lossText, PROBLEM_MAX, TITLE_MAX,
} from "../src/utils/improvementLabels";

const ticket = (extra = {}) => ({ machine: { code: "HP003" }, failure_mode: null, description: "", ...extra });

describe("improvementStateLabel", () => {
  it("names a known state", () => expect(improvementStateLabel("analysing")).toBe("Analysing"));
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
