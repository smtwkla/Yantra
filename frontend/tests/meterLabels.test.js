import { describe, expect, it } from "vitest";
import {
  expectedAnswerText, goodReadingText, KIND_LABELS, limitsBody, meterTypeOption, SOURCE_LABELS, unitAndKind,
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
