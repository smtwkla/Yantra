/**
 * Display labels for the equipment register — one vocabulary for every screen
 * (docs/steps/S003-equipment-screens/1-brief.md § 5.4–5.5). Pure: no imports.
 */

export const LEVEL_LABELS = {
  equipment: "Equipment",
  component_unit: "Component-unit",
  component: "Component",
};

// EN 13306 terms are in_service (operating or idle) and standby; out_of_use and scrapped are Yantra life-cycle statuses.
export const STATUS_LABELS = {
  in_service: "In service",
  standby: "Standby",
  out_of_use: "Out of use",
  scrapped: "Scrapped",
};

export const STATUS_HELP = {
  in_service: "In use (EN 13306 operating or idle).",
  standby: "Ready to run, not running, e.g. a spare pump (EN 13306 standby).",
  out_of_use: "Laid up; no PM due (Yantra life-cycle status).",
  scrapped: "Removed from the plant for good (Yantra life-cycle status).",
};

export const STATUS_BADGE_CLASS = {
  in_service: "text-bg-success",
  standby: "text-bg-primary",
  out_of_use: "text-bg-secondary",
  scrapped: "text-bg-dark text-decoration-line-through",
};

export const CRITICALITY_LABELS = { A: "A", B: "B", C: "C" };

export const CRITICALITY_BADGE_CLASS = {
  A: "text-bg-danger",
  B: "text-bg-warning",
  C: "border border-secondary text-secondary",
};

/** S002 writes this literal for "no own grade" in criticality events. */
const INHERIT = "inherit";

const label = (map, value) => map[value] ?? String(value);
const criticalityText = (value) => (value === INHERIT ? "Inherited" : label(CRITICALITY_LABELS, value));
const change = (name, from, to) => `${name}: ${from} → ${to}`;

/** One history event ({event, old_value, new_value}) in plain words. */
export function describeEvent(event) {
  const { old_value: oldValue, new_value: newValue } = event;
  switch (event.event) {
    case "created":
      return "Created";
    case "moved_unit":
    case "moved_parent":
      return change("Moved", oldValue, newValue);
    case "status":
      return change("Status", label(STATUS_LABELS, oldValue), label(STATUS_LABELS, newValue));
    case "criticality":
      return change("Criticality", criticalityText(oldValue), criticalityText(newValue));
    case "class":
      return change("Class", oldValue, newValue);
    default:
      return String(event.event);
  }
}
