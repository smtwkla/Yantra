/**
 * Tests for utils/contractLabels.js (S080): the type and status labels, and the dialog's body, which leaves
 * the call-out number and the cost note out unless the chosen site's flags allow them.
 */

import { describe, expect, it } from "vitest";
import {
  CONTRACT_TYPES,
  STATUS_FILTERS,
  contractBody,
  contractTypeLabel,
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
