/** The equipment list's property filter — the pure helpers (S062 § 5.1, § 5.3, § 8.3). */

import { describe, expect, it } from "vitest";
import {
  MAX_RULES, decodeFilter, filterSnapshot, describeFilter, encodeFilter, excludesNoValue, operatorLabel, operatorsOf, propsChanges,
  ruleComplete, takesValue,
} from "../src/utils/propertyFilter";

const PROPERTIES = [
  { id: 12, name: "Rated power", data_type: "number", unit: "kW", options: [] },
  {
    id: 15, name: "Mobility", data_type: "choice", unit: null,
    options: [{ id: 31, label: "Fixed", active: 1 }, { id: 32, label: "Mobile", active: 1 }, { id: 33, label: "Portable", active: 1 }],
  },
  { id: 17, name: "Frame size", data_type: "text", unit: null, options: [] },
  { id: 18, name: "Ex-proof", data_type: "yes_no", unit: null, options: [] },
  { id: 19, name: "GPS location", data_type: "geo", unit: null, options: [] },
];

const POWER_GT = { property_id: 12, op: "gt", value: "7.5" };
const MOBILE = { property_id: 15, op: "in", value: [33, 32] };

describe("encodeFilter and decodeFilter", () => {
  it("round-trip, the keys in order, has / none without a value", () => {
    const filter = { match: "any", rules: [POWER_GT, MOBILE, { property_id: 19, op: "has", value: "x" }] };
    const raw = encodeFilter(filter);
    expect(raw).toBe(
      '{"match":"any","rules":[{"property_id":12,"op":"gt","value":"7.5"},{"property_id":15,"op":"in","value":[33,32]},'
        + '{"property_id":19,"op":"has"}]}'
    );
    expect(decodeFilter(raw)).toEqual({
      match: "any",
      rules: [POWER_GT, MOBILE, { property_id: 19, op: "has", value: undefined }],
    });
  });

  it("encodes no rule as no filter", () => {
    expect(encodeFilter(null)).toBeNull();
    expect(encodeFilter({ match: "all", rules: [] })).toBeNull();
  });

  it("reads a missing match as all", () => {
    expect(decodeFilter('{"rules":[]}')).toEqual({ match: "all", rules: [] });
  });

  it.each([
    ["not JSON", "{cut"],
    ["an array", "[]"],
    ["no rules", '{"match":"all"}'],
    ["a wrong match", '{"match":"some","rules":[]}'],
    ["a rule without a property", '{"rules":[{"op":"has"}]}'],
    ["a property id as text", '{"rules":[{"property_id":"12","op":"has"}]}'],
    ["a property id of 0", '{"rules":[{"property_id":0,"op":"has"}]}'],
    ["too many rules", JSON.stringify({ rules: Array(MAX_RULES + 1).fill({ property_id: 12, op: "has" }) })],
    ["too long", JSON.stringify({ rules: [{ property_id: 12, op: "contains", value: "x".repeat(4000) }] })],
    ["empty", ""],
    ["missing", undefined],
  ])("decodes %s to null", (_name, raw) => {
    expect(decodeFilter(raw)).toBeNull();
  });
});

describe("operators", () => {
  it("lists each data type's operators in order", () => {
    expect(operatorsOf("number")).toEqual(["eq", "ne", "lt", "le", "gt", "ge", "between", "has", "none"]);
    expect(operatorsOf("choice")).toEqual(["in", "not_in", "has", "none"]);
    expect(operatorsOf("text")).toEqual(["contains", "eq", "has", "none"]);
    expect(operatorsOf("yes_no")).toEqual(["eq", "has", "none"]);
    expect(operatorsOf("geo")).toEqual(["has", "none"]);
    expect(operatorsOf("other")).toEqual([]);
  });

  it("names them in words", () => {
    expect(operatorsOf("number").map((op) => operatorLabel("number", op))).toEqual([
      "equals", "not equal to", "less than", "at most", "more than", "at least", "between", "has a value", "has no value",
    ]);
    expect(operatorLabel("text", "eq")).toBe("is");
    expect(operatorLabel("yes_no", "eq")).toBe("is");
    expect(operatorLabel("choice", "not_in")).toBe("is not");
  });

  it("knows which take a value and which leave out no value", () => {
    expect(["has", "none", "gt"].map(takesValue)).toEqual([false, false, true]);
    expect(["ne", "not_in", "eq", "in"].map(excludesNoValue)).toEqual([true, true, false, false]);
  });
});

describe("ruleComplete", () => {
  it.each([
    [{ property_id: null, op: "", value: "" }, "number", false],
    [{ property_id: 12, op: "gt", value: " " }, "number", false],
    [{ property_id: 12, op: "gt", value: "7,5" }, "number", true], // the backend refuses it
    [{ property_id: 12, op: "between", value: ["5", ""] }, "number", false],
    [{ property_id: 12, op: "between", value: ["5", "10"] }, "number", true],
    [{ property_id: 15, op: "in", value: [] }, "choice", false],
    [{ property_id: 15, op: "in", value: [31] }, "choice", true],
    [{ property_id: 18, op: "eq", value: "" }, "yes_no", false],
    [{ property_id: 18, op: "eq", value: false }, "yes_no", true],
    [{ property_id: 19, op: "has" }, "geo", true],
    [{ property_id: 17, op: "contains", value: "IE3" }, "text", true],
  ])("%j as %s: %s", (rule, dataType, complete) => {
    expect(ruleComplete(rule, dataType)).toBe(complete);
  });
});

describe("describeFilter", () => {
  it("reads one condition", () => {
    expect(describeFilter({ match: "all", rules: [POWER_GT] }, PROPERTIES)).toBe("Properties: Rated power more than 7.5 kW");
  });

  it("says the match once and separates the conditions with ·", () => {
    const rules = [POWER_GT, { property_id: 15, op: "in", value: [33, 32] }];
    expect(describeFilter({ match: "all", rules }, PROPERTIES))
      .toBe("Properties (all of): Rated power more than 7.5 kW · Mobility is Portable or Mobile");
    expect(describeFilter({ match: "any", rules }, PROPERTIES))
      .toBe("Properties (any of): Rated power more than 7.5 kW · Mobility is Portable or Mobile");
  });

  it("reads between, has, none, text and yes / no", () => {
    const rules = [
      { property_id: 12, op: "between", value: ["5", "10"] },
      { property_id: 19, op: "has" },
      { property_id: 12, op: "none" },
      { property_id: 17, op: "contains", value: "IE3" },
      { property_id: 18, op: "eq", value: true },
      { property_id: 15, op: "not_in", value: [31] },
    ];
    expect(describeFilter({ match: "any", rules }, PROPERTIES)).toBe(
      "Properties (any of): Rated power between 5 and 10 kW · GPS location has a value · Rated power has no value"
        + ' · Frame size contains "IE3" · Ex-proof is Yes · Mobility is not Fixed'
    );
  });

  it("names an unknown property and option by id", () => {
    expect(describeFilter({ match: "all", rules: [{ property_id: 99, op: "has" }] }, PROPERTIES)).toBe("Properties: #99 has a value");
    expect(describeFilter({ match: "all", rules: [{ property_id: 15, op: "in", value: [77] }] }, PROPERTIES))
      .toBe("Properties: Mobility is #77");
    expect(describeFilter({ match: "all", rules: [{ property_id: 12, op: "has" }] }, null)).toBe("Properties: #12 has a value");
  });

  it("says an unreadable filter cannot be read", () => {
    expect(describeFilter(null, PROPERTIES)).toBe("Properties: cannot be read");
  });
});

describe("propsChanges (the level on the first property filter)", () => {
  it("widens the default level on the first filter", () => {
    expect(propsChanges({}, "x")).toEqual({ props: "x", level: "all" });
    expect(propsChanges({ class_id: "3" }, "x")).toEqual({ props: "x", level: "all" });
  });

  it("keeps the level on a change to a filter, or with any level in the URL", () => {
    expect(propsChanges({ props: "old" }, "x")).toEqual({ props: "x" });
    expect(propsChanges({ level: "component" }, "x")).toEqual({ props: "x" });
    expect(propsChanges({ level: "all" }, "x")).toEqual({ props: "x" });
  });

  it("clears without touching the level", () => {
    expect(propsChanges({ props: "old", level: "all" }, null)).toEqual({ props: null });
  });
});

describe("filterSnapshot (the dialog's dirty check, CR2-01)", () => {
  const line = (over) => ({ key: 1, property_id: 20, op: "eq", value: "true", low: "", high: "", optionIds: [], ...over });
  const typeOf = (l) => ({ 20: "yes_no", 15: "choice" })[l.property_id];
  const noTypes = () => undefined;

  it("differs for the same lines before and after the property list loads (the fault)", () => {
    expect(filterSnapshot("all", [line()], noTypes)).not.toBe(filterSnapshot("all", [line()], typeOf));
  });

  it("is equal for a copy of the starting lines when both sides use the same data types", () => {
    const start = [line(), line({ key: 2, property_id: 15, op: "in", optionIds: [3] })];
    const copy = JSON.parse(JSON.stringify(start));
    expect(filterSnapshot("all", copy, noTypes)).toBe(filterSnapshot("all", start, noTypes));
    expect(filterSnapshot("all", copy, typeOf)).toBe(filterSnapshot("all", start, typeOf));
  });

  it("differs when a value or the match changes", () => {
    const start = [line()];
    expect(filterSnapshot("all", [line({ value: "false" })], typeOf)).not.toBe(filterSnapshot("all", start, typeOf));
    expect(filterSnapshot("any", start, typeOf)).not.toBe(filterSnapshot("all", start, typeOf));
  });
});
