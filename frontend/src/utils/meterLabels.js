/**
 * Display words for meters — one vocabulary for every screen (S037 § 9.1, S038 § 1, § 3). Pure:
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
