<script setup>
/**
 * Masters — sites, units, equipment classes and types, trades, Team with each person's
 * roles per site (docs/steps/S001-basic-masters, S004, S010, S011; S011 A1 moved unit access into Team).
 * The level-2 toolbar switches sections as local state, not routes.
 */
import { computed, ref } from "vue";
import ModuleToolbar from "../components/layout/ModuleToolbar.vue";
import { userPermissions } from "../stores/auth";
import { canSeeNavItem } from "../stores/navigation";
import EquipmentClassesPanel from "./masters/EquipmentClassesPanel.vue";
import EquipmentTypesPanel from "./masters/EquipmentTypesPanel.vue";
import SitesPanel from "./masters/SitesPanel.vue";
import PeoplePanel from "./masters/PeoplePanel.vue";
import TradesPanel from "./masters/TradesPanel.vue";
import UnitsPanel from "./masters/UnitsPanel.vue";

const sections = [
  { key: "sites", icon: "fa-solid fa-location-dot", label: "Sites", perm: "masters:read" },
  { key: "units", icon: "fa-solid fa-warehouse", label: "Units", perm: "masters:read" },
  { key: "classes", icon: "fa-solid fa-shapes", label: "Equip Class", perm: "masters:read" },
  { key: "types", icon: "fa-solid fa-sitemap", label: "Equip Type", perm: "masters:read" },
  { key: "trades", icon: "fa-solid fa-screwdriver-wrench", label: "Trades", perm: "masters:read" },
  { key: "people", icon: "fa-solid fa-people-group", label: "Team", perm: "masters:read" },
];
const panels = {
  sites: SitesPanel,
  units: UnitsPanel,
  classes: EquipmentClassesPanel,
  types: EquipmentTypesPanel,
  trades: TradesPanel,
  people: PeoplePanel,
};

const chosen = ref("sites");
// Fall back to the first visible section if the chosen one is not permitted (e.g. permissions arrive late)
const active = computed(() => {
  const visible = sections.filter((s) => canSeeNavItem(s, userPermissions.value));
  return visible.some((s) => s.key === chosen.value) ? chosen.value : (visible[0]?.key ?? "sites");
});
</script>

<template>
  <div class="py-3">
    <ModuleToolbar :sections="sections" :active="active" @select="chosen = $event" />
    <component :is="panels[active]" :key="active" />
  </div>
</template>
