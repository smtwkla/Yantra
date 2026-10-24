/**
 * Equipment properties (S035) — display only: the data-type names and the one-line summary of a
 * property in Masters and the picker. Values come formatted from the API (`display`, "62.5 kVA").
 */

export const DATA_TYPES = [
  { value: "number", label: "Number" },
  { value: "choice", label: "Choice" },
  { value: "text", label: "Text" },
  { value: "yes_no", label: "Yes / No" },
];

/** "Number", "Choice", "Text", "Yes / No"; an unknown type shows as sent. */
export function typeLabel(dataType) {
  return DATA_TYPES.find((t) => t.value === dataType)?.label ?? dataType;
}

/**
 * The Type column of Masters › Properties (§ 7.1) and the grey line of the picker:
 * "Number · kW", "Choice · 2 options" (the active ones), "Text", "Yes / No".
 */
export function typeSummary(property) {
  const label = typeLabel(property.data_type);
  if (property.data_type === "number") return property.unit ? `${label} · ${property.unit}` : label;
  if (property.data_type === "choice") {
    const active = (property.options ?? []).filter((o) => o.active).length;
    return `${label} · ${active} ${active === 1 ? "option" : "options"}`;
  }
  return label;
}

/** A value on the card: its display text, or "—" for no value. */
export function valueText(display) {
  return display ?? "—";
}
