<script setup>
/**
 * UpdateToast — prompts the user to reload when a newer build is deployed.
 *
 * Detection lives in stores/appVersion.js; this component is presentation only.
 * It prompts rather than reloading automatically: an operator may be half-way
 * through entering a ticket, and a surprise reload would discard that.
 *
 * Dismissing hides it for this page view only.  The next load picks up the new
 * build anyway, so there is nothing to remember.
 */

import { ref } from "vue";
import { updateAvailable, serverVersion, reloadApp } from "../../stores/appVersion";

const dismissed = ref(false);
</script>

<template>
  <div v-if="updateAvailable && !dismissed" class="update-toast" role="status">
    <div class="update-toast-text">
      <strong>New version available</strong>
      <span class="update-toast-version">v{{ serverVersion }}</span>
    </div>
    <button type="button" class="btn btn-sm btn-primary" @click="reloadApp">
      Reload
    </button>
    <button
      type="button"
      class="btn-close btn-close-white"
      aria-label="Dismiss"
      @click="dismissed = true"
    ></button>
  </div>
</template>

<style scoped>
.update-toast {
  position: fixed;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  /* Above the mobile bottom nav (z-index 1040 in main.css) */
  z-index: 1050;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  max-width: calc(100vw - 2rem);
  padding: 0.6rem 0.9rem;
  border-radius: 0.5rem;
  background: var(--sidebar-bg);
  color: #ffffff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.update-toast-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  white-space: nowrap;
}

.update-toast-version {
  font-size: 0.75rem;
  color: var(--sidebar-icon-color);
}

/* Clear the bottom nav on mobile so the toast never covers it */
@media (max-width: 576px) {
  .update-toast {
    bottom: calc(56px + 1rem);
  }
}
</style>
