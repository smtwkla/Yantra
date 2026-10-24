/**
 * Display words for meters — one vocabulary for every screen (S037 § 9.1, S038 § 1, § 3; readings: S039). Pure:
 * no imports. The limits wording ("Limits: 10–60 °C") comes from the API (meters_core), so it
 * lives once; here are the kinds, where a node's meter comes from, and a Yes / No meter's
 * expected answer.
 */

export const KIND_LABELS = {
  counter: "Counter",
  gauge: "Gauge",
  amount: "Amount per period",
  yes_no: "Yes / No",
};

// Where a node's meter comes from (S038 § 1.2)
export const SOURCE_LABELS = {
  model: "From the model",
  node: "This machine only",
};

const kindLabel = (kind) => KIND_LABELS[kind] ?? String(kind);

/** A Yes / No meter's good answer, from its type: "Expected: Yes" / "Expected: No"; null otherwise. */
export function expectedAnswerText(meterType) {
  if (meterType.kind !== "yes_no") return null;
  return `Expected: ${meterType.expected_answer === "yes" ? "Yes" : "No"}`;
}

/** What a good reading is, by kind (BR3-01): a gauge's limits text, a Yes / No meter's expected answer, else null. */
export function goodReadingText(meter) {
  return meter.limits_text ?? expectedAnswerText(meter.meter_type);
}

/** A meter type in a select: "Oil temperature (°C, Gauge)", "Oil level above min (Yes / No)". */
export function meterTypeOption(meterType) {
  const kind = kindLabel(meterType.kind);
  return `${meterType.name} (${meterType.unit ? `${meterType.unit}, ${kind}` : kind})`;
}

/**
 * The limits a meter dialog sends: both sides for a gauge, an empty box as null (no limit on
 * that side); nothing for other kinds, which have no limits.
 */
export function limitsBody(form, meterType) {
  if (meterType?.kind !== "gauge") return {};
  const limit = (text) => (String(text ?? "").trim() === "" ? null : String(text).trim());
  return { min_value: limit(form.min_value), max_value: limit(form.max_value) };
}

/** The type's unit and kind on one line, for a list row: "°C · Gauge", "Yes / No". */
export function unitAndKind(meterType) {
  const kind = kindLabel(meterType.kind);
  return meterType.unit ? `${meterType.unit} · ${kind}` : kind;
}

// ---------------------------------------------------------------------------
// Readings (S039)
// ---------------------------------------------------------------------------

/** The words of a reading's marks (§ 1.3): a gauge outside its limits, an unexpected answer, a reset. */
export const LIMIT_STATE_LABELS = { high: "High", low: "Low", not_ok: "Not OK" };
export const RESET_LABEL = "Reset";

const YES_NO_WORDS = { yes: "Yes", no: "No" };

/**
 * A reading as the screens show it: the type's decimals with Indian grouping (U4) and the unit,
 * "12,345.6 h", "420 pcs"; a Yes / No reading as "Yes" / "No". The API's value is a decimal
 * string; display only, so a double is exact enough.
 */
export function formatReading(value, meterType) {
  if (meterType.kind === "yes_no") return YES_NO_WORDS[value] ?? String(value);
  const digits = meterType.decimals;
  const number = Number(value).toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return `${number} ${meterType.unit}`;
}

/** The badges of one reading, in the order the history shows them: High / Low / Not OK, then Reset. */
export function readingBadges(reading) {
  const badges = [];
  if (reading.limit_state) badges.push(LIMIT_STATE_LABELS[reading.limit_state] ?? reading.limit_state);
  if (reading.is_reset) badges.push(RESET_LABEL);
  return badges;
}

/**
 * What the card says after a save (BR2-09): a gauge outside its limits, or an answer other than
 * the expected one; null for every other reading (the dialog just closes).
 */
export function savedMessage(meter, reading) {
  const { unit, expected_answer: expected } = meter.meter_type;
  // A side's limit can be gone by now (cleared while the dialog was open): then name no value.
  if (reading.limit_state === "high") {
    return meter.max_value == null ? "Saved. Above the limit." : `Saved. Above the limit of ${meter.max_value} ${unit}.`;
  }
  if (reading.limit_state === "low") {
    return meter.min_value == null ? "Saved. Below the limit." : `Saved. Below the limit of ${meter.min_value} ${unit}.`;
  }
  if (reading.limit_state === "not_ok") return `Saved. Not OK: the expected answer is ${YES_NO_WORDS[expected]}.`;
  return null;
}
