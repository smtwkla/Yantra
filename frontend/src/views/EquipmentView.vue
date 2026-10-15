<script setup>
/**
 * Equipment list — a paged, filterable table (docs/steps/S003-equipment-screens/1-brief.md § 4.1;
 * type filter and the search in notes and type names: S004).
 * The filters live in the URL query, so Back returns to the same page and a filtered list
 * can be bookmarked. The route is the single source of truth: controls write to it with
 * router.replace and the list reloads when it changes.
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import CriticalityBadge from "../components/CriticalityBadge.vue";
import PagerBar from "../components/PagerBar.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { useDebounced } from "../composables/useDebounced";
import { userPermissions } from "../stores/auth";
import { ensureMyUnits, filterableUnits, myUnits } from "../stores/equipment";
import {
  ensureEquipmentClasses, ensureEquipmentTypes, ensureSites, ensureUnits, equipmentClasses, equipmentTypes, sites, units,
} from "../stores/masters";
import { STATUS_LABELS } from "../utils/equipmentLabels";
import EquipmentFormModal from "./equipment/EquipmentFormModal.vue";

const PAGE_SIZE = 50; // the API default
const SEARCH_DELAY_MS = 300;
const DEFAULT_LEVEL = "equipment";
const LEVEL_CHOICES = [
  ["equipment", "Equipment"],
  ["component_unit", "Component-units"],
  ["component", "Components"],
  ["all", "All levels"],
];

const route = useRoute();
const router = useRouter();

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const formModal = ref(null);

const page = ref(null); // {items, total, page, per_page}
const loading = ref(true);
const loadError = ref("");
let loadSeq = 0;

// ---- filters (from the URL) ----

const query = computed(() => route.query);
const level = computed(() => query.value.level ?? DEFAULT_LEVEL);
const pageNumber = computed(() => Math.max(1, Number.parseInt(query.value.page, 10) || 1));
// A bookmarked status=scrapped needs the scrapped rows, so it ticks the box
const showScrapped = computed(() => query.value.scrapped === "1" || query.value.status === "scrapped");
const hasFilters = computed(() => Object.keys(query.value).some((k) => k !== "page"));
const noUnits = computed(() => myUnits.value && !myUnits.value.all_units && myUnits.value.unit_ids.length === 0);

/** Merge `changes` into the query; defaults and empty values are left out of the URL. */
function update(changes) {
  const merged = { ...query.value, ...changes };
  if (!("page" in changes)) delete merged.page; // a filter change goes back to page 1
  for (const key of Object.keys(merged)) {
    if (merged[key] === null || merged[key] === undefined || merged[key] === "") delete merged[key];
  }
  if (merged.level === DEFAULT_LEVEL) delete merged.level;
  if (merged.page === 1) delete merged.page;
  router.replace({ query: merged });
}

const unitChoices = computed(() => {
  if (!myUnits.value) return [];
  const mine = filterableUnits(units.value, myUnits.value);
  return query.value.site_id ? mine.filter((u) => String(u.site_id) === query.value.site_id) : mine;
});
// Active classes first, then inactive ones (marked)
const classChoices = computed(() =>
  [...(equipmentClasses.value ?? [])].sort((a, b) => Number(b.active) - Number(a.active) || a.code.localeCompare(b.code))
);
// Shown with a class, or with a type_id in the URL alone, so a bookmarked type filter is never applied
// invisibly. Inactive types stay listed (marked): equipment can still carry them.
const showTypeFilter = computed(() => Boolean(query.value.class_id || query.value.type_id));
const typeChoices = computed(() => {
  const all = equipmentTypes.value ?? [];
  const shown = query.value.class_id ? all.filter((t) => String(t.class_id) === query.value.class_id) : all;
  return [...shown].sort((a, b) => Number(b.active) - Number(a.active));
});
const typeLabel = (t) => (query.value.class_id ? t.name : `${t.class_code} · ${t.name}`);
const statusChoices = computed(() =>
  Object.entries(STATUS_LABELS).filter(([value]) => value !== "scrapped" || showScrapped.value)
);

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
// A type belongs to one class, so choosing a class always clears the type
const classModel = filterModel("class_id", "", (value) => update({ class_id: value, type_id: null }));
const typeModel = filterModel("type_id");
// Leaving a bookmarked status=scrapped must not untick "Show scrapped" behind the user's back
function chooseStatus(value) {
  const changes = { status: value };
  if (query.value.status === "scrapped" && query.value.scrapped !== "1") changes.scrapped = "1";
  update(changes);
}
const statusModel = filterModel("status", "", chooseStatus);
const criticalityModel = filterModel("criticality");
const levelModel = filterModel("level", DEFAULT_LEVEL);

function toggleScrapped(on) {
  const changes = { scrapped: on ? "1" : null };
  if (!on && query.value.status === "scrapped") changes.status = null;
  update(changes);
}

// ---- search: 300 ms after the last keystroke ----

const searchText = ref(query.value.q ?? "");

function applySearch() {
  const text = searchText.value.trim();
  const before = (query.value.q ?? "").trim();
  if (text === before) return;
  const changes = { q: text };
  // A motor is found by its code, so the first search widens the level; the user can narrow it again
  if (before === "" && text !== "" && level.value === DEFAULT_LEVEL) changes.level = "all";
  update(changes);
}

const { schedule: scheduleSearch } = useDebounced(applySearch, SEARCH_DELAY_MS);
watch(searchText, scheduleSearch);
// Back / Forward changes q without typing
watch(() => query.value.q, (q) => {
  if ((q ?? "") !== searchText.value.trim()) searchText.value = q ?? "";
});

// ---- loading ----

function listUrl() {
  const params = new URLSearchParams({ level: level.value, page: String(pageNumber.value), per_page: String(PAGE_SIZE) });
  for (const key of ["site_id", "unit_id", "class_id", "type_id", "status", "criticality", "q"]) {
    if (query.value[key]) params.set(key, query.value[key]);
  }
  if (showScrapped.value) params.set("include_scrapped", "1");
  return `/api/equipment?${params}`;
}

async function load() {
  if (route.name !== "equipment") return; // the route is changing to another page
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const [result] = await Promise.all([
      apiGet(listUrl()), ensureSites(), ensureUnits(), ensureEquipmentClasses(), ensureEquipmentTypes(), ensureMyUnits(),
    ]);
    if (seq === loadSeq) page.value = result;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

onMounted(load);
watch(() => route.fullPath, load);

function openNode(id) {
  router.push(`/equipment/${id}`);
}
</script>

<template>
  <div class="py-3">
    <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
      <select v-model="siteModel" class="form-select form-select-sm w-auto" aria-label="Site">
        <option value="">All sites</option>
        <option v-for="s in sites ?? []" :key="s.id" :value="s.id">{{ s.code }}{{ s.active ? "" : " (inactive)" }}</option>
      </select>
      <select v-model="unitModel" class="form-select form-select-sm w-auto" aria-label="Unit">
        <option value="">All units</option>
        <option v-for="u in unitChoices" :key="u.id" :value="u.id">{{ u.full_code }}{{ u.active ? "" : " (inactive)" }}</option>
      </select>
      <select v-model="classModel" class="form-select form-select-sm w-auto" aria-label="Class">
        <option value="">All classes</option>
        <option v-for="c in classChoices" :key="c.id" :value="c.id">{{ c.code }}{{ c.active ? "" : " (inactive)" }}</option>
      </select>
      <select v-if="showTypeFilter" v-model="typeModel" class="form-select form-select-sm w-auto" aria-label="Type">
        <option value="">All types</option>
        <option v-for="t in typeChoices" :key="t.id" :value="t.id">{{ typeLabel(t) }}{{ t.active ? "" : " (inactive)" }}</option>
      </select>
      <select v-model="statusModel" class="form-select form-select-sm w-auto" aria-label="Status">
        <option value="">All statuses</option>
        <option v-for="[value, text] in statusChoices" :key="value" :value="value">{{ text }}</option>
      </select>
      <select v-model="criticalityModel" class="form-select form-select-sm w-auto" aria-label="Criticality">
        <option value="">Any criticality</option>
        <option v-for="g in ['A', 'B', 'C']" :key="g" :value="g">{{ g }}</option>
      </select>
      <select v-model="levelModel" class="form-select form-select-sm w-auto" aria-label="Level">
        <option v-for="[value, text] in LEVEL_CHOICES" :key="value" :value="value">{{ text }}</option>
      </select>
      <input v-model="searchText" class="form-control form-control-sm w-auto" type="search" placeholder="Search code, name, notes…" aria-label="Search" />
      <button v-if="canEdit" class="btn btn-sm btn-primary ms-auto" @click="formModal.openCreateEquipment()">
        <i class="fa-solid fa-plus me-1"></i>Add equipment
      </button>
    </div>
    <div class="form-check form-switch mb-3">
      <input id="eq-show-scrapped" :checked="showScrapped" class="form-check-input" type="checkbox" @change="toggleScrapped($event.target.checked)" />
      <label class="form-check-label small" for="eq-show-scrapped">Show scrapped</label>
    </div>

    <div v-if="loading && page" class="text-secondary small mb-1">Loading…</div>
    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-sm btn-outline-danger" @click="load">Retry</button>
    </div>
    <div v-else-if="loading && !page" class="text-secondary">Loading…</div>
    <div v-else-if="noUnits" class="text-secondary">You have no units assigned — ask IT admin for unit access.</div>
    <div v-else-if="page && page.total === 0" class="text-secondary">
      {{ hasFilters ? "No equipment matches these filters." : "No equipment yet." }}
    </div>
    <div v-else-if="page && page.items.length === 0" class="text-secondary">No equipment on this page.</div>
    <div v-else-if="page" class="table-responsive">
      <table class="table table-sm table-hover align-middle mb-0">
        <thead>
          <tr>
            <th>Code</th><th>Name</th><th>Class</th><th>{{ level === "equipment" ? "Unit" : "Path" }}</th>
            <th>Crit.</th><th>Status</th><th class="text-end">Parts</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="e in page.items"
            :key="e.id"
            role="link"
            style="cursor: pointer"
            :class="{ 'text-secondary': e.status === 'scrapped' }"
            @click="openNode(e.id)"
          >
            <td><router-link :to="`/equipment/${e.id}`" class="fw-semibold" @click.stop>{{ e.code }}</router-link></td>
            <td>{{ e.name }}</td>
            <td>{{ e.class_code }}<span v-if="e.type_name" class="text-secondary"> · {{ e.type_name }}</span></td>
            <td>{{ level === "equipment" ? e.unit : e.full_path }}</td>
            <td><CriticalityBadge :grade="e.effective_criticality" /></td>
            <td><StatusBadge :status="e.status" /></td>
            <td class="text-end">{{ e.part_count }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <PagerBar
      v-if="page && !loadError"
      :page="pageNumber"
      :total="page.total"
      :per-page="PAGE_SIZE"
      @page="update({ page: $event })"
    />

    <EquipmentFormModal ref="formModal" @saved="({ result }) => openNode(result.id)" />
  </div>
</template>
