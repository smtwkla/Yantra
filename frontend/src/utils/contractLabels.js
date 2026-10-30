/**
 * Vendor contracts (S080, R02.1) — labels and the dialog's body, pure.  The rules live in the backend
 * (contracts_core.py); this file only names things and shapes what the dialog sends.
 */

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
