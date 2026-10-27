<script setup>
/**
 * /e/<code> — the link on a QR label (docs/steps/S014-qr-labels/1-brief.md § 3). Looks the code
 * up and replaces this route with the equipment page, so Back does not return here and loop.
 * An unknown code and one outside the user's units are the same 404 → one text for both, so it
 * never tells which (S064 UX-03): a printed label exists, so "doesn't exist" would be wrong.
 * Sign-in is as for every page: keycloak-js returns to this same link after login.
 */
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";

const route = useRoute();
const router = useRouter();

const notFound = ref(false);
// Upper-cased as the label prints it (labels_core.py)
const shownCode = computed(() => String(route.params.code ?? "").toUpperCase());
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
  <div v-if="notFound" class="py-5 text-center" data-test="code-not-found">
    <i class="fa-solid fa-qrcode fa-2x text-secondary mb-3"></i>
    <h1 class="h4 text-break">{{ shownCode }}</h1>
    <p class="text-secondary">Not found, or not at your units. Ask your engineer if you should see it.</p>
    <router-link to="/equipment" class="btn btn-primary btn-lg">Go to equipment list</router-link>
  </div>
  <div v-else-if="loadError" class="py-3">
    <div class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-sm btn-outline-danger" @click="resolve">Retry</button>
    </div>
  </div>
  <div v-else class="py-3 text-secondary">Opening {{ route.params.code }}…</div>
</template>
