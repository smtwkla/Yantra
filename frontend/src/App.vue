<script setup>
import { computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppSidebar from "./components/layout/AppSidebar.vue";
import AppTopbar from "./components/layout/AppTopbar.vue";
import AppBottomNav from "./components/layout/AppBottomNav.vue";
import UpdateToast from "./components/layout/UpdateToast.vue";
import { authenticated, authError, logout, networkDenied, userPermissions } from "./stores/auth";
import { canOpenRoute, landingPath } from "./stores/navigation";
import { startVersionChecks, stopVersionChecks } from "./stores/appVersion";
import { loadNotifications } from "./stores/notifications";
import NoAccessView from "./views/NoAccessView.vue";

const noAccess = computed(() => authenticated.value && userPermissions.value.length === 0);

// Watch for newer deployed builds — a tab left open on the shop floor would
// otherwise keep running old JS indefinitely. See stores/appVersion.js.
onMounted(startVersionChecks);
onUnmounted(stopVersionChecks);

// The first navigation happens before login completes, so the router guard
// could not check it — re-check once the permissions are known.
const route = useRoute();
const router = useRouter();
watch(userPermissions, (perms) => {
  if (!authenticated.value || canOpenRoute(route.name, perms)) return;
  const landing = landingPath(perms);
  if (landing && landing !== route.path) router.replace(landing);
});

// The bell's dot (S021 § 1.3): this device's state, once the user is known. A failure leaves no
// dot; My notifications loads again and shows the error.
watch(userPermissions, (perms) => {
  if (authenticated.value && perms.includes("push:subscribe")) loadNotifications().catch(() => {});
});
</script>

<template>
  <!-- Checked first: loadProfile also sets authError on the same 403, and a refusal can arrive mid-session (S013) -->
  <div v-if="networkDenied" class="d-flex justify-content-center align-items-center vh-100 p-3">
    <div class="card auth-error-card">
      <div class="card-body text-center">
        <h5 class="card-title"><i class="fa-solid fa-network-wired me-2 text-secondary"></i>Yantra</h5>
        <p class="card-text">{{ networkDenied.message }}.</p>
        <p class="card-text text-secondary small">
          The server saw your address as <strong>{{ networkDenied.ip || "unknown" }}</strong>.
          Connect to the plant network (Wi-Fi or VPN) and reload the page.
        </p>
        <button class="btn btn-sm btn-outline-secondary" @click="logout">
          <i class="fa-solid fa-right-from-bracket me-1"></i>Sign out
        </button>
      </div>
    </div>
  </div>
  <div v-else-if="authenticated" class="app-shell">
    <AppSidebar class="no-print" />
    <AppBottomNav class="no-print" />
    <div class="app-main">
      <AppTopbar class="topbar-desktop no-print" />
      <main class="app-content">
        <AppTopbar class="topbar-mobile no-print" />
        <!-- Signed in with no permission anywhere: no nav items, and this page instead (S011) -->
        <NoAccessView v-if="noAccess" />
        <router-view v-else />
      </main>
    </div>
    <UpdateToast class="no-print" />
  </div>
  <div v-else-if="authError" class="d-flex justify-content-center align-items-center vh-100 p-3">
    <div class="card auth-error-card">
      <div class="card-body text-center">
        <h5 class="card-title">Yantra</h5>
        <p class="card-text text-secondary">{{ authError }}</p>
        <button class="btn btn-sm btn-outline-secondary" @click="logout">
          <i class="fa-solid fa-right-from-bracket me-1"></i>Sign out
        </button>
      </div>
    </div>
  </div>
  <div v-else class="d-flex justify-content-center align-items-center vh-100">
    <div class="spinner-border" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: var(--sidebar-width);
  min-width: 0;
}

.app-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 1.5rem 1.5rem;
}

.auth-error-card {
  max-width: 420px;
}

.topbar-mobile { display: none; }

@media (max-width: 576px) {
  .app-main { margin-left: 0; }
  .topbar-desktop { display: none; }
  .topbar-mobile { display: flex; margin: -1.5rem -1.5rem 1rem -1.5rem; }
}
</style>
