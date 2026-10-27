<script setup>
/**
 * Equipment list — a paged, filterable table (docs/steps/S003-equipment-screens/1-brief.md § 4.1;
 * type filter and the search in notes and type names: S004; ticks for QR labels: S014).
 * The filters live in the URL query, so Back returns to the same page and a filtered list
 * can be bookmarked. The route is the single source of truth: controls write to it with
 * router.replace and the list reloads when it changes. The property filter (S062) is one key,
 * `props`, built in its dialog; applying or clearing it is a history step (router.push), so Back
 * brings back a filter that took a dialog to build. The category (S063) narrows the class select
 * to its classes; like the class, it does not change the level.
 * On a phone (below md, S064 UX-08) the search comes first, the filters fold behind one counted
 * Filters (n) button, the office's ticks and print buttons are hidden, and each row is a two-line
 * card: a second template over the same rows, so the table stays as it is from md up.
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import CriticalityBadge from "../components/CriticalityBadge.vue";
import PagerBar from "../components/PagerBar.vue";
import LifecycleBadge from "../components/LifecycleBadge.vue";
import TicketLight from "../components/TicketLight.vue";
import { useDebounced } from "../composables/useDebounced";
import { userPermissions } from "../stores/auth";
import { ensureMyUnits, filterableUnits, myUnits } from "../stores/equipment";
import {
  ensureEquipmentCategories, ensureEquipmentClasses, ensureEquipmentTypes, ensureProperties, ensureSites, ensureUnits,
  equipmentCategories, equipmentClasses, equipmentTypes, properties, sites, units,
} from "../stores/masters";
import { CRITICALITY_OPTIONS, LIFECYCLE_LABELS } from "../utils/equipmentLabels";
import { assetListPath } from "../utils/assetList";
import { activeFirstBy, classChoicesFor, classOutsideCategory } from "../utils/equipmentFilters";
import { labelsPath, MAX_LABELS } from "../utils/labelSheets";
import { NO_UNITS_TEXT } from "../utils/messages";
import { decodeFilter, describeFilter, encodeFilter, propsChanges } from "../utils/propertyFilter";
import { TICKET_FILTER_CHOICES } from "../utils/ticketLabels";
import EquipmentFormModal from "./equipment/EquipmentFormModal.vue";
import PropertyFilterModal from "./equipment/PropertyFilterModal.vue";

const PAGE_SIZE = 50; // the API default
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
// The bulb and its filter are for people who may read tickets at some site (the list is the union
// over their sites; the API answers a dash for the rows of the other sites)
const canSeeTickets = computed(() => userPermissions.value.includes("ticket:read"));
const formModal = ref(null);
const filterModal = ref(null);

const page = ref(null); // {items, total, page, per_page}
const loading = ref(true);
const loadError = ref("");
let loadSeq = 0;

// ---- filters (from the URL) ----

const query = computed(() => route.query);
const level = computed(() => query.value.level ?? DEFAULT_LEVEL);
const pageNumber = computed(() => Math.max(1, Number.parseInt(query.value.page, 10) || 1));
// A bookmarked lifecycle=scrapped needs the scrapped rows, so it ticks the box
const showScrapped = computed(() => query.value.scrapped === "1" || query.value.lifecycle === "scrapped");
const hasFilters = computed(() => Object.keys(query.value).some((k) => k !== "page"));
const noUnits = computed(() => myUnits.value && !myUnits.value.all_units && myUnits.value.unit_ids.length === 0);

/**
 * Merge `changes` into the query; defaults and empty values are left out of the URL. `push`: a
 * history step (the property filter), else the entry is replaced.
 */
function update(changes, { push = false } = {}) {
  const merged = { ...query.value, ...changes };
  if (!("page" in changes)) delete merged.page; // a filter change goes back to page 1
  for (const key of Object.keys(merged)) {
    if (merged[key] === null || merged[key] === undefined || merged[key] === "") delete merged[key];
  }
  if (merged.level === DEFAULT_LEVEL) delete merged.level;
  if (merged.page === 1) delete merged.page;
  if (push) router.push({ query: merged });
  else router.replace({ query: merged });
}

const unitChoices = computed(() => {
  if (!myUnits.value) return [];
  const mine = filterableUnits(units.value, myUnits.value);
  return query.value.site_id ? mine.filter((u) => String(u.site_id) === query.value.site_id) : mine;
});
// Active categories by name, then inactive ones (marked)
const categoryChoices = computed(() => activeFirstBy(equipmentCategories.value, "name"));
// Active classes first, then inactive ones (marked); with a category, only its classes (S063)
const classChoices = computed(() => classChoicesFor(equipmentClasses.value, query.value.category_id, query.value.class_id));
// Shown with a class, or with a type_id in the URL alone, so a bookmarked type filter is never applied
// invisibly. Inactive types stay listed (marked): equipment can still carry them.
const showTypeFilter = computed(() => Boolean(query.value.class_id || query.value.type_id));
const typeChoices = computed(() => {
  const all = equipmentTypes.value ?? [];
  const shown = query.value.class_id ? all.filter((t) => String(t.class_id) === query.value.class_id) : all;
  const choices = [...shown].sort((a, b) => Number(b.active) - Number(a.active));
  // A hand-made URL can pair a class with a type of another class; list that type (last) so the applied
  // filter is visible. An unknown type_id stays unlisted: the select is blank and the list empty.
  const foreign = all.find((t) => String(t.id) === query.value.type_id);
  if (foreign && !choices.includes(foreign)) choices.push(foreign);
  return choices;
});
const typeLabel = (t) => (String(t.class_id) === query.value.class_id ? t.name : `${t.class_code} · ${t.name}`);
const lifecycleChoices = computed(() =>
  Object.entries(LIFECYCLE_LABELS).filter(([value]) => value !== "scrapped" || showScrapped.value)
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
// A class outside the new category goes, with its type; a class inside it stays
function chooseCategory(value) {
  const changes = { category_id: value };
  if (classOutsideCategory(equipmentClasses.value, value, query.value.class_id)) {
    changes.class_id = null;
    changes.type_id = null;
  }
  update(changes);
}
const categoryModel = filterModel("category_id", "", chooseCategory);
// A type belongs to one class, so choosing a class always clears the type
const classModel = filterModel("class_id", "", (value) => update({ class_id: value, type_id: null }));
const typeModel = filterModel("type_id");
// Leaving a bookmarked lifecycle=scrapped must not untick "Show scrapped" behind the user's back
function chooseLifecycle(value) {
  const changes = { lifecycle: value };
  if (query.value.lifecycle === "scrapped" && query.value.scrapped !== "1") changes.scrapped = "1";
  update(changes);
}
const lifecycleModel = filterModel("lifecycle", "", chooseLifecycle);
const criticalityModel = filterModel("criticality");
const levelModel = filterModel("level", DEFAULT_LEVEL);
const ticketsModel = filterModel("tickets");

// ---- the phone's folded filters (S064 UX-08): closed on load (D5); the count says what is set ----

const filtersOpen = ref(false);
// Each select set, Show scrapped when on, the property filter as one; not the search, the page or
// the default level.  The keys the list sends (listUrl), so a filter that does not apply is not counted.
const FILTER_KEYS = ["site_id", "unit_id", "category_id", "class_id", "type_id", "lifecycle", "criticality", "tickets"];
const filterCount = computed(() => {
  let count = FILTER_KEYS.filter((key) => query.value[key] && (key !== "tickets" || canSeeTickets.value)).length;
  if (level.value !== DEFAULT_LEVEL) count += 1;
  if (showScrapped.value) count += 1;
  if (hasProps.value) count += 1;
  return count;
});

function toggleScrapped(on) {
  const changes = { scrapped: on ? "1" : null };
  if (!on && query.value.lifecycle === "scrapped") changes.lifecycle = null;
  update(changes);
}

// ---- the property filter (S062): one key, props; the line shows whenever the URL has it ----

const hasProps = computed(() => query.value.props !== undefined && query.value.props !== null);
const propertyFilter = computed(() => decodeFilter(query.value.props));
// A hand-edited or cut bookmark: the line says so and the list is not asked (it would only refuse)
const propsUnreadable = computed(() => hasProps.value && propertyFilter.value === null);
const conditionCount = computed(() => propertyFilter.value?.rules.length ?? 0);
const filterLineText = computed(() => describeFilter(propertyFilter.value, properties.value));

function openPropertyFilter() {
  filterModal.value.open(propertyFilter.value, query.value.class_id);
}

// The first property filter at the default level also shows every level (D11)
function applyPropertyFilter(filter) {
  update(propsChanges(query.value, encodeFilter(filter)), { push: true });
}

function clearPropertyFilter() {
  update({ props: null }, { push: true });
}

// ---- search: SEARCH_DELAY_MS after the last keystroke ----

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

const { schedule: scheduleSearch } = useDebounced(applySearch);
watch(searchText, scheduleSearch);
// Back / Forward changes q without typing
watch(() => query.value.q, (q) => {
  if ((q ?? "") !== searchText.value.trim()) searchText.value = q ?? "";
});

// ---- loading ----

function listUrl() {
  const params = new URLSearchParams({ level: level.value, page: String(pageNumber.value), per_page: String(PAGE_SIZE) });
  for (const key of ["site_id", "unit_id", "category_id", "class_id", "type_id", "lifecycle", "criticality", "tickets", "q", "props"]) {
    // A bookmarked ?tickets= must not filter invisibly for a user who has no ticket column or filter
    if (key === "tickets" && !canSeeTickets.value) continue;
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
      propsUnreadable.value ? null : apiGet(listUrl()),
      ensureSites(), ensureUnits(), ensureEquipmentCategories(), ensureEquipmentClasses(), ensureEquipmentTypes(),
      ensureMyUnits(),
      // The filter line names the properties
      hasProps.value ? ensureProperties() : null,
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

// ---- ticks for QR labels (S014): kept across pages of the same filters, cleared when a filter
// or the search changes (a new filter is a new group), at most MAX_LABELS ----

const selected = ref(new Set());
const selectionHint = ref("");
const CAP_HINT = `${MAX_LABELS} labels at most — print this group first`;

// Everything in the query but the page number
const filterKey = computed(() => {
  const { page: _page, ...filters } = query.value;
  return JSON.stringify(Object.keys(filters).sort().map((k) => [k, filters[k]]));
});
watch(filterKey, () => {
  selected.value.clear();
  selectionHint.value = "";
});

const pageIds = computed(() => (page.value?.items ?? []).map((e) => e.id));
const allOnPage = computed(() => pageIds.value.length > 0 && pageIds.value.every((id) => selected.value.has(id)));

/** A refused tick: the box is unticked again, as the selection did not change. */
function refuse(event) {
  event.target.checked = false;
  selectionHint.value = CAP_HINT;
}

function toggleOne(id, event) {
  if (!event.target.checked) {
    selected.value.delete(id);
    selectionHint.value = "";
  } else if (selected.value.size >= MAX_LABELS) {
    refuse(event);
  } else {
    selected.value.add(id);
  }
}

function toggleAllOnPage(event) {
  if (!event.target.checked) {
    for (const id of pageIds.value) selected.value.delete(id);
    selectionHint.value = "";
    return;
  }
  const missing = pageIds.value.filter((id) => !selected.value.has(id));
  if (selected.value.size + missing.length > MAX_LABELS) {
    refuse(event);
    return;
  }
  for (const id of missing) selected.value.add(id);
}

// A new tab, so this list and its ticks stay as they are (base pattern § Print / Export Views)
function printLabels() {
  window.open(router.resolve(labelsPath([...selected.value])).href, "_blank");
}

// The list's filters (not the search or the level) on a printable page in a new tab (S015)
function printAssetList() {
  window.open(router.resolve(assetListPath(route.query)).href, "_blank");
}
</script>

<template>
  <div class="py-3">
    <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
      <input
        v-model="searchText"
        class="form-control search-box order-md-1"
        type="search"
        placeholder="Search code, name, model, notes…"
        aria-label="Search"
      />
      <button v-if="canEdit" class="btn btn-sm btn-primary order-md-3" @click="formModal.openCreateEquipment()">
        <i class="fa-solid fa-plus me-1"></i>Add equipment
      </button>
      <div class="w-100 d-md-none"></div>
      <button
        type="button"
        class="btn btn-outline-secondary tap-target d-md-none"
        :aria-expanded="filtersOpen"
        aria-controls="eq-filters"
        @click="filtersOpen = !filtersOpen"
      >
        <i class="fa-solid fa-filter me-1"></i>Filters ({{ filterCount }})
        <i class="fa-solid ms-1" :class="filtersOpen ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
      </button>
      <div id="eq-filters" class="filters-block" :class="{ open: filtersOpen }">
      <select v-model="siteModel" class="form-select form-select-sm w-auto" aria-label="Site">
        <option value="">All sites</option>
        <option v-for="s in sites ?? []" :key="s.id" :value="s.id">{{ s.code }}{{ s.active ? "" : " (inactive)" }}</option>
      </select>
      <select v-model="unitModel" class="form-select form-select-sm w-auto" aria-label="Unit">
        <option value="">All units</option>
        <option v-for="u in unitChoices" :key="u.id" :value="u.id">{{ u.full_code }}{{ u.active ? "" : " (inactive)" }}</option>
      </select>
      <select v-model="categoryModel" class="form-select form-select-sm w-auto" aria-label="Category">
        <option value="">All categories</option>
        <option v-for="c in categoryChoices" :key="c.id" :value="c.id">{{ c.name }}{{ c.active ? "" : " (inactive)" }}</option>
      </select>
      <select v-model="classModel" class="form-select form-select-sm w-auto" aria-label="Class">
        <option value="">All classes</option>
        <option v-for="c in classChoices" :key="c.id" :value="c.id">{{ c.code }}{{ c.active ? "" : " (inactive)" }}</option>
      </select>
      <select v-if="showTypeFilter" v-model="typeModel" class="form-select form-select-sm w-auto" aria-label="Type">
        <option value="">All types</option>
        <option v-for="t in typeChoices" :key="t.id" :value="t.id">{{ typeLabel(t) }}{{ t.active ? "" : " (inactive)" }}</option>
      </select>
      <select v-model="lifecycleModel" class="form-select form-select-sm w-auto" aria-label="Lifecycle">
        <option value="">Any lifecycle</option>
        <option v-for="[value, text] in lifecycleChoices" :key="value" :value="value">{{ text }}</option>
      </select>
      <select v-model="criticalityModel" class="form-select form-select-sm w-auto" aria-label="Criticality">
        <option value="">Any criticality</option>
        <option v-for="(text, grade) in CRITICALITY_OPTIONS" :key="grade" :value="grade">{{ text }}</option>
      </select>
      <select v-if="canSeeTickets" v-model="ticketsModel" class="form-select form-select-sm w-auto" aria-label="Tickets">
        <option v-for="[value, text] in TICKET_FILTER_CHOICES" :key="value" :value="value">{{ text }}</option>
      </select>
      <select v-model="levelModel" class="form-select form-select-sm w-auto" aria-label="Level">
        <option v-for="[value, text] in LEVEL_CHOICES" :key="value" :value="value">{{ text }}</option>
      </select>
      <button class="btn btn-sm" :class="conditionCount ? 'btn-primary' : 'btn-outline-primary'" @click="openPropertyFilter">
        <i class="fa-solid fa-sliders me-1"></i>{{ conditionCount ? `Properties (${conditionCount})` : "Filter by property" }}
      </button>
      <div class="form-check form-switch mb-0">
        <input id="eq-show-scrapped" :checked="showScrapped" class="form-check-input" type="checkbox" @change="toggleScrapped($event.target.checked)" />
        <label class="form-check-label small" for="eq-show-scrapped">Show scrapped</label>
      </div>
      </div>
      <!-- The office's buttons: hidden on a phone (S064 UX-08, D12) -->
      <button class="btn btn-sm btn-outline-primary ms-auto d-none d-md-inline-block order-md-2" :disabled="selected.size === 0" @click="printLabels">
        <i class="fa-solid fa-qrcode me-1"></i>Print labels ({{ selected.size }})
      </button>
      <button class="btn btn-sm btn-outline-primary d-none d-md-inline-block order-md-2" @click="printAssetList">
        <i class="fa-solid fa-list-check me-1"></i>Print asset list
      </button>
    </div>
    <div v-if="hasProps" class="d-flex align-items-center gap-2 mb-2">
      <button type="button" class="btn btn-link btn-sm p-0 text-start text-decoration-none" @click="openPropertyFilter">
        {{ filterLineText }}
      </button>
      <button
        type="button"
        class="btn btn-sm btn-outline-secondary"
        title="Clear property filter"
        aria-label="Clear property filter"
        @click="clearPropertyFilter"
      >
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>
    <div v-if="selectionHint" class="text-warning-emphasis small mb-2">{{ selectionHint }}</div>

    <div v-if="loading && page" class="text-secondary small mb-1">Loading…</div>
    <div v-if="propsUnreadable" class="alert alert-warning">The property filter cannot be read. Clear it and make it again.</div>
    <div v-else-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-sm btn-outline-danger" @click="load">Retry</button>
    </div>
    <div v-else-if="loading && !page" class="text-secondary">Loading…</div>
    <div v-else-if="noUnits" class="text-secondary">{{ NO_UNITS_TEXT }}</div>
    <div v-else-if="page && page.total === 0" class="text-secondary">
      {{ hasFilters ? "No equipment matches these filters." : "No equipment yet." }}
    </div>
    <div v-else-if="page && page.items.length === 0" class="text-secondary">No equipment on this page.</div>
    <template v-else-if="page">
    <div class="table-responsive d-none d-md-block">
      <table class="table table-sm table-hover align-middle mb-0">
        <thead>
          <tr>
            <th class="tick-cell">
              <input
                class="form-check-input"
                type="checkbox"
                :checked="allOnPage"
                title="Select all on this page"
                aria-label="Select all on this page"
                @change="toggleAllOnPage"
              />
            </th>
            <th v-if="canSeeTickets" class="tick-cell text-center">
              <i class="fa-solid fa-ticket" title="Tickets" role="img" aria-label="Tickets"></i>
            </th>
            <th>Code</th><th>Name</th><th>Class</th><th>Model</th><th>{{ level === "equipment" ? "Unit" : "Path" }}</th>
            <th>Crit.</th><th>Lifecycle</th><th class="text-end">Parts</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="e in page.items"
            :key="e.id"
            data-test="equipment-row"
            role="link"
            style="cursor: pointer"
            :class="{ 'text-secondary': e.lifecycle === 'scrapped' }"
            @click="openNode(e.id)"
          >
            <td class="tick-cell" @click.stop>
              <input
                class="form-check-input"
                type="checkbox"
                :checked="selected.has(e.id)"
                :aria-label="`Select ${e.code} for labels`"
                @change="toggleOne(e.id, $event)"
              />
            </td>
            <td v-if="canSeeTickets" class="tick-cell text-center">
              <TicketLight v-if="e.lifecycle !== 'scrapped'" :light="e.ticket_light" />
            </td>
            <td><router-link :to="`/equipment/${e.id}`" class="fw-semibold" @click.stop>{{ e.code }}</router-link></td>
            <td>{{ e.name }}</td>
            <td>{{ e.class_code }}<span v-if="e.type_name" class="text-secondary"> · {{ e.type_name }}</span></td>
            <!-- So a row found by "GA37" shows why (S012); a component-unit may have no model (S033) -->
            <td>{{ e.model_label ?? "—" }}</td>
            <td>{{ level === "equipment" ? e.unit : e.full_path }}</td>
            <td><CriticalityBadge :grade="e.effective_criticality" /></td>
            <td><LifecycleBadge :lifecycle="e.lifecycle" /></td>
            <td class="text-end">{{ e.part_count }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <!-- A phone: the same rows as two-line cards, each a link to the equipment page (S064 UX-08) -->
    <div class="list-group d-md-none">
      <router-link
        v-for="e in page.items"
        :key="e.id"
        :to="`/equipment/${e.id}`"
        data-test="equipment-row"
        class="list-group-item list-group-item-action"
        :class="{ 'text-secondary': e.lifecycle === 'scrapped' }"
      >
        <div class="d-flex align-items-center gap-2 min-w-0">
          <TicketLight v-if="canSeeTickets && e.lifecycle !== 'scrapped'" :light="e.ticket_light" />
          <span class="fw-semibold text-nowrap">{{ e.code }}</span>
          <span class="text-truncate">{{ e.name }}</span>
        </div>
        <div class="d-flex flex-wrap align-items-center gap-2 mt-1 small">
          <LifecycleBadge :lifecycle="e.lifecycle" />
          <CriticalityBadge :grade="e.effective_criticality" />
          <span class="text-secondary text-break">{{ level === "equipment" ? e.unit : e.full_path }}</span>
        </div>
      </router-link>
    </div>
    </template>
    <PagerBar
      v-if="page && !loadError"
      :page="pageNumber"
      :total="page.total"
      :per-page="PAGE_SIZE"
      @page="update({ page: $event })"
    />

    <EquipmentFormModal ref="formModal" @saved="({ result }) => openNode(result.id)" />
    <PropertyFilterModal ref="filterModal" @apply="applyPropertyFilter" />
  </div>
</template>

<style scoped>
.tick-cell {
  width: 2rem;
}
.min-w-0 {
  min-width: 0;
}
/* A phone: the search fills the first line beside Add equipment; the filters fold (S064 UX-08) */
.search-box {
  flex: 1 1 0;
  min-width: 0;
}
.filters-block {
  display: none;
  width: 100%;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.filters-block.open {
  display: flex;
}
/* From md up: the filters sit inline in the toolbar as before, and the search is the small one */
@media (min-width: 768px) {
  .filters-block,
  .filters-block.open {
    display: contents;
  }
  /* The values of Bootstrap 5.3's .form-control-sm, copied: the box carries its own class below md */
  .search-box {
    flex: 0 1 auto;
    width: auto;
    min-height: calc(1.5em + 0.5rem + calc(var(--bs-border-width) * 2));
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    border-radius: var(--bs-border-radius-sm);
  }
}
</style>
