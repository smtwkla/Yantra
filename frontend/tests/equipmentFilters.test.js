import { describe, expect, it } from "vitest";
import { activeFirstBy, classChoicesFor, classOutsideCategory } from "../src/utils/equipmentFilters.js";

// Two categories: 1 Lifting equipment (EOT, HST), 2 Utilities (CMP); PMP has none; OLD is inactive
const CLASSES = [
  { id: 10, code: "HST", active: 1, category_id: 1 },
  { id: 11, code: "EOT", active: 1, category_id: 1 },
  { id: 12, code: "CMP", active: 1, category_id: 2 },
  { id: 13, code: "PMP", active: 1, category_id: null },
  { id: 14, code: "OLD", active: 0, category_id: 1 },
];
const codes = (list) => list.map((c) => c.code);

describe("activeFirstBy", () => {
  it("puts active records first, each group by the key, and leaves the input as it was", () => {
    const categories = [{ name: "Utilities", active: 1 }, { name: "Old", active: 0 }, { name: "Conveyors", active: 1 }];
    expect(activeFirstBy(categories, "name").map((c) => c.name)).toEqual(["Conveyors", "Utilities", "Old"]);
    expect(categories[0].name).toBe("Utilities");
    expect(activeFirstBy(null, "name")).toEqual([]);
  });
});

describe("classChoicesFor", () => {
  it("lists every class, active first, by code, with no category", () => {
    expect(codes(classChoicesFor(CLASSES, "", ""))).toEqual(["CMP", "EOT", "HST", "PMP", "OLD"]);
    expect(codes(classChoicesFor(CLASSES, undefined, undefined))).toEqual(["CMP", "EOT", "HST", "PMP", "OLD"]);
  });

  it("lists only the category's classes, the URL's string id matching the API's number", () => {
    expect(codes(classChoicesFor(CLASSES, "1", ""))).toEqual(["EOT", "HST", "OLD"]);
    expect(codes(classChoicesFor(CLASSES, "2", "12"))).toEqual(["CMP"]);
  });

  it("keeps a chosen class outside the category, last, so the filter is never invisible", () => {
    expect(codes(classChoicesFor(CLASSES, "2", "13"))).toEqual(["CMP", "PMP"]);
  });

  it("copes with the classes still loading", () => {
    expect(classChoicesFor(null, "1", "10")).toEqual([]);
  });
});

describe("classOutsideCategory", () => {
  it("is true only for a chosen class not in the chosen category", () => {
    expect(classOutsideCategory(CLASSES, "1", "10")).toBe(false);
    expect(classOutsideCategory(CLASSES, "1", "12")).toBe(true);
    expect(classOutsideCategory(CLASSES, "1", "13")).toBe(true);
  });

  it("is false with no category or no class chosen", () => {
    expect(classOutsideCategory(CLASSES, "", "12")).toBe(false);
    expect(classOutsideCategory(CLASSES, "1", "")).toBe(false);
    expect(classOutsideCategory(CLASSES, null, null)).toBe(false);
  });

  it("clears an unknown class", () => {
    expect(classOutsideCategory(CLASSES, "1", "99")).toBe(true);
  });
});
