<script setup>
/**
 * Masters — sites, units, equipment classes and types, unit access (docs/steps/S001-basic-masters, S004).
 * The level-2 toolbar switches sections as local state, not routes.
 */
import { computed, ref } from "vue";
import ModuleToolbar from "../components/layout/ModuleToolbar.vue";
import { userPermissions } from "../stores/auth";
import { canSeeNavItem } from "../stores/navigation";
import EquipmentClassesPanel from "./masters/EquipmentClassesPanel.vue";
import EquipmentTypesPanel from "./masters/EquipmentTypesPanel.vue";
import SitesPanel from "./masters/SitesPanel.vue";
import UnitsPanel from "./masters/UnitsPanel.vue";
import UserUnitsPanel from "./masters/UserUnitsPanel.vue";

const sections = [
  { key: "sites", icon: "fa-solid fa-location-dot", label: "Sites", perm: "masters:read" },
  { key: "units", icon: "fa-solid fa-warehouse", label: "Units", perm: "masters:read" },
  { key: "classes", icon: "fa-solid fa-shapes", label: "Equipment classes", perm: "masters:read" },
  { key: "types", icon: "fa-solid fa-sitemap", label: "Equipment types", perm: "masters:read" },
  { key: "access", icon: "fa-solid fa-user-lock", label: "Unit access", perm: "masters:read_senior" },
];
const panels = {
  sites: SitesPanel,
  units: UnitsPanel,
  classes: EquipmentClassesPanel,
  types: EquipmentTypesPanel,
  access: UserUnitsPanel,
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
