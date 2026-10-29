<script setup>
/**
 * The two tabs above the Tickets list and the Improvements list (S068, Q1.2 a). Shown only to
 * holders of improvement:read, so a role without it sees the Tickets list as before. The active
 * tab follows the route name, not router-link-active, which also matches /tickets on
 * /tickets/improvements (a prefix match).
 */
import { computed } from "vue";
import { useRoute } from "vue-router";
import { userPermissions } from "../stores/auth";

const route = useRoute();
const shown = computed(() => userPermissions.value.includes("improvement:read"));
const onImprovements = computed(() => route.name === "improvements" || route.name === "improvement-detail");
const tabs = computed(() => [
  { to: "/tickets", text: "Tickets", active: route.name === "tickets" },
  { to: "/tickets/improvements", text: "Improvements", active: onImprovements.value },
]);
</script>

<template>
  <ul v-if="shown" class="nav nav-tabs nav-fill mb-3" data-testid="tickets-tabs">
    <li v-for="tab in tabs" :key="tab.to" class="nav-item">
      <router-link
        :to="tab.to"
        class="nav-link w-100 px-1"
        :class="{ active: tab.active }"
        :aria-current="tab.active ? 'page' : undefined"
      >{{ tab.text }}</router-link>
    </li>
  </ul>
</template>
