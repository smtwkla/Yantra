<script setup>
/**
 * Sidebar — icon-only navigation, permission-filtered.
 *
 * Nav items are data-driven (not hardcoded markup). Items are excluded
 * from the DOM entirely if the user lacks the required permission.
 */
import { computed, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { userPermissions } from "../../stores/auth";
import { navItems, canSeeNavItem, isActivePath } from "../../stores/navigation";
import ChangelogModal from "./ChangelogModal.vue";

const router = useRouter();
const route = useRoute();

const visibleItems = computed(() =>
  navItems.filter((item) => canSeeNavItem(item, userPermissions.value))
);

// The version opens the change log for IT Admin and Admin (S048); Admin holds every key
const canSeeChangelog = computed(() => userPermissions.value.includes("settings:edit"));
const changelog = ref(null);

function navigate(path) {
  router.push(path);
}
</script>

<template>
  <aside class="sidebar">
    <nav class="sidebar-nav">
      <button
        v-for="item in visibleItems"
        :key="item.name"
        class="sidebar-btn"
        :class="{ active: isActivePath(route.path, item.path) }"
        :title="item.label"
        @click="navigate(item.path)"
      >
        <i :class="item.icon"></i>
      </button>
    </nav>

    <div class="sidebar-footer">
      <button
        v-if="canSeeChangelog"
        type="button"
        class="version-btn"
        title="See what changed"
        @click="changelog.open()"
      >v{{ $appVersion }}</button>
      <small v-else>v{{ $appVersion }}</small>
    </div>
    <ChangelogModal v-if="canSeeChangelog" ref="changelog" />
  </aside>
</template>

<script>
// Make the app version available as a global property
export default {
  computed: {
    $appVersion() {
      return typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "?";
    },
  },
};
</script>

<style scoped>
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  z-index: 100;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 1rem;
  gap: 0.25rem;
}

.sidebar-btn {
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--sidebar-icon-color);
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}

.sidebar-btn:hover {
  background: var(--sidebar-icon-hover-bg);
}

.sidebar-btn.active {
  background: var(--sidebar-icon-active-bg);
  color: var(--sidebar-icon-active-color);
}

.sidebar-footer {
  text-align: center;
  padding: 0.5rem;
  color: var(--text-muted);
  font-size: 0.7rem;
}

.version-btn {
  border: none;
  background: transparent;
  padding: 0;
  color: inherit;
  font-size: inherit;
  text-decoration: underline dotted;
  cursor: pointer;
}

@media (max-width: 576px) {
  .sidebar { display: none; }
}
</style>
