/**
 * Tests for utils/contractLabels.js (S080): the type and status labels, and the dialog's body, which leaves
 * the call-out number and the cost note out unless the chosen site's flags allow them.  S081: the rupees, the
 * coverage lines, the response time, the overlap line and the machine dialog's body, which never sends a price
 * for an editor without the key.
 */

import { describe, expect, it } from "vitest";
import {
  CONTRACT_TYPES,
  STATUS_FILTERS,
  contractBody,
  contractTypeLabel,
  coverageLines,
  formatRupees,
  lineBody,
  overlapText,
  responseText,
  statusBadgeClass,
} from "../src/utils/contractLabels";

const FORM = {
  site_id: 1, vendor_id: 2, contract_type: "amc", title: "Atlas Copco AMC 2026–27", contract_number: "  ",
  from_date: "2026-04-01", to_date: "2027-03-31", covers_labour: true, covers_parts: false,
  covers_consumables: false, covers_breakdown_calls: false, breakdown_calls_per_year: 4, covered_text: " Labour ",
  not_covered_text: "", pm_visits_per_year: "4", response_hours: "", only_vendor_repairs: true,
  callout_number: "+91 00000 00000", cost_note: "Rs 1", notes: "",
};

describe("labels", () => {
  it("names the four types, AMC first", () => {
    expect(CONTRACT_TYPES.map((t) => t.value)).toEqual(["amc", "cmc", "warranty", "on_call"]);
    expect(contractTypeLabel("on_call")).toBe("On call");
    expect(contractTypeLabel("lease")).toBe("lease");
  });

  it("lists the status filters, Not ended first", () => {
    expect(STATUS_FILTERS.map((s) => s.value)).toEqual(["not_ended", "in_force", "ending", "upcoming", "ended", "all"]);
  });

  it("gives each status kind its badge", () => {
    expect(statusBadgeClass("in_force")).toBe("text-bg-success");
    expect(statusBadgeClass("ending")).toBe("text-bg-warning");
    expect(statusBadgeClass("ended")).toBe("text-bg-secondary");
    expect(statusBadgeClass("upcoming")).toBe("text-bg-info");
  });
});

describe("contractBody", () => {
  it("turns empty texts into null, numbers into numbers and clears calls without the tick", () => {
    const body = contractBody(FORM, { can_read_callout: false, can_read_cost: false });
    expect(body).toEqual({
      site_id: 1, vendor_id: 2, contract_type: "amc", title: "Atlas Copco AMC 2026–27",
      from_date: "2026-04-01", to_date: "2027-03-31", contract_number: null, covered_text: "Labour",
      not_covered_text: null, notes: null, pm_visits_per_year: 4, response_hours: null,
      breakdown_calls_per_year: null, covers_labour: true, covers_parts: false, covers_consumables: false,
      covers_breakdown_calls: false, only_vendor_repairs: true,
    });
  });

  it("keeps calls per year with the tick on", () => {
    expect(contractBody({ ...FORM, covers_breakdown_calls: true }, {}).breakdown_calls_per_year).toBe(4);
  });

  it("sends the call-out number only with its flag, the cost note only with its own", () => {
    const engineer = contractBody(FORM, { can_read_callout: true, can_read_cost: false });
    expect(engineer.callout_number).toBe("+91 00000 00000");
    expect("cost_note" in engineer).toBe(false);
    const manager = contractBody({ ...FORM, cost_note: " " }, { can_read_callout: true, can_read_cost: true });
    expect(manager.cost_note).toBeNull();
    expect("callout_number" in contractBody(FORM, null)).toBe(false);
  });

  it("sends empty dates as null, so the backend says which to enter", () => {
    const body = contractBody({ ...FORM, from_date: "", to_date: "" }, {});
    expect([body.from_date, body.to_date]).toEqual([null, null]);
  });
});

describe("the contract page (S081)", () => {
  it("shows rupees in Indian grouping, paise only when there are some", () => {
    expect(formatRupees("9809.00")).toBe("₹9,809");
    expect(formatRupees("9809.50")).toBe("₹9,809.50");
    expect(formatRupees("37837.00")).toBe("₹37,837");
    expect(formatRupees("99999999.99")).toBe("₹9,99,99,999.99");
    expect(formatRupees("0.00")).toBe("₹0");
  });

  it("says what the ticks cover, and leaves out an empty line", () => {
    const ticks = { covers_labour: 1, covers_parts: 0, covers_consumables: 1, covers_breakdown_calls: 1 };
    expect(coverageLines({ ...ticks, breakdown_calls_per_year: 4 })).toEqual([
      "Covered: labour, consumables, breakdown calls (4 a year).",
      "Not covered: spare parts.",
    ]);
    expect(coverageLines({ ...ticks, breakdown_calls_per_year: null })[0]).toBe("Covered: labour, consumables, breakdown calls.");
    expect(coverageLines({ covers_labour: 0, covers_parts: 0, covers_consumables: 0, covers_breakdown_calls: 0 })).toEqual([
      "Not covered: labour, spare parts, consumables, breakdown calls.",
    ]);
    expect(coverageLines({ covers_labour: 1, covers_parts: 1, covers_consumables: 1, covers_breakdown_calls: 1 })).toEqual([
      "Covered: labour, spare parts, consumables, breakdown calls.",
    ]);
  });

  it("gives the response time in hours, or null", () => {
    expect(responseText(24)).toBe("24 hours");
    expect(responseText(1)).toBe("1 hour");
    expect(responseText(null)).toBeNull();
  });

  it("names the other contract of an overlap, and the node when it is another", () => {
    const overlap = { contract_id: 2, title: "Atlas Copco AMC 2025–26", contract_type: "amc", from_date: "2025-04-01",
      to_date: "2026-03-31", on_code: null };
    expect(overlapText(overlap)).toBe("Also in another AMC: Atlas Copco AMC 2025–26, 01-04-2025 to 31-03-2026.");
    expect(overlapText({ ...overlap, contract_type: "on_call", on_code: "CMP001" })).toBe(
      "Also in another on-call contract: Atlas Copco AMC 2025–26, 01-04-2025 to 31-03-2026 (on CMP001).",
    );
    expect(overlapText({ ...overlap, contract_type: "warranty" })).toMatch(/^Also in another warranty: /);
  });

  it("sends a price only for a reader of prices on Add machine", () => {
    const form = { equipment_id: 7, price: " 9809.50 " };
    expect(lineBody(form, { creating: true, canReadCost: true })).toEqual({ equipment_id: 7, price: "9809.50" });
    expect(lineBody(form, { creating: true, canReadCost: false })).toEqual({ equipment_id: 7 });
    expect(lineBody({ equipment_id: 7, price: "" }, { creating: true, canReadCost: true })).toEqual({ equipment_id: 7, price: null });
  });

  it("sends the price alone on Edit price", () => {
    expect(lineBody({ equipment_id: 7, price: "28028" }, { creating: false, canReadCost: true })).toEqual({ price: "28028" });
    expect(lineBody({ equipment_id: 7, price: "" }, { creating: false, canReadCost: true })).toEqual({ price: null });
  });
});
