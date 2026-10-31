import { describe, expect, it } from "vitest";
import { readingSites, unitSites } from "../src/stores/equipment.js";

const SITES = [
  { id: 1, code: "BRICKS", name: "Bricks plant", active: true },
  { id: 2, code: "SMTW", name: "Main factory", active: true },
  { id: 3, code: "OLD", name: "Closed site", active: false },
];
const UNITS = [
  { id: 10, site_id: 1, code: "FILTER", active: true },
  { id: 20, site_id: 2, code: "MCC1", active: true },
  { id: 21, site_id: 2, code: "MCC2", active: true },
  { id: 22, site_id: 2, code: "OLD", active: false },
  { id: 30, site_id: 3, code: "X", active: true },
];
const mine = (reading_unit_ids) => ({ all_units: false, unit_ids: [], edit_unit_ids: [], reading_unit_ids });

describe("readingSites (S040 BR1-01, BR2-01)", () => {
  it("offers the sites where the user logs readings, as id, code and name", () => {
    expect(readingSites(UNITS, SITES, mine([20]))).toEqual([{ id: 2, code: "SMTW", name: "Main factory" }]);
    expect(readingSites(UNITS, SITES, mine([20, 10])).map((s) => s.code)).toEqual(["BRICKS", "SMTW"]);
  });

  it("null (admin) is every active site with an active unit", () => {
    expect(readingSites(UNITS, SITES, mine(null)).map((s) => s.code)).toEqual(["BRICKS", "SMTW"]);
  });

  it("leaves out inactive units, inactive sites, and a user who logs nowhere", () => {
    expect(readingSites(UNITS, SITES, mine([22]))).toEqual([]);
    expect(readingSites(UNITS, SITES, mine([30]))).toEqual([]);
    expect(readingSites(UNITS, SITES, mine([]))).toEqual([]);
  });

  it("copes with lists that are not loaded yet", () => {
    expect(readingSites(null, null, mine(null))).toEqual([]);
  });
});

describe("unitSites (S087 A1)", () => {
  const units = (unit_ids, all_units = false) => ({ all_units, unit_ids, edit_unit_ids: [], reading_unit_ids: [] });

  it("offers the active sites where the user has an active unit", () => {
    expect(unitSites(UNITS, SITES, units([20]))).toEqual([{ id: 2, code: "SMTW", name: "Main factory" }]);
    expect(unitSites(UNITS, SITES, units([20, 10])).map((s) => s.code)).toEqual(["BRICKS", "SMTW"]);
  });

  it("all-units access is every active site with a unit; no units is no site", () => {
    expect(unitSites(UNITS, SITES, units([], true)).map((s) => s.code)).toEqual(["BRICKS", "SMTW"]);
    expect(unitSites(UNITS, SITES, units([]))).toEqual([]);
    expect(unitSites(UNITS, SITES, units([30]))).toEqual([]);
  });

  it("copes with lists that are not loaded yet", () => {
    expect(unitSites(null, null, units([], true))).toEqual([]);
  });
});
