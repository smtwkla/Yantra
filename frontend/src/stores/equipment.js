/**
 * Equipment screens' cache — which units the user may work at (GET /api/equipment/my-units).
 *
 * The masters API lists every unit to every role; the unit pickers combine that
 * list with this one so users are not offered units the server would refuse.
 * The cache lives for the tab: a unit-access change by IT admin shows after a
 * reload, and a save at a revoked unit gets the API's 403 beside the field.
 */

import { ref } from "vue";
import { apiGet } from "../api";

export const myUnits = ref(null); // {all_units: bool, unit_ids: [...]}

export async function ensureMyUnits() {
  if (myUnits.value === null) myUnits.value = await apiGet("/api/equipment/my-units");
  return myUnits.value;
}

/** Units a create or move may target: active ones the user can work at. */
export function pickableUnits(allUnits, mine) {
  return (allUnits ?? []).filter((u) => u.active && (mine.all_units || mine.unit_ids.includes(u.id)));
}

/**
 * Units the list filter offers. Users with unit rows get their active units; users
 * with all-units access get every unit, since a deactivated unit may still hold
 * scrapped equipment.
 */
export function filterableUnits(allUnits, mine) {
  return mine.all_units ? (allUnits ?? []) : pickableUnits(allUnits, mine);
}
