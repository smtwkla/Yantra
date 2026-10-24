/** The display rules of equipment properties (S035 § 7.1, § 7.4). */

import { describe, expect, it } from "vitest";
import { typeLabel, typeSummary, valueText } from "../src/utils/propertyFormat";

describe("typeLabel", () => {
  it("names each data type", () => {
    expect(["number", "choice", "text", "yes_no"].map(typeLabel)).toEqual(["Number", "Choice", "Text", "Yes / No"]);
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
  });
});

describe("valueText", () => {
  it("shows a dash for no value", () => {
    expect(valueText("62.5 kVA")).toBe("62.5 kVA");
    expect(valueText(null)).toBe("—");
  });
});
