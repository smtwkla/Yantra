/**
 * Display labels for the equipment register — one vocabulary for every screen
 * (docs/steps/S003-equipment-screens/1-brief.md § 5.4–5.5; type events: S004; model events:
 * S012; meter events: S038; property events: S044). Pure: no imports.
 */

export const LEVEL_LABELS = {
  equipment: "Equipment",
  component_unit: "Component-unit",
  component: "Component",
};

// The lifecycle (S030; ISO 55000 life cycle). EN 13306 terms are in_service (operating or idle) and standby;
// out_of_use and scrapped are Yantra lifecycle stages.
export const LIFECYCLE_LABELS = {
  in_service: "In service",
  standby: "Standby",
  out_of_use: "Out of use",
  scrapped: "Scrapped",
};

export const LIFECYCLE_HELP = {
  in_service: "In use (EN 13306 operating or idle).",
  standby: "Ready to run, not running, e.g. a spare pump (EN 13306 standby).",
  out_of_use: "Laid up; no PM due (Yantra lifecycle stage).",
  scrapped: "Removed from the plant for good (Yantra lifecycle stage).",
};

export const LIFECYCLE_BADGE_CLASS = {
  in_service: "text-bg-success",
  standby: "text-bg-primary",
  out_of_use: "text-bg-secondary",
  scrapped: "text-bg-dark text-decoration-line-through",
};

export const CRITICALITY_LABELS = { A: "A", B: "B", C: "C" };

export const CRITICALITY_BADGE_CLASS = {
  // Shades of blue, strongest = most critical: a grade is a ranking, not an alarm, so no red/amber.
  A: "text-bg-primary",
  B: "bg-primary-subtle text-primary-emphasis border border-primary-subtle",
  C: "border border-primary text-primary",
};

/** S002 writes this literal for "no own grade" in criticality events. */
const INHERIT = "inherit";
/** S004 writes this literal for "no type" in type events (no type may be named it). */
const NO_TYPE = "none";

const label = (map, value) => map[value] ?? String(value);
const criticalityText = (value) => (value === INHERIT ? "Inherited" : label(CRITICALITY_LABELS, value));
const typeText = (value) => (value === NO_TYPE ? "None" : value);
const change = (name, from, to) => `${name}: ${from} → ${to}`;
// The new side without the old side's "<name>: ", so the meter or property is named once:
// after "Oil temperature: 10–60 °C", "Oil temperature: up to 55 °C" reads "up to 55 °C"
function secondSide(from, to) {
  // The shared start of both sides, cut back to the last ": ", so a name that holds ": " stays whole
  let shared = 0;
  while (shared < from.length && shared < to.length && from[shared] === to[shared]) shared++;
  const cut = from.slice(0, shared).lastIndexOf(": ");
  return cut < 0 ? to : to.slice(cut + 2);
}

/** One history event ({event, old_value, new_value}) in plain words. */
export function describeEvent(event) {
  const { old_value: oldValue, new_value: newValue } = event;
  switch (event.event) {
    case "created":
      return "Created";
    case "moved_unit":
    case "moved_parent":
      return change("Moved", oldValue, newValue);
    case "lifecycle":
      return change("Lifecycle", label(LIFECYCLE_LABELS, oldValue), label(LIFECYCLE_LABELS, newValue));
    case "criticality":
      return change("Criticality", criticalityText(oldValue), criticalityText(newValue));
    case "class":
      return change("Class", oldValue, newValue);
    case "type":
      return change("Type", typeText(oldValue), typeText(newValue));
    case "model":
      // A side without a model reads "No model", as the backend writes it (S033 § 5.4)
      return change("Model", oldValue, newValue);
    // Meters (S038 § 5.5): the backend writes "<meter>" or "<meter>: <limits>" on each side
    case "meter_added":
      return `Meter added: ${newValue}`;
    case "meter_removed":
      return `Meter removed: ${oldValue}`;
    case "meter_limits":
      return change("Meter limits", oldValue, secondSide(oldValue, newValue));
    // An item's own property value (S044 § 5.4): "<property>: <value>" on each side, the model's
    // value in force marked "(model)"
    case "property":
      return change("Property", oldValue, secondSide(oldValue, newValue));
    default:
      return String(event.event);
  }
}
