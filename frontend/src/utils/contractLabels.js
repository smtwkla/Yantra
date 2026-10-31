/**
 * Vendor contracts (S080, R02.1; S081, R02.2: the machines and their prices; S082: the Under contract card and the
 * list's Contract filter) — labels and the dialogs' bodies, pure.  The rules live in the backend (contracts_core.py); this file only names things and shapes what the
 * dialogs send.
 */
import { formatDate } from "./datetime";

// The four types (contracts.contract_type), AMC first: the dialog's default and the common case
export const CONTRACT_TYPES = [
  { value: "amc", label: "AMC", help: "labour and visits" },
  { value: "cmc", label: "CMC", help: "parts included" },
  { value: "warranty", label: "Warranty", help: "the maker's guarantee" },
  { value: "on_call", label: "On call", help: "paid per call" },
];

/** "amc" → "AMC"; an unknown value is shown as it is. */
export function contractTypeLabel(value) {
  return CONTRACT_TYPES.find((t) => t.value === value)?.label ?? value;
}

// The list's Status filter (contracts_core.STATUS_FILTERS), the default first
export const STATUS_FILTERS = [
  { value: "not_ended", label: "Not ended" },
  { value: "in_force", label: "In force" },
  { value: "ending", label: "Ending within 60 days" },
  { value: "upcoming", label: "Starts later" },
  { value: "ended", label: "Ended" },
  { value: "all", label: "All" },
];

const BADGES = {
  in_force: "text-bg-success",
  ending: "text-bg-warning",
  ended: "text-bg-secondary",
  upcoming: "text-bg-info",
};

/** The badge class of a status kind (contracts_core.contract_status). */
export function statusBadgeClass(kind) {
  return BADGES[kind] ?? "text-bg-light";
}

const OPTIONAL_TEXTS = ["contract_number", "covered_text", "not_covered_text", "notes"];
const NUMBERS = ["pm_visits_per_year", "response_hours", "breakdown_calls_per_year"];
const TICKS = ["covers_labour", "covers_parts", "covers_consumables", "covers_breakdown_calls", "only_vendor_repairs"];

/** "" or null → null; a number typed → the number (a wrong one is refused by the backend with its message). */
function numberOrNull(value) {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  return Number(value);
}

function textOrNull(value) {
  const text = (value ?? "").trim();
  return text || null;
}

/**
 * The dialog's form → the request body (S080 § 5.7).  ``site`` is the chosen site's row of the list's
 * ``sites`` ({can_read_callout, can_read_cost}): the call-out number and the cost note are left out unless
 * its flag allows them, so a save by an editor without the key never touches them.  Calls per year is null
 * while its tick is off.
 */
export function contractBody(form, site) {
  const body = {
    site_id: form.site_id,
    vendor_id: form.vendor_id,
    contract_type: form.contract_type,
    title: form.title,
    from_date: form.from_date || null,
    to_date: form.to_date || null,
  };
  for (const field of OPTIONAL_TEXTS) body[field] = textOrNull(form[field]);
  for (const field of NUMBERS) body[field] = numberOrNull(form[field]);
  for (const field of TICKS) body[field] = Boolean(form[field]);
  if (!body.covers_breakdown_calls) body.breakdown_calls_per_year = null;
  if (site?.can_read_callout) body.callout_number = textOrNull(form.callout_number);
  if (site?.can_read_cost) body.cost_note = textOrNull(form.cost_note);
  return body;
}

// The dialog's empty form (S080 § 5.7), apart from the site and the type: one copy for add, edit and renew (S085)
export const EMPTY_CONTRACT_FORM = Object.freeze({
  vendor_id: null, title: "", contract_number: "", from_date: "", to_date: "", covers_labour: false,
  covers_parts: false, covers_consumables: false, covers_breakdown_calls: false, breakdown_calls_per_year: "",
  covered_text: "", not_covered_text: "", pm_visits_per_year: "", response_hours: "", only_vendor_repairs: false,
  callout_number: "", cost_note: "", notes: "",
});

/** A contract from the API → the dialog's form: a tick as a boolean, an empty value as "" (a field the reader may
 * not see, absent from the answer, is "" too and is never sent). */
export function contractForm(contract) {
  const form = { site_id: contract.site_id, contract_type: contract.contract_type };
  for (const field of Object.keys(EMPTY_CONTRACT_FORM)) {
    const value = contract[field];
    form[field] = typeof EMPTY_CONTRACT_FORM[field] === "boolean" ? Boolean(value) : (value ?? "");
  }
  form.vendor_id = contract.vendor_id;
  return form;
}

// ---------------------------------------------------------------------------
// Renewal (S085 § 5.7)
// ---------------------------------------------------------------------------

/** The renew dialog's form from the contract's detail: its terms, the proposed dates (``renewal``; "" past 2099)
 * and an empty cost note (each period's note is its own, E4). */
export function renewalForm(contract) {
  return {
    ...contractForm(contract),
    from_date: contract.renewal?.from_date ?? "",
    to_date: contract.renewal?.to_date ?? "",
    cost_note: "",
  };
}

/** The renew dialog's notice: what is copied and what is not. ``renewal`` is the detail's offer
 * ({machines, skipped}); a reader of prices enters them, others are told who does. */
export function renewalNotice(renewal, canReadCost, siteCode) {
  const codes = (lines) => lines.map((line) => line.code).join(", ");
  const skippedText = (lines) => lines.map((line) => `${line.code} (${line.reason})`).join(", ");
  const { machines, skipped } = renewal;
  const sentences = ["The new contract starts the day after this one ends."];
  if (machines.length === 0 && skipped.length === 0) {
    sentences.push("This contract has no machines; the new one starts with none.");
  } else if (machines.length === 0) {
    sentences.push(`No machine is copied: ${skippedText(skipped)}.`);
  } else {
    const count = machines.length === 1 ? "1 machine is copied" : `${machines.length} machines are copied`;
    sentences.push(`${count}: ${codes(machines)}.`);
  }
  if (skipped.length && machines.length) {
    sentences.push(`Not copied: ${skippedText(skipped)}.`);
  }
  if (machines.length) {
    sentences.push(canReadCost
      ? "Prices start empty: enter them on the new contract."
      : `Prices start empty: the managers of ${siteCode} enter them on the new contract.`);
  }
  sentences.push("Documents stay on this contract.");
  return sentences.join(" ");
}

/** A chain line's text after the linked title: " · 01-04-2026 to 31-03-2027", and " (inactive)" for an inactive
 * contract. */
export function chainText(link) {
  return ` · ${formatDate(link.from_date)} to ${formatDate(link.to_date)}${link.active ? "" : " (inactive)"}`;
}

// ---------------------------------------------------------------------------
// The contract page and its machines (S081 § 5.7)
// ---------------------------------------------------------------------------

/** A price from the API ("9809.00", a DECIMAL as a string) → "₹9,809"; paise only when there are some
 * ("₹9,809.50"); Indian grouping ("₹9,99,99,999.99"). */
export function formatRupees(value) {
  const number = Number(value);
  const digits = Number.isInteger(number) ? 0 : 2;
  return `₹${number.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
}

/** What the four ticks say, as at most two lines: "Covered: labour, consumables, breakdown calls (4 a year)." and
 * "Not covered: spare parts."; a line with no item is left out. */
export function coverageLines(contract) {
  const calls = contract.breakdown_calls_per_year;
  const items = [
    [contract.covers_labour, "labour"],
    [contract.covers_parts, "spare parts"],
    [contract.covers_consumables, "consumables"],
    [contract.covers_breakdown_calls, calls ? `breakdown calls (${calls} a year)` : "breakdown calls"],
  ];
  const covered = items.filter(([tick]) => tick).map(([, text]) => text);
  // An unticked item never has a number of calls (contracts_core.breakdown_calls_error)
  const notCovered = items.filter(([tick]) => !tick).map(([, text]) => text);
  const lines = [];
  if (covered.length) lines.push(`Covered: ${covered.join(", ")}.`);
  if (notCovered.length) lines.push(`Not covered: ${notCovered.join(", ")}.`);
  return lines;
}

/** The response time: 24 → "24 hours", 1 → "1 hour", none → null (the page shows "—"). */
export function responseText(hours) {
  if (hours === null || hours === undefined) return null;
  return hours === 1 ? "1 hour" : `${hours} hours`;
}

// The type as a noun in a sentence ("Also in another warranty: …")
const TYPE_NOUNS = { amc: "AMC", cmc: "CMC", warranty: "warranty", on_call: "on-call contract" };

/** One overlap of a machine line (contracts._overlaps): "Also in another AMC: Atlas Copco AMC 2025–26, 01-04-2025
 * to 31-03-2026." and, when the other line is on the machine above or a part, " (on CMP001)" before the stop. */
export function overlapText(overlap) {
  const noun = TYPE_NOUNS[overlap.contract_type] ?? overlap.contract_type;
  const on = overlap.on_code ? ` (on ${overlap.on_code})` : "";
  return `Also in another ${noun}: ${overlap.title}, ${formatDate(overlap.from_date)} to ${formatDate(overlap.to_date)}${on}.`;
}

// ---------------------------------------------------------------------------
// Under contract on the machine (S082 § 5.3, § 5.4)
// ---------------------------------------------------------------------------

// The equipment list's Contract filter (contracts_core.COVERAGE_FILTERS), "" = no filter
export const CONTRACT_FILTER_CHOICES = [
  ["", "Any contract status"],
  ["under", "Under contract"],
  ["not_under", "Not under contract"],
];

export const DO_NOT_REPAIR = "Do not repair. Call the engineer; the vendor repairs this machine.";
export const ASK_THE_ENGINEER = "To call the vendor, ask the engineer.";
export const NO_CALLOUT_NUMBER = "No call-out number on the contract.";

// The type in the card's headline: in force ("Under AMC with …"), and ended, at the start of a sentence
const IN_FORCE_TEXT = { amc: "Under AMC", cmc: "Under CMC", warranty: "Under warranty", on_call: "On-call contract" };
const ENDED_TEXT = { amc: "AMC", cmc: "CMC", warranty: "Warranty", on_call: "On-call contract" };

export const isEnded = (item) => item.status?.kind === "ended";

/** The D9 warning shows on a card item not ended whose contract lets only the vendor repair. */
export function showsDoNotRepair(item) {
  return !isEnded(item) && Boolean(item.only_vendor_repairs);
}

/** "Under AMC with Atlas Copco until 31-03-2027"; ended: "AMC with Atlas Copco ended on 31-03-2026." */
export function cardHeadline(item) {
  const type = item.contract_type;
  if (isEnded(item)) return `${ENDED_TEXT[type] ?? type} with ${item.vendor_name} ended on ${formatDate(item.to_date)}.`;
  return `${IN_FORCE_TEXT[type] ?? type} with ${item.vendor_name} until ${formatDate(item.to_date)}`;
}

/** The ancestor whose line brings the contract: "Through CMP001 — Screw compressor 1, this part's machine." */
export function viaText(via) {
  const level = via.level === "component_unit" ? "component-unit" : "machine";
  return `Through ${via.code} — ${via.name}, this part's ${level}.`;
}

/**
 * The call line of a card item, or null when there is none: an ended contract has none, and a reader without
 * the number gets none when the D9 warning already says to call the engineer. ``{text, number}``: a reader of
 * the call-out number gets "Call-out number:" and the number (or the text that there is none); anyone else
 * "To call the vendor, ask the engineer." (D10).
 */
export function callLine(item) {
  if (isEnded(item)) return null;
  if (!item.can_read_callout) return showsDoNotRepair(item) ? null : { text: ASK_THE_ENGINEER, number: null };
  if (!item.callout_number) return { text: NO_CALLOUT_NUMBER, number: null };
  return { text: "Call-out number:", number: item.callout_number };
}

/** A tap-to-call link: "tel:" and the number with every character but the digits and a leading "+" removed. */
export function telHref(number) {
  const text = String(number).trim();
  return `tel:${text.startsWith("+") ? "+" : ""}${text.replace(/\D/g, "")}`;
}

/**
 * The machine dialog's form → the request body (S081 § 5.7). On *Add machine* the machine and, only for a reader
 * of prices, the price ("" → null); a price is never sent by an editor without the key. On *Edit price* the price
 * alone (the path names the machine).
 */
export function lineBody(form, { creating, canReadCost }) {
  const text = String(form.price ?? "").trim();
  const price = text === "" ? null : text;
  if (!creating) return { price };
  const body = { equipment_id: form.equipment_id };
  if (canReadCost) body.price = price;
  return body;
}
