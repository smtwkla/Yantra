/**
 * Masters cache — sites, units, equipment classes and types, fetched once and shared.
 *
 * Lists include inactive records (consumers filter on `active`). After any
 * master is saved, call resetMasters() so the next ensureX() fetches fresh
 * data — a renamed site changes the full codes shown on its units.
 */

import { ref } from "vue";
import { apiGet } from "../api";

export const sites = ref(null);
export const units = ref(null);
export const equipmentClasses = ref(null);
export const equipmentTypes = ref(null);

async function fetchItems(path) {
  return (await apiGet(`/api/masters/${path}?include_inactive=1`)).items;
}

export async function ensureSites() {
  if (sites.value === null) sites.value = await fetchItems("sites");
  return sites.value;
}

export async function ensureUnits() {
  if (units.value === null) units.value = await fetchItems("units");
  return units.value;
}

export async function ensureEquipmentClasses() {
  if (equipmentClasses.value === null) equipmentClasses.value = await fetchItems("equipment-classes");
  return equipmentClasses.value;
}

export async function ensureEquipmentTypes() {
  if (equipmentTypes.value === null) equipmentTypes.value = await fetchItems("equipment-types");
  return equipmentTypes.value;
}

/** Id of the active default site, or null when none is set. Used to preselect pick-one site fields. */
export function defaultSiteId() {
  return (sites.value ?? []).find((s) => s.is_default && s.active)?.id ?? null;
}

export function resetMasters() {
  sites.value = null;
  units.value = null;
  equipmentClasses.value = null;
  equipmentTypes.value = null;
}
