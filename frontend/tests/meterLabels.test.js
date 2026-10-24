import { describe, expect, it } from "vitest";
import {
  expectedAnswerText, formatReading, goodReadingText, isToday, isUnavailable, KIND_LABELS, limitsBody, meterTypeOption,
  NOT_SAVED, notSavedOr, readingBadges, savedMessage, SOURCE_LABELS, unitAndKind,
} from "../src/utils/meterLabels.js";

const OIL = { id: 6, name: "Oil temperature", unit: "°C", kind: "gauge", decimals: 1, expected_answer: null };
const HOURS = { id: 1, name: "Run hours", unit: "h", kind: "counter", decimals: 1, expected_answer: null };
const OIL_OK = { id: 9, name: "Oil level above min", unit: null, kind: "yes_no", decimals: 0, expected_answer: "yes" };

describe("meter labels (S037, S038)", () => {
  it("names the four kinds and the two sources", () => {
    expect(KIND_LABELS).toEqual({ counter: "Counter", gauge: "Gauge", amount: "Amount per period", yes_no: "Yes / No" });
    expect(SOURCE_LABELS).toEqual({ model: "From the model", node: "This machine only" });
  });

  it("a Yes / No meter's expected answer (BR3-01)", () => {
    expect(expectedAnswerText(OIL_OK)).toBe("Expected: Yes");
    expect(expectedAnswerText({ ...OIL_OK, expected_answer: "no" })).toBe("Expected: No");
    expect(expectedAnswerText(OIL)).toBeNull();
  });

  it("what a good reading is, by kind", () => {
    expect(goodReadingText({ meter_type: OIL, limits_text: "Limits: 10–60 °C" })).toBe("Limits: 10–60 °C");
    expect(goodReadingText({ meter_type: OIL_OK, limits_text: null })).toBe("Expected: Yes");
    expect(goodReadingText({ meter_type: HOURS, limits_text: null })).toBeNull();
  });

  it("a dialog sends a gauge's limits, an empty box as null, and nothing for other kinds", () => {
    expect(limitsBody({ min_value: " 10 ", max_value: "" }, OIL)).toEqual({ min_value: "10", max_value: null });
    expect(limitsBody({ min_value: "5", max_value: "6" }, HOURS)).toEqual({});
    expect(limitsBody({}, null)).toEqual({});
  });

  it("a select option shows the unit and kind (BR3-05)", () => {
    expect(meterTypeOption(OIL)).toBe("Oil temperature (°C, Gauge)");
    expect(meterTypeOption(OIL_OK)).toBe("Oil level above min (Yes / No)");
    expect(unitAndKind(HOURS)).toBe("h · Counter");
    expect(unitAndKind(OIL_OK)).toBe("Yes / No");
  });
});

const SHIFT = { id: 8, name: "Shift production", unit: "pcs", kind: "amount", decimals: 0, expected_answer: null };

describe("readings (S039)", () => {
  it("formats a reading with the type's decimals, Indian grouping and the unit (U4)", () => {
    expect(formatReading("12345.6", HOURS)).toBe("12,345.6 h");
    expect(formatReading("12350", HOURS)).toBe("12,350.0 h");
    expect(formatReading("1234567.8", HOURS)).toBe("12,34,567.8 h");
    expect(formatReading("420", SHIFT)).toBe("420 pcs");
    expect(formatReading("-2.5", OIL)).toBe("-2.5 °C");
    expect(formatReading("no", OIL_OK)).toBe("No");
    expect(formatReading("yes", OIL_OK)).toBe("Yes");
  });

  it("names a reading's marks: High, Low, Not OK and Reset (BR3-06)", () => {
    expect(readingBadges({ limit_state: "high", is_reset: false })).toEqual(["High"]);
    expect(readingBadges({ limit_state: "low", is_reset: false })).toEqual(["Low"]);
    expect(readingBadges({ limit_state: "not_ok", is_reset: false })).toEqual(["Not OK"]);
    expect(readingBadges({ limit_state: null, is_reset: true })).toEqual(["Reset"]);
    expect(readingBadges({ limit_state: null, is_reset: false })).toEqual([]);
  });

  it("says what was saved only when the reading is outside what is good (BR2-09)", () => {
    const oil = { meter_type: OIL, min_value: "10", max_value: "60" };
    expect(savedMessage(oil, { limit_state: "high" })).toBe("Saved. Above the limit of 60 °C.");
    expect(savedMessage(oil, { limit_state: "low" })).toBe("Saved. Below the limit of 10 °C.");
    expect(savedMessage(oil, { limit_state: null })).toBeNull();
    expect(savedMessage({ meter_type: OIL_OK }, { limit_state: "not_ok" })).toBe("Saved. Not OK: the expected answer is Yes.");
    expect(savedMessage({ meter_type: { ...OIL_OK, expected_answer: "no" } }, { limit_state: "not_ok" }))
      .toBe("Saved. Not OK: the expected answer is No.");
  });

  it("does not name a limit the meter does not have (CR2-01)", () => {
    const noMax = { meter_type: OIL, min_value: "10", max_value: null };
    const noMin = { meter_type: OIL, min_value: null, max_value: "60" };
    expect(savedMessage(noMax, { limit_state: "high" })).toBe("Saved. Above the limit.");
    expect(savedMessage(noMin, { limit_state: "low" })).toBe("Saved. Below the limit.");
  });
});

describe("the readings sheet's shared helpers (S040)", () => {
  const status = (code) => Object.assign(new Error("x"), { status: code, field: "value" });

  it("a reading is not saved when the server or the network does not answer (BS1-02)", () => {
    for (const code of [502, 503, 504, undefined]) {
      expect(isUnavailable(status(code))).toBe(true);
      const err = notSavedOr(status(code));
      expect([err.message, err.field, err.status]).toEqual([NOT_SAVED, null, code]);
    }
  });

  it("a refusal is passed on as it is", () => {
    for (const code of [400, 403, 404, 409, 500]) {
      const err = status(code);
      expect(isUnavailable(err)).toBe(false);
      expect(notSavedOr(err)).toBe(err);
    }
  });

  it("isToday counts the IST day whatever the browser's time zone is (CR2-03)", () => {
    const now = new Date("2026-10-24T20:00:00Z"); // 25-10-2026 01:30 in IST, still 24-10 in UTC and the Americas
    expect(isToday("2026-10-25T01:00:00+05:30", now)).toBe(true);
    expect(isToday("2026-10-24T23:00:00+05:30", now)).toBe(false);
  });

  it("isToday compares the API's IST date with the IST date of now (BS1-07)", () => {
    const now = new Date("2026-10-24T18:29:00Z"); // 24-10-2026 23:59 in IST, a minute before midnight
    expect(isToday("2026-10-24T00:00:00+05:30", now)).toBe(true);
    expect(isToday("2026-10-24T17:50:00+05:30", now)).toBe(true);
    expect(isToday("2026-10-23T23:59:00+05:30", now)).toBe(false);
    expect(isToday("2026-10-25T00:00:00+05:30", now)).toBe(false);
    expect(isToday(null, now)).toBe(false);
    expect(isToday(undefined, now)).toBe(false);
  });

  it("isToday pads one-digit months and days", () => {
    expect(isToday("2026-01-05T08:00:00+05:30", new Date("2026-01-05T03:30:00Z"))).toBe(true);
  });
});
