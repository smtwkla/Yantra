<script setup>
/**
 * Readings (S040, S050 § 1.1): two tabs.
 *   Sheet     — the end-of-day sheet (readings/ReadingsSheet.vue), for reading:log holders; the default.
 *   Register  — one node's readings as a table (readings/ReadingsRegister.vue), for every
 *               equipment:read holder. A user without reading:log (the storekeeper, IT admin) sees
 *               only this tab and no tab bar; a typed ?tab=sheet opens it too (BR1-11).
 * The tab lives in the URL query, as on Me (S031), so Back returns to it.
 *
 * Each tab mounts the first time it shows and then stays mounted (a seen-flag with v-if, then
 * v-show; BR1-01, BR2-01): readings typed on the sheet survive a look at the register, and a user
 * who arrives on the register never mounts the sheet, so no sheet request runs for him.
 */
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { userPermissions } from "../stores/auth";
import ReadingsRegister from "./readings/ReadingsRegister.vue";
import ReadingsSheet from "./readings/ReadingsSheet.vue";

const SHEET = "sheet";
const REGISTER = "register";
const TABS = [
  [SHEET, "Sheet"],
  [REGISTER, "Register"],
];

const route = useRoute();
const router = useRouter();

const canLog = computed(() => userPermissions.value.includes("reading:log"));
const tab = computed(() => (!canLog.value || route.query.tab === REGISTER ? REGISTER : SHEET));
const seen = reactive({ [SHEET]: false, [REGISTER]: false });
watch(tab, (key) => {
  seen[key] = true;
}, { immediate: true });

// The register's node and meters are kept while the sheet shows, and given back on the way back
const lastRegisterQuery = ref({ tab: REGISTER });
watch(() => route.query, (query) => {
  if (tab.value === REGISTER) lastRegisterQuery.value = { ...query, tab: REGISTER };
}, { immediate: true });

function chooseTab(key) {
  if (key === tab.value) return;
  router.replace({ query: key === SHEET ? {} : lastRegisterQuery.value });
}
</script>

<template>
  <div class="pt-3">
    <ul v-if="canLog" class="nav nav-tabs nav-fill">
      <li v-for="[key, text] in TABS" :key="key" class="nav-item">
        <button
          type="button"
          class="nav-link w-100 px-1"
          :class="{ active: tab === key }"
          :aria-current="tab === key ? 'page' : undefined"
          @click="chooseTab(key)"
        >{{ text }}</button>
      </li>
    </ul>
    <ReadingsSheet v-if="canLog && seen.sheet" v-show="tab === 'sheet'" />
    <ReadingsRegister v-if="seen.register" v-show="tab === 'register'" :active="tab === 'register'" />
  </div>
</template>
