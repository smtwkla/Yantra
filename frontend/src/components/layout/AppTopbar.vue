<script setup>
/**
 * Topbar — page title, the notifications bell, username, and Sign out.
 * The bell (S021 § 1.3) opens My notifications. It shows to people with push:subscribe, and its
 * dot when this device needs turning on (stores/notifications.js decides).
 * Yantra runs on shared phones and kiosks, so the name is plain dark text and Sign out a
 * labelled 44 px button on every width (S064 UX-02; Plan.MD § 3 Shared-device login), a
 * deliberate departure from the base's "logout as an icon button" Topbar rule.
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
      <span class="user-name text-body me-2" data-test="user-name">{{ userName }}</span>
      <button type="button" class="btn btn-outline-secondary tap-target sign-out" @click="logout">
        <i class="fa-solid fa-right-from-bracket me-1"></i>Sign out
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
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.topbar-right {
  display: flex;
  align-items: center;
  min-width: 0;
}
/* A long name gives way, so the bell and Sign out always fit a phone's width */
.user-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* The button never loses its word (S064 § 5.2 rule 1) */
.sign-out {
  flex-shrink: 0;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
}
/* A 44 px tap target (a gloved thumb), drawn without a border so it sits in the 48 px bar */
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
