<script setup>
/**
 * Topbar — page title, username, and logout.
 */
import { useRoute } from "vue-router";
import { userName, logout } from "../../stores/auth";

const route = useRoute();
</script>

<template>
  <header class="topbar">
    <div class="topbar-left">
      <strong>Yantra</strong>
    </div>
    <div class="topbar-center">
      {{ route.meta?.title }}
    </div>
    <div class="topbar-right">
      <span class="text-secondary me-2">{{ userName }}</span>
      <button class="btn btn-sm btn-outline-secondary" @click="logout" title="Logout">
        <i class="fa-solid fa-right-from-bracket"></i>
      </button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  height: var(--topbar-height);
  min-height: var(--topbar-height);
  background: var(--topbar-bg);
  border-bottom: 1px solid var(--topbar-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
}
.topbar-center {
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-primary);
}

@media (max-width: 576px) {
  .topbar {
    padding: 0 0.75rem;
  }
  .topbar-left strong {
    font-size: 0.8rem;
  }
  .topbar-center {
    font-size: 0.85rem;
  }
  .topbar-right {
    font-size: 0.8rem;
  }
}
</style>
