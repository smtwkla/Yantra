/**
 * Tests for utils/contractLabels.js (S080): the type and status labels, and the dialog's body, which leaves
 * the call-out number and the cost note out unless the reader's flags allow them.  S081: the rupees, the
 * coverage lines, the response time, the overlap line and the machine dialog's body, which never sends a price
 * for an editor without the key.  S082: the Under contract card's headline, call line, tel: link and via line, and
 * the list's Contract filter choices.  S085: the dialog's form from a contract, the renewal's form, its notice and
 * the chain line.  S086: the breakdown calls' lines (one call's figures, the total, the calls used), the vendor
 * warning and the ticket's contract line.  S087: a contract has no site; siteCodesText names its machines' sites.
 */

import { describe, expect, it } from "vitest";
import {
  ASK_THE_ENGINEER,
  CONTRACT_FILTER_CHOICES,
  CONTRACT_TYPES,
  EMPTY_CONTRACT_FORM,
  NO_CALLOUT_NUMBER,
  STATUS_FILTERS,
  callFiguresLine,
  callLine,
  callsTotalLine,
  callsUsedLine,
  cardHeadline,
  chainText,
  contractBody,
  contractForm,
  contractTypeLabel,
  coverageLines,
  formatRupees,
  lineBody,
  overlapText,
  renewalForm,
  renewalNotice,
  responseText,
  showsDoNotRepair,
  siteCodesText,
  statusBadgeClass,
  telHref,
  ticketContractLine,
  vendorWarningText,
  viaText,
} from "../src/utils/contractLabels";

const FORM = {
  vendor_id: 2, contract_type: "amc", title: "Atlas Copco AMC 2026–27", contract_number: "  ",
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
      vendor_id: 2, contract_type: "amc", title: "Atlas Copco AMC 2026–27",
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

describe("the Under contract card (S082)", () => {
  const IN_FORCE = { kind: "in_force", label: "In force", days: null };
  const ENDED = { kind: "ended", label: "Ended", days: null };
  const ITEM = {
    contract_type: "amc", vendor_name: "Atlas Copco", to_date: "2027-03-31", status: IN_FORCE,
    only_vendor_repairs: 0, can_read_callout: true, callout_number: "+91 00000 00000",
  };

  it("names each type in force and ended", () => {
    const headlines = (status, toDate) => CONTRACT_TYPES.map(({ value }) => (
      cardHeadline({ ...ITEM, contract_type: value, status, to_date: toDate })
    ));
    expect(headlines(IN_FORCE, "2027-03-31")).toEqual([
      "Under AMC with Atlas Copco until 31-03-2027",
      "Under CMC with Atlas Copco until 31-03-2027",
      "Under warranty with Atlas Copco until 31-03-2027",
      "On-call contract with Atlas Copco until 31-03-2027",
    ]);
    expect(headlines(ENDED, "2026-03-31")).toEqual([
      "AMC with Atlas Copco ended on 31-03-2026.",
      "CMC with Atlas Copco ended on 31-03-2026.",
      "Warranty with Atlas Copco ended on 31-03-2026.",
      "On-call contract with Atlas Copco ended on 31-03-2026.",
    ]);
  });

  it("shows the Do not repair warning only on a contract not ended with the tick", () => {
    expect(showsDoNotRepair({ ...ITEM, only_vendor_repairs: 1 })).toBe(true);
    expect(showsDoNotRepair({ ...ITEM, only_vendor_repairs: 1, status: ENDED })).toBe(false);
    expect(showsDoNotRepair(ITEM)).toBe(false);
  });

  it("gives the call line by who reads it", () => {
    expect(callLine(ITEM)).toEqual({ text: "Call-out number:", number: "+91 00000 00000" });
    expect(callLine({ ...ITEM, callout_number: null })).toEqual({ text: NO_CALLOUT_NUMBER, number: null });
    expect(NO_CALLOUT_NUMBER).toBe("No call-out number on the contract.");
    const reader = { ...ITEM, can_read_callout: false, callout_number: undefined };
    expect(callLine(reader)).toEqual({ text: ASK_THE_ENGINEER, number: null });
    expect(ASK_THE_ENGINEER).toBe("To call the vendor, ask the engineer.");
    // The warning already says to call the engineer; the engineer keeps the number
    expect(callLine({ ...reader, only_vendor_repairs: 1 })).toBeNull();
    expect(callLine({ ...ITEM, only_vendor_repairs: 1 }).number).toBe("+91 00000 00000");
    expect(callLine({ ...ITEM, status: ENDED })).toBeNull();
  });

  it("makes a tel: link of the digits and a leading plus", () => {
    expect(telHref("+91 00000 00000")).toBe("tel:+910000000000");
    expect(telHref("0422-000 000")).toBe("tel:0422000000");
    expect(telHref(" +91 (0422) 000-000 ")).toBe("tel:+910422000000");
  });

  it("names the ancestor whose line brings the contract", () => {
    expect(viaText({ code: "CMP001", name: "Screw compressor 1", level: "equipment" })).toBe(
      "Through CMP001 — Screw compressor 1, this part's machine.",
    );
    expect(viaText({ code: "CU001", name: "Gearbox", level: "component_unit" })).toBe(
      "Through CU001 — Gearbox, this part's component-unit.",
    );
  });

  it("offers the list's Contract filter", () => {
    expect(CONTRACT_FILTER_CHOICES).toEqual([
      ["", "Any contract status"],
      ["under", "Under contract"],
      ["not_under", "Not under contract"],
    ]);
  });
});

describe("the renewal (S085)", () => {
  // A detail as the API sends it to an engineer: no cost note, a call-out number, ticks as 0/1
  const DETAIL = {
    id: 7, site_codes: ["SMTW"], vendor_id: 2, contract_type: "amc", title: "Atlas Copco AMC 2026–27",
    contract_number: "AC/17", from_date: "2026-04-01", to_date: "2027-03-31", covers_labour: 1, covers_parts: 0,
    covers_consumables: 0, covers_breakdown_calls: 1, breakdown_calls_per_year: 4, covered_text: null,
    not_covered_text: "Filters", pm_visits_per_year: 4, response_hours: null, only_vendor_repairs: 1,
    callout_number: "+91 00000 00000", notes: null, active: 1,
    renewal: { from_date: "2027-04-01", to_date: "2028-03-31", machines: [], skipped: [] },
  };

  it("contractForm fills every field of the empty form", () => {
    const form = contractForm(DETAIL);
    expect(Object.keys(form).sort()).toEqual(["contract_type", ...Object.keys(EMPTY_CONTRACT_FORM)].sort());
    expect(form.covers_labour).toBe(true);
    expect(form.covers_parts).toBe(false);
    expect(form.covered_text).toBe("");
    expect(form.cost_note).toBe(""); // absent for this reader
    expect(form.vendor_id).toBe(2);
  });

  it("renewalForm takes the proposed dates and starts the cost note empty", () => {
    const form = renewalForm({ ...DETAIL, cost_note: "Rs 37,837 a year" });
    expect([form.from_date, form.to_date]).toEqual(["2027-04-01", "2028-03-31"]);
    expect(form.cost_note).toBe("");
    expect(form.title).toBe("Atlas Copco AMC 2026–27");
    expect(form.callout_number).toBe("+91 00000 00000");
    expect("site_id" in form).toBe(false);
    const late = renewalForm({ ...DETAIL, renewal: { from_date: null, to_date: null, machines: [], skipped: [] } });
    expect([late.from_date, late.to_date]).toEqual(["", ""]);
    const { callout_number: _gone, ...noCallout } = DETAIL;
    expect(renewalForm(noCallout).callout_number).toBe("");
  });

  it("renewalNotice names the machines copied and skipped", () => {
    const renewal = {
      machines: [{ equipment_id: 1, code: "CMP001" }, { equipment_id: 2, code: "CMP002" }],
      skipped: [{ equipment_id: 4, code: "CMP004", reason: "scrapped" }],
    };
    expect(renewalNotice({ ...renewal, skipped: [] }, false)).toBe(
      "The new contract starts the day after this one ends. 2 machines are copied: CMP001, CMP002. Prices start" +
        " empty: the managers enter them on the new contract. Documents stay on this contract."
    );
    expect(renewalNotice(renewal, true)).toBe(
      "The new contract starts the day after this one ends. 2 machines are copied: CMP001, CMP002. Not copied:" +
        " CMP004 (scrapped). Prices start empty: enter them on the new contract. Documents stay on this contract."
    );
    expect(renewalNotice({ machines: [renewal.machines[0]], skipped: [] }, true)).toContain(
      "1 machine is copied: CMP001."
    );
    expect(renewalNotice({ machines: [], skipped: [] }, false)).toBe(
      "The new contract starts the day after this one ends. This contract has no machines; the new one starts with" +
        " none. Documents stay on this contract."
    );
    expect(renewalNotice({ machines: [], skipped: renewal.skipped }, false)).toBe(
      "The new contract starts the day after this one ends. No machine is copied: CMP004 (scrapped)." +
        " Documents stay on this contract."
    );
  });

  it("chainText gives the period and marks an inactive contract", () => {
    const link = { id: 8, title: "Atlas Copco AMC 2027–28", from_date: "2027-04-01", to_date: "2028-03-31", active: true };
    expect(chainText(link)).toBe(" · 01-04-2027 to 31-03-2028");
    expect(chainText({ ...link, active: false })).toBe(" · 01-04-2027 to 31-03-2028 (inactive)");
  });

  it("the renewal body sends the gated fields only with their flags", () => {
    const form = renewalForm(DETAIL);
    const body = contractBody(form, { can_read_callout: true, can_read_cost: false });
    expect(body.callout_number).toBe("+91 00000 00000");
    expect("cost_note" in body).toBe(false);
    expect("callout_number" in contractBody(form, { can_read_callout: false, can_read_cost: false })).toBe(false);
  });
});

describe("breakdown calls and the ticket's contract line (S086)", () => {
  it("callFiguresLine gives the downtime and the wait on the vendor, leaving out null or 0", () => {
    expect(callFiguresLine({ downtime_minutes: 330, vendor_waiting_minutes: 120 })).toBe(
      "Down 5 h 30 min · waited on the vendor 2 h",
    );
    expect(callFiguresLine({ downtime_minutes: 45, vendor_waiting_minutes: null })).toBe("Down 45 min");
    expect(callFiguresLine({ downtime_minutes: 0, vendor_waiting_minutes: 30 })).toBe("Waited on the vendor 30 min");
    expect(callFiguresLine({ downtime_minutes: 0, vendor_waiting_minutes: 0 })).toBeNull();
    expect(callFiguresLine({ downtime_minutes: null, vendor_waiting_minutes: null })).toBeNull();
  });

  it("callsTotalLine counts the calls and sums the minutes", () => {
    expect(callsTotalLine({ count: 3, downtime_minutes: 320, vendor_waiting_minutes: 120 })).toBe(
      "3 calls · down 5 h 20 min · waited on the vendor 2 h",
    );
    expect(callsTotalLine({ count: 1, downtime_minutes: 0, vendor_waiting_minutes: 0 })).toBe("1 call · no downtime");
    expect(callsTotalLine({ count: 2, downtime_minutes: 90, vendor_waiting_minutes: 0 })).toBe("2 calls · down 1 h 30 min");
  });

  it("callsUsedLine gives the three texts, or null", () => {
    expect(callsUsedLine({ count: 3, agreed: 4, over: false, per_year_only: false })).toBe("3 of 4 calls used this period.");
    expect(callsUsedLine({ count: 5, agreed: 4, over: true, per_year_only: false })).toBe(
      "5 of 4 calls used — more than agreed.",
    );
    expect(callsUsedLine({ count: 5, agreed: 4, over: true, per_year_only: true })).toBe(
      "5 calls in this period · 4 a year agreed.",
    );
    expect(callsUsedLine({ count: 1, agreed: 4, over: false, per_year_only: true })).toBe(
      "1 call in this period · 4 a year agreed.",
    );
    expect(callsUsedLine(null)).toBeNull();
  });

  it("vendorWarningText names the vendor, the sites and what to do", () => {
    expect(vendorWarningText("no_linked", "Atlas Copco", [])).toBe(
      "No Team record is linked to Atlas Copco. Link the vendor's technician, or a record such as 'Atlas Copco" +
        " service', in Masters › Team.",
    );
    expect(vendorWarningText("no_assignable", "Atlas Copco", ["SMTW"])).toBe(
      "No Team record of Atlas Copco can be assigned at SMTW. Give one a Technician role there in Masters › Team.",
    );
    expect(vendorWarningText("no_assignable", "VP Power", ["BRICKS", "SMTW-KP"])).toBe(
      "No Team record of VP Power can be assigned at BRICKS, SMTW-KP. Give one a Technician role there in"
        + " Masters › Team.",
    );
    expect(vendorWarningText(null, "Atlas Copco", [])).toBeNull();
  });

  it("siteCodesText names the machines' sites, or a dash for none (S087)", () => {
    expect(siteCodesText(["BRICKS", "SMTW"])).toBe("BRICKS, SMTW");
    expect(siteCodesText(["SMTW"])).toBe("SMTW");
    expect(siteCodesText([])).toBe("—");
    expect(siteCodesText(undefined)).toBe("—");
  });

  it("ticketContractLine adds the response time and the breakdown calls to S082's headline", () => {
    const item = {
      contract_type: "amc", vendor_name: "Atlas Copco", to_date: "2027-03-31",
      status: { kind: "in_force", label: "In force", days: null }, response_hours: 24, covers_breakdown_calls: 1,
    };
    const whole = (it) => {
      const line = ticketContractLine(it);
      return line.headline + line.details;
    };
    expect(whole(item)).toBe("Under AMC with Atlas Copco until 31-03-2027 · response 24 hours · breakdown calls included");
    expect(ticketContractLine(item).headline).toBe("Under AMC with Atlas Copco until 31-03-2027");
    expect(whole({ ...item, response_hours: null })).toBe("Under AMC with Atlas Copco until 31-03-2027 · breakdown calls included");
    expect(whole({ ...item, covers_breakdown_calls: 0 })).toBe("Under AMC with Atlas Copco until 31-03-2027 · response 24 hours");
    expect(whole({ ...item, response_hours: null, covers_breakdown_calls: 0 })).toBe("Under AMC with Atlas Copco until 31-03-2027");
  });
});
