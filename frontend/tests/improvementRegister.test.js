import { afterEach, describe, expect, it } from "vitest";
import {
  actionsText, AGE_BAND_LABELS, monthPeriod, periodText, registerPath, workedShareText,
} from "../src/utils/improvementRegister";

describe("monthPeriod", () => {
  it("this month", () => expect(monthPeriod("2026-10-30", 0)).toEqual({ from: "2026-10-01", to: "2026-10-31" }));
  it("last month", () => expect(monthPeriod("2026-10-30", 1)).toEqual({ from: "2026-09-01", to: "2026-09-30" }));
  it("crosses the year", () => expect(monthPeriod("2026-01-15", 1)).toEqual({ from: "2025-12-01", to: "2025-12-31" }));
  it("February of a leap year", () => expect(monthPeriod("2028-03-31", 1)).toEqual({ from: "2028-02-01", to: "2028-02-29" }));
  it("February of an ordinary year", () => expect(monthPeriod("2026-03-31", 1).to).toBe("2026-02-28"));

  describe("in a time zone west of UTC (BR1-13)", () => {
    const original = process.env.TZ;
    afterEach(() => {
      if (original === undefined) delete process.env.TZ;
      else process.env.TZ = original;
    });

    it("gives the same month", () => {
      process.env.TZ = "America/Los_Angeles";
      expect(monthPeriod("2026-10-01", 0)).toEqual({ from: "2026-10-01", to: "2026-10-31" });
      expect(monthPeriod("2026-10-01", 1)).toEqual({ from: "2026-09-01", to: "2026-09-30" });
      expect(monthPeriod("2026-03-01", 1)).toEqual({ from: "2026-02-01", to: "2026-02-28" });
    });
  });
});

describe("actionsText", () => {
  it("open and overdue", () => expect(actionsText({ actions_open: 2, actions_overdue: 1 })).toBe("2 open, 1 overdue"));
  it("open only", () => expect(actionsText({ actions_open: 2, actions_overdue: 0 })).toBe("2 open"));
  it("none open", () => expect(actionsText({ actions_open: 0, actions_overdue: 0 })).toBe("None open"));
});

describe("periodText", () => {
  it("shows DD-MM-YYYY", () => expect(periodText({ from: "2026-10-01", to: "2026-10-31" })).toBe("01-10-2026 to 31-10-2026"));
});

describe("AGE_BAND_LABELS", () => {
  it("is word for word", () =>
    expect(AGE_BAND_LABELS).toEqual({
      "0_30": "0–30 days",
      "31_90": "31–90 days",
      "91_180": "91–180 days",
      over_180: "Over 180 days",
    }));
});

describe("workedShareText", () => {
  it("with verified closes", () =>
    expect(workedShareText({ it_worked: 3, did_not_work: 1, dropped: 0, worked_share: 75 })).toBe(
      "Closed: it worked 3 · Closed: did not work 1 · Dropped 0 · it worked in 75 % of the verified closes"
    ));
  it("without a verified close", () =>
    expect(workedShareText({ it_worked: 0, did_not_work: 0, dropped: 2, worked_share: null })).toBe(
      "Closed: it worked 0 · Closed: did not work 0 · Dropped 2 · No improvement was verified in this period."
    ));
});

describe("registerPath", () => {
  it("drops empty values", () =>
    expect(registerPath({ site_id: 3, from: "", to: undefined })).toBe("/tickets/improvements/register?site_id=3"));
  it("keeps a full query", () =>
    expect(registerPath({ site_id: "3", from: "2026-10-01", to: "2026-10-31" })).toBe(
      "/tickets/improvements/register?site_id=3&from=2026-10-01&to=2026-10-31"
    ));
  it("has no query when there is none", () => expect(registerPath()).toBe("/tickets/improvements/register"));
});
