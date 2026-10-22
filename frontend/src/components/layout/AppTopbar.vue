<script setup>
/**
 * Topbar — page title, the notifications bell, username, and logout.
 * The bell (S021 § 1.3) opens My notifications. It shows to people with push:subscribe, and its
 * dot when this device needs turning on (stores/notifications.js decides).
 */
import { computed } from "vue";
import { useRoute } from "vue-router";
import { userName, userPermissions, logout } from "../../stores/auth";
import { showDot } from "../../stores/notifications";

const route = useRoute();
const canSubscribe = computed(() => userPermissions.value.includes("push:subscribe"));
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
      <router-link
        v-if="canSubscribe"
        to="/notifications"
        class="bell text-secondary"
        aria-label="My notifications"
        title="My notifications"
      >
        <i class="fa-solid fa-bell"></i>
        <span v-if="showDot" class="bell-dot"><span class="visually-hidden">Turn notifications on</span></span>
      </router-link>
      <span class="user-name text-secondary me-2">{{ userName }}</span>
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
.topbar-right {
  display: flex;
  align-items: center;
  min-width: 0;
}
/* A long name gives way, so the bell and Logout always fit a phone's width */
.user-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* A 44 px tap target (a gloved thumb), drawn without a border so it sits in the 42 px bar */
.bell {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  font-size: 1.1rem;
}
.bell-dot {
  position: absolute;
  top: 9px;
  right: 9px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--bs-danger);
  border: 2px solid var(--topbar-bg);
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
