<script setup>
/**
 * ModuleToolbar — level-2 navigation (SMTW-WebApp-Base § Navigation Hierarchy).
 *
 * Switches between a module's sections as local state, not routes. Data-driven:
 * sections are {key, icon, label, perm}; those the user lacks `perm` for are
 * dropped, and the bar is hidden when at most one section remains.
 */
import { computed } from "vue";
import { userPermissions } from "../../stores/auth";
import { canSeeNavItem } from "../../stores/navigation";

const props = defineProps({
  sections: { type: Array, required: true },
  active: { type: String, required: true },
});
defineEmits(["select"]);

const visibleSections = computed(() =>
  props.sections.filter((section) => canSeeNavItem(section, userPermissions.value))
);
</script>

<template>
  <nav v-if="visibleSections.length > 1" class="module-toolbar">
    <button
      v-for="section in visibleSections"
      :key="section.key"
      class="module-toolbar-btn"
      :class="{ active: section.key === active }"
      :title="section.label"
      @click="$emit('select', section.key)"
    >
      <i :class="section.icon"></i>
      <span class="module-toolbar-label">{{ section.label }}</span>
    </button>
  </nav>
</template>

<style scoped>
.module-toolbar {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  padding-bottom: 12px;
}
.module-toolbar-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.module-toolbar-btn:hover {
  background: var(--sidebar-icon-hover-bg);
  color: var(--sidebar-icon-active-color);
}
.module-toolbar-btn.active {
  background: var(--sidebar-icon-active-bg);
  color: var(--sidebar-icon-active-color);
}
@media (max-width: 576px) {
  .module-toolbar-label {
    font-size: 0.8rem;
  }
}
</style>
