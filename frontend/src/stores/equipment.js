/**
 * Equipment screens' cache — which units the user may work at (GET /api/equipment/my-units).
 *
 * The masters API lists every unit to every role; the unit pickers combine that
 * list with this one so users are not offered units the server would refuse.
 * The cache lives for the tab: an access change by IT admin shows after a
 * reload, and a save at a revoked unit gets the API's 403 beside the field.
 */

import { computed, ref } from "vue";
import { apiGet } from "../api";

// {all_units: bool, unit_ids: [...], edit_unit_ids: [...] | null, reading_unit_ids: [...] | null}:
// unit_ids are where the user reads, edit_unit_ids where they may write and reading_unit_ids where
// they may log readings (null = every unit), per their site roles (S011, S040)
export const myUnits = ref(null);

/** True once loaded when the user reads no unit at all (the lists then show "no units assigned"). */
export const noUnits = computed(() => myUnits.value && !myUnits.value.all_units && myUnits.value.unit_ids.length === 0);

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

/**
 * The sites the readings sheet offers (S040 BR1-01, BR2-01): active sites with an active unit
 * where the user logs readings (every such unit when reading_unit_ids is null), as {id, code, name}.
 */
export function readingSites(allUnits, allSites, mine) {
  const logs = (u) => mine.reading_unit_ids === null || mine.reading_unit_ids.includes(u.id);
  const siteIds = new Set((allUnits ?? []).filter((u) => u.active && logs(u)).map((u) => u.site_id));
  return (allSites ?? []).filter((s) => s.active && siteIds.has(s.id)).map(({ id, code, name }) => ({ id, code, name }));
}
