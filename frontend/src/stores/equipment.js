/**
 * Equipment screens' cache — which units the user may work at (GET /api/equipment/my-units).
 *
 * The masters API lists every unit to every role; the unit pickers combine that
 * list with this one so users are not offered units the server would refuse.
 * The cache lives for the tab: an access change by IT admin shows after a
 * reload, and a save at a revoked unit gets the API's 403 beside the field.
 */

import { ref } from "vue";
import { apiGet } from "../api";

// {all_units: bool, unit_ids: [...], edit_unit_ids: [...] | null}: unit_ids are where the user
// reads, edit_unit_ids where they may write (null = every unit), per their site roles (S011)
export const myUnits = ref(null);

export async function ensureMyUnits() {
  if (myUnits.value === null) myUnits.value = await apiGet("/api/equipment/my-units");
  return myUnits.value;
}

/** Units a create or move may target: active ones where the user may edit equipment. */
export function pickableUnits(allUnits, mine) {
  return (allUnits ?? []).filter(
    (u) => u.active && (mine.edit_unit_ids === null || mine.edit_unit_ids.includes(u.id))
  );
}

/**
 * Units the list filter offers. Users with unit rows get their active units; users
 * with all-units access get every unit, since a deactivated unit may still hold
 * scrapped equipment.
 */
export function filterableUnits(allUnits, mine) {
  if (mine.all_units) return allUnits ?? [];
  return (allUnits ?? []).filter((u) => u.active && mine.unit_ids.includes(u.id));
}
