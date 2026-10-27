/**
 * Equipment properties (S043) — display only: the data-type names and the one-line summary of a
 * property in Masters and the picker. Values come formatted from the API (`display`, "62.5 kVA").
 * S061: the Location type, and the texts of "Use my current location" (one browser reading; the
 * backend checks and rounds the value).
 */

export const DATA_TYPES = [
  { value: "number", label: "Number" },
  { value: "choice", label: "Choice" },
  { value: "text", label: "Text" },
  { value: "yes_no", label: "Yes / No" },
  { value: "geo", label: "Location" },
];

/** "Number", "Choice", "Text", "Yes / No", "Location"; an unknown type shows as sent. */
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

// Above this accuracy (metres) the reading is rough: the user is told to go into the open (S061 D3)
export const ROUGH_ACCURACY_M = 50;

/** A browser position as the Location input takes it: "11.016823, 76.955812" (6 decimals, about 10 cm). */
export function positionText(coords) {
  return `${coords.latitude.toFixed(6)}, ${coords.longitude.toFixed(6)}`;
}

/** The line under the Location input after a reading: "About 12 m accurate", or the rough-location advice. */
export function accuracyText(accuracy) {
  const metres = Math.round(accuracy);
  if (metres > ROUGH_ACCURACY_M) return `Rough location (about ${metres} m). Go into the open, then try again.`;
  return `About ${metres} m accurate`;
}

// GeolocationPositionError.PERMISSION_DENIED
const PERMISSION_DENIED = 1;

/** The message under the Location input when the browser gives no position (S061 D3). */
export function locationErrorText(code) {
  if (code === PERMISSION_DENIED) {
    return "Location is blocked for Yantra in this browser. Allow it in the browser's settings, or type the location";
  }
  return "The phone could not find its location. Try again in the open, or type the location";
}
