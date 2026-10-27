<script setup>
/**
 * AppBottomNav — mobile bottom navigation bar.
 *
 * Visible only on small screens (< 576px) via CSS.
 * Mirrors the sidebar nav items, filtered by user permissions.
 * Each item is a real link (S064 UX-22): Tab reaches it and Enter opens it.
 */

import { computed } from "vue";
import { useRoute } from "vue-router";
import { userPermissions } from "../../stores/auth";
import { navItems, canSeeNavItem, isActivePath } from "../../stores/navigation";

const route = useRoute();

const visibleItems = computed(() =>
  navItems.filter((item) => canSeeNavItem(item, userPermissions.value))
);
</script>

<template>
  <nav class="app-bottom-nav">
    <router-link
      v-for="item in visibleItems"
      :key="item.name"
      :to="item.path"
      class="bottom-nav-item"
      :class="{ active: isActivePath(route.path, item.path) }"
    >
      <i :class="item.icon"></i>
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
</template>
