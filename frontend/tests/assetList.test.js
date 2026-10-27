import { describe, expect, it } from "vitest";
import { assetListPath, filtersLabel, parseAssetListQuery } from "../src/utils/assetList.js";

const PROPS = JSON.stringify({ match: "all", rules: [{ property_id: 12, op: "gt", value: "7.5" }] });

describe("parseAssetListQuery", () => {
  it("keeps the list's filters and drops unknown keys", () => {
    const { params } = parseAssetListQuery({ site_id: "1", unit_id: "2", class_id: "3", type_id: "4", lifecycle: "standby",
      criticality: "A", level: "all", q: "pump", page: "2", junk: "x" });
    expect(params).toEqual({ site_id: "1", unit_id: "2", class_id: "3", type_id: "4", lifecycle: "standby", criticality: "A" });
  });

  it("defaults the switches off and reads them when on", () => {
    expect(parseAssetListQuery({})).toEqual({ params: {}, withParts: false, checklist: false });
    expect(parseAssetListQuery({ parts: "1", check: "1" })).toMatchObject({ withParts: true, checklist: true });
    expect(parseAssetListQuery({ parts: "0", check: "yes" })).toMatchObject({ withParts: false, checklist: false });
  });

  it("includes scrapped for scrapped=1 or lifecycle=scrapped alone", () => {
    expect(parseAssetListQuery({ scrapped: "1" }).params.include_scrapped).toBe("1");
    expect(parseAssetListQuery({ lifecycle: "scrapped" }).params.include_scrapped).toBe("1");
    expect(parseAssetListQuery({ lifecycle: "standby" }).params.include_scrapped).toBeUndefined();
  });

  it("carries the property filter (S062)", () => {
    expect(parseAssetListQuery({ props: PROPS }).params).toEqual({ props: PROPS });
  });

  it("copes with a missing query", () => {
    expect(parseAssetListQuery(undefined)).toEqual({ params: {}, withParts: false, checklist: false });
  });
});

describe("assetListPath", () => {
  it("drops level, q and page and keeps the filters", () => {
    expect(assetListPath({ site_id: "1", class_id: "3", level: "all", q: "x", page: "2", scrapped: "1" }))
      .toBe("/asset-list?site_id=1&class_id=3&scrapped=1");
  });

  it("adds the switches", () => {
    expect(assetListPath({ unit_id: "2" }, true, true)).toBe("/asset-list?unit_id=2&parts=1&check=1");
  });

  it("carries the property filter, encoded (S062)", () => {
    const path = assetListPath({ class_id: "3", props: PROPS, level: "all" });
    expect(path).toBe(`/asset-list?class_id=3&props=${encodeURIComponent(PROPS).replace(/%20/g, "+")}`);
    expect(new URLSearchParams(path.split("?")[1]).get("props")).toBe(PROPS);
  });

  it("is the bare page for an unfiltered list", () => {
    expect(assetListPath({})).toBe("/asset-list");
  });
});

describe("filtersLabel", () => {
  const lookups = { classes: [{ id: 3, code: "RPP" }], types: [{ id: 4, name: "Closed" }] };

  it("names the filters in words", () => {
    expect(filtersLabel({ class_id: "3", type_id: "4", lifecycle: "in_service", criticality: "A" }, lookups))
      .toBe("Class: RPP · Type: Closed · Lifecycle: In service · Criticality: A");
  });

  it("says scrapped included", () => {
    expect(filtersLabel({ include_scrapped: "1" }, lookups)).toBe("scrapped included");
    expect(filtersLabel({ lifecycle: "scrapped", include_scrapped: "1" }, lookups)).toBe("Lifecycle: Scrapped");
  });

  it("reads All equipment with no filter, site and unit not repeated", () => {
    expect(filtersLabel({}, lookups)).toBe("All equipment");
    expect(filtersLabel({ site_id: "1", unit_id: "2" }, lookups)).toBe("All equipment");
  });

  it("names the property filter in the words of the list's filter line (S062)", () => {
    const properties = [{ id: 12, name: "Rated power", data_type: "number", unit: "kW", options: [] }];
    expect(filtersLabel({ class_id: "3", props: PROPS }, { ...lookups, properties }))
      .toBe("Class: RPP · Properties: Rated power more than 7.5 kW");
    expect(filtersLabel({ props: "{cut" }, lookups)).toBe("Properties: cannot be read");
  });

  it("falls back to the id while the masters load", () => {
    expect(filtersLabel({ class_id: "9" }, {})).toBe("Class: #9");
  });

  it("names the category first, by name or by id (S063)", () => {
    const categories = [{ id: 7, name: "Lifting equipment" }];
    expect(filtersLabel({ category_id: "7", class_id: "3" }, { ...lookups, categories }))
      .toBe("Category: Lifting equipment · Class: RPP");
    expect(filtersLabel({ category_id: "8" }, lookups)).toBe("Category: #8");
  });
});

describe("the category filter (S063)", () => {
  it("is carried to the print page and read back", () => {
    expect(assetListPath({ category_id: "7", class_id: "3", level: "all" })).toBe("/asset-list?category_id=7&class_id=3");
    expect(parseAssetListQuery({ category_id: "7" }).params).toEqual({ category_id: "7" });
  });
});
