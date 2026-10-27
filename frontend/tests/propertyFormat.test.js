/** The display rules of equipment properties (S043 § 7.1, § 7.4; the Location type: S061). */

import { describe, expect, it } from "vitest";
import { accuracyText, locationErrorText, positionText, typeLabel, typeSummary, valueText } from "../src/utils/propertyFormat";

describe("typeLabel", () => {
  it("names each data type", () => {
    expect(["number", "choice", "text", "yes_no", "geo"].map(typeLabel)).toEqual([
      "Number", "Choice", "Text", "Yes / No", "Location",
    ]);
    expect(typeLabel("other")).toBe("other");
  });
});

describe("typeSummary", () => {
  it("adds a number's unit", () => {
    expect(typeSummary({ data_type: "number", unit: "kW" })).toBe("Number · kW");
    expect(typeSummary({ data_type: "number", unit: null })).toBe("Number");
  });

  it("counts a choice's active options", () => {
    const options = [{ active: 1 }, { active: 1 }, { active: 0 }];
    expect(typeSummary({ data_type: "choice", options })).toBe("Choice · 2 options");
    expect(typeSummary({ data_type: "choice", options: [{ active: 1 }] })).toBe("Choice · 1 option");
    expect(typeSummary({ data_type: "choice", options: [] })).toBe("Choice · 0 options");
  });

  it("shows text and yes/no plainly", () => {
    expect(typeSummary({ data_type: "text", unit: null })).toBe("Text");
    expect(typeSummary({ data_type: "yes_no" })).toBe("Yes / No");
    expect(typeSummary({ data_type: "geo", unit: null })).toBe("Location");
  });
});

describe("valueText", () => {
  it("shows a dash for no value", () => {
    expect(valueText("62.5 kVA")).toBe("62.5 kVA");
    expect(valueText(null)).toBe("—");
  });
});

describe("Use my current location (S061 D3)", () => {
  it("fills 6 decimals", () => {
    expect(positionText({ latitude: 11.0168234567, longitude: 76.9558 })).toBe("11.016823, 76.955800");
    expect(positionText({ latitude: -0.5, longitude: -179.1234567 })).toBe("-0.500000, -179.123457");
  });

  it("says how accurate the reading is, and advises above 50 m", () => {
    expect(accuracyText(12.4)).toBe("About 12 m accurate");
    expect(accuracyText(50)).toBe("About 50 m accurate");
    expect(accuracyText(300.2)).toBe("Rough location (about 300 m). Go into the open, then try again.");
  });

  it("tells a blocked permission from no position", () => {
    expect(locationErrorText(1)).toBe(
      "Location is blocked for Yantra in this browser. Allow it in the browser's settings, or type the location"
    );
    for (const code of [2, 3]) {
      expect(locationErrorText(code)).toBe("The phone could not find its location. Try again in the open, or type the location");
    }
  });
});
