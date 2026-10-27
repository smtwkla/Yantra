/**
 * Masters cache — sites, units, equipment categories (S063), classes and types, manufacturers and equipment
 * models (S012), trades, meter types (S037), failure modes, causes and maintenance actions (S016),
 * equipment properties (S043), fetched once and shared.
 *
 * Lists include inactive records (consumers filter on `active`). Pickers (the equipment
 * form, the move dialog) take the cached copy: a list a few minutes old is harmless there.
 * The Masters panels pass `{ refresh: true }` so the screen that shows and edits a list
 * always shows what is in the database now, including what another user just added.
 * After any master is saved, call resetMasters() so every other list is fetched fresh
 * on its next ensureX() — a renamed site changes the full codes shown on its units.
 */

import { ref } from "vue";
import { apiGet } from "../api";

export const sites = ref(null);
export const units = ref(null);
export const equipmentCategories = ref(null);
export const equipmentClasses = ref(null);
export const equipmentTypes = ref(null);
export const manufacturers = ref(null);
export const equipmentModels = ref(null);
export const trades = ref(null);
export const meterTypes = ref(null);
export const failureModes = ref(null);
export const failureCauses = ref(null);
export const maintenanceActions = ref(null);
export const properties = ref(null);

async function fetchItems(path) {
  return (await apiGet(`/api/masters/${path}?include_inactive=1`)).items;
}

// Fills `target` from the API when it is empty or `refresh` asks for it; returns the list
async function ensure(target, path, refresh) {
  if (refresh || target.value === null) target.value = await fetchItems(path);
  return target.value;
}

export function ensureSites({ refresh = false } = {}) {
  return ensure(sites, "sites", refresh);
}

export function ensureUnits({ refresh = false } = {}) {
  return ensure(units, "units", refresh);
}

export function ensureEquipmentCategories({ refresh = false } = {}) {
  return ensure(equipmentCategories, "equipment-categories", refresh);
}

export function ensureEquipmentClasses({ refresh = false } = {}) {
  return ensure(equipmentClasses, "equipment-classes", refresh);
}

export function ensureEquipmentTypes({ refresh = false } = {}) {
  return ensure(equipmentTypes, "equipment-types", refresh);
}

export function ensureManufacturers({ refresh = false } = {}) {
  return ensure(manufacturers, "manufacturers", refresh);
}

export function ensureModels({ refresh = false } = {}) {
  return ensure(equipmentModels, "equipment-models", refresh);
}

export function ensureTrades({ refresh = false } = {}) {
  return ensure(trades, "trades", refresh);
}

export function ensureMeterTypes({ refresh = false } = {}) {
  return ensure(meterTypes, "meter-types", refresh);
}

export function ensureFailureModes({ refresh = false } = {}) {
  return ensure(failureModes, "failure-modes", refresh);
}

export function ensureFailureCauses({ refresh = false } = {}) {
  return ensure(failureCauses, "failure-causes", refresh);
}

export function ensureMaintenanceActions({ refresh = false } = {}) {
  return ensure(maintenanceActions, "maintenance-actions", refresh);
}

export function ensureProperties({ refresh = false } = {}) {
  return ensure(properties, "properties", refresh);
}

/** Id of the active default site, or null when none is set. Used to preselect pick-one site fields. */
export function defaultSiteId() {
  return (sites.value ?? []).find((s) => s.is_default && s.active)?.id ?? null;
}

export function resetMasters() {
  sites.value = null;
  units.value = null;
  equipmentCategories.value = null;
  equipmentClasses.value = null;
  equipmentTypes.value = null;
  manufacturers.value = null;
  equipmentModels.value = null;
  trades.value = null;
  meterTypes.value = null;
  failureModes.value = null;
  failureCauses.value = null;
  maintenanceActions.value = null;
  properties.value = null;
}
