import { describe, expect, it } from "vitest";
import {
  causeText, defaultProblem, defaultRootCause, defaultTitle, improvementStateLabel, lossText, PROBLEM_MAX, ROOT_CAUSE_MAX,
  ticketCauses, TITLE_MAX, whyBody,
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
