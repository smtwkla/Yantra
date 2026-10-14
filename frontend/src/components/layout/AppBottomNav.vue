<script setup>
/**
 * AppBottomNav — mobile bottom navigation bar.
 *
 * Visible only on small screens (< 576px) via CSS.
 * Mirrors the sidebar nav items, filtered by user permissions.
 */

import { computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { userPermissions } from "../../stores/auth";
import { navItems, canSeeNavItem, isActivePath } from "../../stores/navigation";

const router = useRouter();
const route = useRoute();

const visibleItems = computed(() =>
  navItems.filter((item) => canSeeNavItem(item, userPermissions.value))
);

function navigate(path) {
  router.push(path);
}
</script>

<template>
  <nav class="app-bottom-nav">
    <a
      v-for="item in visibleItems"
      :key="item.name"
      class="bottom-nav-item"
      :class="{ active: isActivePath(route.path, item.path) }"
      role="button"
      @click="navigate(item.path)"
    >
      <i :class="item.icon"></i>
      <span>{{ item.label }}</span>
    </a>
  </nav>
</template>
