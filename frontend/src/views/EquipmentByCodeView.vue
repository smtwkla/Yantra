<script setup>
/**
 * /e/<code> — the link on a QR label (docs/steps/S014-qr-labels/1-brief.md § 3). Looks the code
 * up and replaces this route with the equipment page, so Back does not return here and loop.
 * An unknown code and one outside the user's units are the same 404 → the not-found page.
 * Sign-in is as for every page: keycloak-js returns to this same link after login.
 */
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import NotFoundView from "./NotFoundView.vue";

const route = useRoute();
const router = useRouter();

const notFound = ref(false);
const loadError = ref("");

async function resolve() {
  const code = route.params.code;
  if (code === undefined) return; // the route is changing to another page
  notFound.value = false;
  loadError.value = "";
  try {
    const { id } = await apiGet(`/api/equipment/by-code/${encodeURIComponent(code)}`);
    router.replace(`/equipment/${id}`);
  } catch (err) {
    if (err.status === 404) notFound.value = true;
    else loadError.value = err.message;
  }
}

watch(() => route.params.code, resolve, { immediate: true });
</script>

<template>
  <NotFoundView v-if="notFound" />
  <div v-else-if="loadError" class="py-3">
    <div class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-sm btn-outline-danger" @click="resolve">Retry</button>
    </div>
  </div>
  <div v-else class="py-3 text-secondary">Opening {{ route.params.code }}…</div>
</template>
