import { describe, expect, it } from "vitest";
import { chunkSheets, labelsPath, parseLabelQuery } from "../src/utils/labelSheets.js";

describe("parseLabelQuery", () => {
  it("reads the ids and the parts flag", () => {
    expect(parseLabelQuery({ ids: "12,15,40", parts: "1" })).toEqual({ ids: [12, 15, 40], withParts: true });
    expect(parseLabelQuery({ ids: "7", parts: "0" })).toEqual({ ids: [7], withParts: false });
    expect(parseLabelQuery({ ids: "7" })).toEqual({ ids: [7], withParts: false });
  });

  it("drops repeats and keeps the order", () => {
    expect(parseLabelQuery({ ids: "5,3,5" }).ids).toEqual([5, 3]);
  });

  it("refuses a link without a clean list", () => {
    for (const ids of [undefined, "", "1,,2", "1,a", "0", "-1", "1.5", ["1", "2"]]) {
      expect(parseLabelQuery({ ids })).toBeNull();
    }
    expect(parseLabelQuery(undefined)).toBeNull();
  });
});

describe("chunkSheets", () => {
  const labels = (n) => Array.from({ length: n }, (_, i) => ({ id: i + 1 }));

  it("puts 15 on a sheet", () => {
    expect(chunkSheets(labels(15)).map((s) => s.length)).toEqual([15]);
    expect(chunkSheets(labels(16)).map((s) => s.length)).toEqual([15, 1]);
    expect(chunkSheets(labels(16))[1][0].id).toBe(16);
  });

  it("gives no sheet for no labels", () => {
    expect(chunkSheets([])).toEqual([]);
  });
});

describe("labelsPath", () => {
  it("builds the print page's address", () => {
    expect(labelsPath([3, 1])).toBe("/labels?ids=3,1&parts=0");
    expect(labelsPath([3], true)).toBe("/labels?ids=3&parts=1");
  });
});
