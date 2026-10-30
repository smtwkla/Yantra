<script setup>
/**
 * Improvements list, the second tab of Tickets (docs/steps/S068-improvement-screens/1-brief.md
 * § 5.5; mock-up docs/roadmap/R05-mockups/07-improvements.html, left). Open or closed
 * improvements, a Unit filter; the filters and the page live in the URL query, as on the Tickets
 * list, so Back returns to the same list. A row: serial, state, lead, title, the loss.
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import PagerBar from "../components/PagerBar.vue";
import TicketsTabs from "../components/TicketsTabs.vue";
import { userPermissions } from "../stores/auth";
import { ensureMyUnits, filterableUnits, myUnits, noUnits } from "../stores/equipment";
import { ensureUnits, units } from "../stores/masters";
import { IMPROVEMENT_STATE_FILTERS, improvementStateLabel, lossText } from "../utils/improvementLabels";
import { registerPath } from "../utils/improvementRegister";
import { NO_UNITS_TEXT } from "../utils/messages";

const PAGE_SIZE = 50; // the API default
const DEFAULT_STATE = "open";

const route = useRoute();
const router = useRouter();

const page = ref(null); // {items, total, page, per_page}
const loading = ref(true);
const loadError = ref("");
const forbidden = ref(false);
let loadSeq = 0;

const query = computed(() => route.query);
const state = computed(() => query.value.state ?? DEFAULT_STATE);
const pageNumber = computed(() => Math.max(1, Number.parseInt(query.value.page, 10) || 1));
const canStart = computed(() => userPermissions.value.includes("improvement:edit"));
const canPrintRegister = computed(() => userPermissions.value.includes("report:read"));

// The management review's register on a printable page in a new tab (S076), as the asset list from Equipment
function printRegister() {
  window.open(router.resolve(registerPath()).href, "_blank");
}

/** Merge `changes` into the query; defaults and empty values are left out of the URL. */
function update(changes) {
  const merged = { ...query.value, ...changes };
  if (!("page" in changes)) delete merged.page; // a filter change goes back to page 1
  for (const key of Object.keys(merged)) {
    if (merged[key] === null || merged[key] === undefined || merged[key] === "") delete merged[key];
  }
  if (merged.state === DEFAULT_STATE) delete merged.state;
  if (merged.page === 1) delete merged.page;
  router.replace({ query: merged });
}

const unitChoices = computed(() => (myUnits.value ? filterableUnits(units.value, myUnits.value) : []));

// v-model on a select re-syncs when its options arrive later (a plain :value would not)
const filterModel = (key, fallback = "") => computed({ get: () => query.value[key] ?? fallback, set: (value) => update({ [key]: value }) });
const stateModel = filterModel("state", DEFAULT_STATE);
const unitModel = filterModel("unit_id");

function listUrl() {
  const params = new URLSearchParams({ state: state.value, page: String(pageNumber.value), per_page: String(PAGE_SIZE) });
  if (query.value.unit_id) params.set("unit_id", query.value.unit_id);
  return `/api/improvements?${params}`;
}

async function load() {
  if (route.name !== "improvements") return; // the route is changing to another page
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  forbidden.value = false;
  try {
    const [result] = await Promise.all([apiGet(listUrl()), ensureUnits(), ensureMyUnits()]);
    if (seq !== loadSeq) return;
    page.value = result;
  } catch (err) {
    if (seq !== loadSeq) return;
    if (err.status === 403) forbidden.value = true; // no improvement:read: said in its own words, no Retry
    else loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

const emptyText = computed(() => {
  if (query.value.unit_id) return "No improvements match these filters.";
  return state.value === "closed" ? "No closed improvements yet." : "No open improvements.";
});

onMounted(load);
watch(() => route.fullPath, load);
</script>

<template>
  <div class="py-3">
    <TicketsTabs />
    <div v-if="forbidden" class="alert alert-warning">You can't see improvements.</div>
    <template v-else>
      <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
        <select v-model="stateModel" class="form-select w-auto" aria-label="State">
          <option v-for="[value, text] in IMPROVEMENT_STATE_FILTERS" :key="value" :value="value">{{ text }}</option>
        </select>
        <select v-model="unitModel" class="form-select w-auto" aria-label="Unit">
          <option value="">All units</option>
          <option v-for="u in unitChoices" :key="u.id" :value="u.id">{{ u.full_code }}</option>
        </select>
        <button v-if="canPrintRegister" class="btn btn-sm btn-outline-primary ms-auto d-none d-md-inline-block" @click="printRegister">
          <i class="fa-solid fa-print me-1"></i>Print register
        </button>
      </div>

      <div v-if="loading && page" class="text-secondary small mb-1">Loading…</div>
      <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
        <span>{{ loadError }}</span>
        <button class="btn btn-outline-danger" @click="load">Retry</button>
      </div>
      <div v-else-if="loading && !page" class="text-secondary">Loading…</div>
      <div v-else-if="noUnits" class="text-secondary">{{ NO_UNITS_TEXT }}</div>
      <div v-else-if="page && page.total === 0" class="text-secondary">
        <div>{{ emptyText }}</div>
        <div v-if="canStart && state === 'open' && !query.unit_id">Start one from a ticket that is back in service or closed.</div>
      </div>
      <div v-else-if="page && page.items.length === 0" class="text-secondary">No improvements on this page.</div>
      <div v-else-if="page" class="list-group">
        <router-link
          v-for="im in page.items"
          :key="im.id"
          :to="`/tickets/improvements/${im.id}`"
          class="list-group-item list-group-item-action"
        >
          <div class="d-flex flex-wrap align-items-center gap-2">
            <span class="fw-semibold">{{ im.serial }}</span>
            <span class="badge text-bg-light border">{{ improvementStateLabel(im.state) }}</span>
            <span class="ms-auto small text-secondary">lead {{ im.lead.name }}</span>
          </div>
          <div class="mt-1 text-break">{{ im.title }}</div>
          <div class="small text-secondary">{{ lossText(im.loss) }}</div>
        </router-link>
      </div>
      <PagerBar
        v-if="page && !loadError"
        :page="pageNumber"
        :total="page.total"
        :per-page="PAGE_SIZE"
        @page="update({ page: $event })"
      />
    </template>
  </div>
</template>
