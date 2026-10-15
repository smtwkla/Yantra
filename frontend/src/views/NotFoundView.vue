<script setup>
/**
 * Shown for any address that matches no route (docs/steps/S005-tidy-up/1-brief.md § 4.1).
 * The address is echoed as text ({{ }}), never as HTML.
 */
import { computed } from "vue";
import { useRoute } from "vue-router";
import { userPermissions } from "../stores/auth";
import { landingNavItem } from "../stores/navigation";

const route = useRoute();
const landing = computed(() => landingNavItem(userPermissions.value));
</script>

<template>
  <div class="py-5 text-center">
    <i class="fa-solid fa-triangle-exclamation fa-2x text-secondary mb-3"></i>
    <h1 class="h4">Page not found</h1>
    <p class="text-secondary text-break">
      The address <strong>{{ route.fullPath }}</strong> doesn't exist in Yantra.
    </p>
    <router-link v-if="landing" :to="landing.path" class="btn btn-primary">Go to {{ landing.label }}</router-link>
  </div>
</template>
