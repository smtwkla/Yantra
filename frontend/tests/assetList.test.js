import { describe, expect, it } from "vitest";
import { assetListPath, filtersLabel, parseAssetListQuery } from "../src/utils/assetList.js";

describe("parseAssetListQuery", () => {
  it("keeps the list's filters and drops unknown keys", () => {
    const { params } = parseAssetListQuery({ site_id: "1", unit_id: "2", class_id: "3", type_id: "4", status: "standby",
      criticality: "A", level: "all", q: "pump", page: "2", junk: "x" });
    expect(params).toEqual({ site_id: "1", unit_id: "2", class_id: "3", type_id: "4", status: "standby", criticality: "A" });
  });

  it("defaults the switches off and reads them when on", () => {
    expect(parseAssetListQuery({})).toEqual({ params: {}, withParts: false, checklist: false });
    expect(parseAssetListQuery({ parts: "1", check: "1" })).toMatchObject({ withParts: true, checklist: true });
    expect(parseAssetListQuery({ parts: "0", check: "yes" })).toMatchObject({ withParts: false, checklist: false });
  });

  it("includes scrapped for scrapped=1 or status=scrapped alone", () => {
    expect(parseAssetListQuery({ scrapped: "1" }).params.include_scrapped).toBe("1");
    expect(parseAssetListQuery({ status: "scrapped" }).params.include_scrapped).toBe("1");
    expect(parseAssetListQuery({ status: "standby" }).params.include_scrapped).toBeUndefined();
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

  it("is the bare page for an unfiltered list", () => {
    expect(assetListPath({})).toBe("/asset-list");
  });
});

describe("filtersLabel", () => {
  const lookups = { classes: [{ id: 3, code: "RPP" }], types: [{ id: 4, name: "Closed" }] };

  it("names the filters in words", () => {
    expect(filtersLabel({ class_id: "3", type_id: "4", status: "in_service", criticality: "A" }, lookups))
      .toBe("Class: RPP · Type: Closed · Status: In service · Criticality: A");
  });

  it("says scrapped included", () => {
    expect(filtersLabel({ include_scrapped: "1" }, lookups)).toBe("scrapped included");
    expect(filtersLabel({ status: "scrapped", include_scrapped: "1" }, lookups)).toBe("Status: Scrapped");
  });

  it("reads All equipment with no filter, site and unit not repeated", () => {
    expect(filtersLabel({}, lookups)).toBe("All equipment");
    expect(filtersLabel({ site_id: "1", unit_id: "2" }, lookups)).toBe("All equipment");
  });

  it("falls back to the id while the masters load", () => {
    expect(filtersLabel({ class_id: "9" }, {})).toBe("Class: #9");
  });
});
