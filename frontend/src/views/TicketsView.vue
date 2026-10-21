<script setup>
/**
 * Tickets list (docs/steps/S017-raise-tickets/1-brief.md § 1). Open tickets at the user's
 * units by default; filters site, unit, breakdown / defect, state, one equipment, and text in
 * the serial or description. The server orders: open by intensity (critical first), then the
 * oldest event first — what is down and waiting longest leads; closed and all newest first.
 *
 * The filters live in the URL query, as on the equipment list, so Back returns to the same
 * list. Rows are a list, not a table, so they read on a phone. Age counts from the event
 * time, on this device's clock.
 *
 * S018: *Assigned to me* (shown to a user with a Team record), the assignees' first names on
 * each row, and *Not a fault* on a ticket closed as such.
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import IntensityBadge from "../components/IntensityBadge.vue";
import PagerBar from "../components/PagerBar.vue";
import { useDebounced } from "../composables/useDebounced";
import { userPermissions, userPersonId } from "../stores/auth";
import { ensureMyUnits, filterableUnits, myUnits } from "../stores/equipment";
import { ensureSites, ensureUnits, sites, units } from "../stores/masters";
import { ageText, firstName, INTENSITY_FILTERS, problemText, STATE_FILTERS, STATE_LABELS } from "../utils/ticketLabels";

const PAGE_SIZE = 50; // the API default
const DEFAULT_STATE = "open";

const route = useRoute();
const router = useRouter();

const canRaise = computed(() => userPermissions.value.includes("ticket:raise"));

const page = ref(null); // {items, total, page, per_page}
const loading = ref(true);
const loadError = ref("");
const now = ref(new Date());
let loadSeq = 0;

const query = computed(() => route.query);
const state = computed(() => query.value.state ?? DEFAULT_STATE);
const pageNumber = computed(() => Math.max(1, Number.parseInt(query.value.page, 10) || 1));
const hasFilters = computed(() => Object.keys(query.value).some((k) => k !== "page"));
const noUnits = computed(() => myUnits.value && !myUnits.value.all_units && myUnits.value.unit_ids.length === 0);

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

const unitChoices = computed(() => {
  if (!myUnits.value) return [];
  const mine = filterableUnits(units.value, myUnits.value);
  return query.value.site_id ? mine.filter((u) => String(u.site_id) === query.value.site_id) : mine;
});

function chooseSite(value) {
  const changes = { site_id: value };
  const unit = (units.value ?? []).find((u) => String(u.id) === query.value.unit_id);
  if (value && unit && String(unit.site_id) !== String(value)) changes.unit_id = null;
  update(changes);
}

// v-model on a select re-syncs when its options arrive later (a plain :value would not)
const filterModel = (key, fallback = "", set = (value) => update({ [key]: value })) =>
  computed({ get: () => query.value[key] ?? fallback, set });
const siteModel = filterModel("site_id", "", chooseSite);
const unitModel = filterModel("unit_id");
const intensityModel = filterModel("intensity");
const assignedToMe = computed({
  get: () => query.value.assigned === "me",
  set: (value) => update({ assigned: value ? "me" : null }),
});
const stateModel = filterModel("state", DEFAULT_STATE);

const searchText = ref(query.value.q ?? "");
const { schedule: scheduleSearch } = useDebounced(() => {
  if (searchText.value.trim() !== (query.value.q ?? "")) update({ q: searchText.value.trim() });
});
watch(searchText, scheduleSearch);
watch(() => query.value.q, (q) => {
  if ((q ?? "") !== searchText.value.trim()) searchText.value = q ?? "";
});

// The code of the filtered equipment, read off the first row (a machine, or the part the
// tickets were raised on); "this equipment" when the list is empty
const filteredEquipmentCode = computed(() => {
  const first = page.value?.items[0];
  if (!first) return "this equipment";
  const id = query.value.equipment_id;
  return [first.machine, first.component].find((n) => n && String(n.id) === id)?.code ?? "this equipment";
});

function listUrl() {
  const params = new URLSearchParams({ state: state.value, page: String(pageNumber.value), per_page: String(PAGE_SIZE) });
  for (const key of ["site_id", "unit_id", "intensity", "equipment_id", "assigned", "q"]) {
    if (query.value[key]) params.set(key, query.value[key]);
  }
  return `/api/tickets?${params}`;
}

async function load() {
  if (route.name !== "tickets") return; // the route is changing to another page
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const [result] = await Promise.all([apiGet(listUrl()), ensureSites(), ensureUnits(), ensureMyUnits()]);
    if (seq !== loadSeq) return;
    page.value = result;
    now.value = new Date();
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

onMounted(load);
watch(() => route.fullPath, load);
</script>

<template>
  <div class="py-3">
    <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
      <select v-model="stateModel" class="form-select w-auto" aria-label="State">
        <option v-for="[value, text] in STATE_FILTERS" :key="value" :value="value">{{ text }}</option>
      </select>
      <select v-model="intensityModel" class="form-select w-auto" aria-label="Breakdown or defect">
        <option v-for="[value, text] in INTENSITY_FILTERS" :key="value" :value="value">{{ text }}</option>
      </select>
      <select v-model="siteModel" class="form-select w-auto" aria-label="Site">
        <option value="">All sites</option>
        <option v-for="s in sites ?? []" :key="s.id" :value="s.id">{{ s.code }}</option>
      </select>
      <select v-model="unitModel" class="form-select w-auto" aria-label="Unit">
        <option value="">All units</option>
        <option v-for="u in unitChoices" :key="u.id" :value="u.id">{{ u.full_code }}</option>
      </select>
      <input v-model="searchText" class="form-control w-auto" type="search" placeholder="Search serial or text…" aria-label="Search" />
      <div v-if="userPersonId" class="form-check mb-0">
        <input id="tickets-assigned-me" v-model="assignedToMe" class="form-check-input" type="checkbox" />
        <label class="form-check-label" for="tickets-assigned-me">Assigned to me</label>
      </div>
      <router-link v-if="canRaise" to="/tickets/new" class="btn btn-primary ms-auto">
        <i class="fa-solid fa-plus me-1"></i>Raise ticket
      </router-link>
    </div>
    <div v-if="query.equipment_id" class="mb-3">
      <button type="button" class="btn btn-outline-secondary" title="Show every equipment" @click="update({ equipment_id: null })">
        Only {{ filteredEquipmentCode }}<i class="fa-solid fa-xmark ms-2"></i>
      </button>
    </div>

    <div v-if="loading && page" class="text-secondary small mb-1">Loading…</div>
    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger" @click="load">Retry</button>
    </div>
    <div v-else-if="loading && !page" class="text-secondary">Loading…</div>
    <div v-else-if="noUnits" class="text-secondary">You have no units assigned — ask IT admin for unit access.</div>
    <div v-else-if="page && page.total === 0" class="text-secondary">
      {{ hasFilters ? "No tickets match these filters." : "No open tickets." }}
    </div>
    <div v-else-if="page && page.items.length === 0" class="text-secondary">No tickets on this page.</div>
    <div v-else-if="page" class="list-group">
      <router-link
        v-for="t in page.items"
        :key="t.id"
        :to="`/tickets/${t.id}`"
        class="list-group-item list-group-item-action"
      >
        <div class="d-flex flex-wrap align-items-center gap-2">
          <IntensityBadge :intensity="t.intensity" />
          <span class="fw-semibold">{{ t.serial }}</span>
          <span class="ms-auto small text-secondary" :title="t.is_breakdown ? 'Stopped for' : 'Reported'">
            <i class="fa-regular fa-clock me-1"></i>{{ ageText(t.occurred_at, now) }}
          </span>
        </div>
        <div class="mt-1 ticket-text">
          {{ t.machine.code }} — {{ t.machine.name }}<span v-if="t.component" class="text-secondary"> · {{ t.component.code }}</span>
        </div>
        <div class="ticket-text">{{ problemText(t) }}</div>
        <div class="small text-secondary">
          {{ t.unit.site_code }}.{{ t.unit.code }} · {{ STATE_LABELS[t.state] }}<template v-if="t.not_a_fault"> · Not a fault</template>
          <template v-if="t.assignees.length"> · <i class="fa-solid fa-user"></i> {{ t.assignees.map((a) => firstName(a.name)).join(", ") }}</template>
        </div>
      </router-link>
    </div>
    <PagerBar
      v-if="page && !loadError"
      :page="pageNumber"
      :total="page.total"
      :per-page="PAGE_SIZE"
      @page="update({ page: $event })"
    />
  </div>
</template>

<style scoped>
.ticket-text {
  overflow-wrap: anywhere;
}
</style>
