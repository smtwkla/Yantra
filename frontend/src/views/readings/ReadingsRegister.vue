<script setup>
/**
 * The meter reading register (docs/steps/S050-reading-register/1-brief.md § 1.3–§ 1.7): every
 * active reading of one node as a table, like the log book at the machine. A row per reading
 * time (one exact minute), newest first; a column per meter of the node, then the meters no
 * longer on it that still have readings. The rows and columns come shaped from
 * GET /api/equipment/<id>/readings/register; this screen only shows them.
 *
 * - The node and the ticked meters live in the URL (?tab=register&node=<id>&meters=3,7; absent
 *   meters = all), so a link from the Meters card, a bookmark and Back keep them. The ticks shown
 *   are the answer's `shown` (a stale id in the URL is dropped by the server, BR1-03).
 * - No node: the shared equipment search (EquipmentPicker). A node: its card with Change and
 *   Open equipment page, the column chooser, the table and Show more (30 rows a page).
 * - The time column stays on the left; the meter columns scroll sideways inside the frame.
 *
 * Mounted once and kept while the Sheet tab shows (ReadingsView.vue): `active` is false then,
 * and the URL is not read.
 */
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../../api";
import EquipmentPicker from "../../components/EquipmentPicker.vue";
import { formatDateTime } from "../../utils/datetime";
import {
  formatReading, meterHeader, parseRegisterQuery, readingBadgeClass, readingBadges, registerQuery,
} from "../../utils/meterLabels";

const props = defineProps({
  active: { type: Boolean, default: true },
});

const LOAD_FAILED = "Readings could not be loaded. Try again in a minute.";
const NOT_FOUND = "This machine was not found, or you have no access to it. Find another machine.";

const route = useRoute();
const router = useRouter();

const register = ref(null); // the last answer: {node, columns, shown, total, page, per_page}
const rows = ref([]); // every row loaded so far, newest first
const loading = ref(false);
const loadError = ref("");
const failedPage = ref(1); // the page whose load failed: Try again asks for it, and its line sits where the user is
const notFound = ref(false);
const chooserOpen = ref(false);
let loadSeq = 0;

const wanted = computed(() => parseRegisterQuery(route.query));
const nodeId = computed(() => wanted.value.nodeId);
const shownColumns = computed(() => {
  const shown = new Set(register.value?.shown ?? []);
  return (register.value?.columns ?? []).filter((c) => shown.has(c.meter_type.id));
});
const allShown = computed(() => register.value && register.value.shown.length === register.value.columns.length);
const chooserLabel = computed(() => (allShown.value
  ? "Meters: All"
  : `Meters: ${register.value.shown.length} of ${register.value.columns.length}`));
// By the server's pages, not by the rows shown: a reading logged between two pages leaves a row out of
// the count, and Show more must not stay on screen for it
const canShowMore = computed(() => register.value && register.value.page * register.value.per_page < register.value.total);

function registerUrl(id, meterIds, page) {
  const params = new URLSearchParams({ page: String(page) });
  if (meterIds) params.set("meter_type_ids", meterIds.join(","));
  return `/api/equipment/${id}/readings/register?${params}`;
}

async function load(page) {
  const seq = ++loadSeq;
  const { nodeId: id, meterIds } = wanted.value;
  loading.value = true;
  loadError.value = "";
  notFound.value = false;
  try {
    const result = await apiGet(registerUrl(id, meterIds, page));
    if (seq !== loadSeq) return;
    // A reading logged between two pages shifts the minutes by one: never show a time twice (§ 5.3.5)
    const kept = page === 1 ? [] : rows.value;
    const seen = new Set(kept.map((r) => r.taken_at));
    rows.value = [...kept, ...result.rows.filter((r) => !seen.has(r.taken_at))];
    register.value = result;
  } catch (err) {
    if (seq !== loadSeq) return;
    if (page === 1) register.value = null;
    // 403 cannot happen for a site role today (equipment:read is every role's): the 404 words (BR1-12)
    if (err.status === 404 || err.status === 403) notFound.value = true;
    else {
      loadError.value = LOAD_FAILED;
      failedPage.value = page;
    }
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

/** From the first page. Another node starts from an empty screen; other ticks keep the table until the answer. */
function reload(sameNode) {
  if (!sameNode) {
    register.value = null;
    rows.value = [];
  }
  if (nodeId.value !== null) {
    load(1);
    return;
  }
  loadSeq++; // an answer still on its way is for a node no longer picked
  loading.value = false;
}

// Another node or other meters in the URL: from the first page. Not while the Sheet tab shows,
// nor on the way to another page; back from the Sheet tab to the same URL keeps what is loaded.
let loadedFor = null; // the URL's node and meters the rows are for
watch(() => (props.active && route.name === "readings" ? `${route.query.node}|${route.query.meters}` : null), (key) => {
  if (key === null || key === loadedFor) return;
  const sameNode = loadedFor?.split("|")[0] === String(route.query.node);
  if (!sameNode) chooserOpen.value = false;
  loadedFor = key;
  reload(sameNode);
}, { immediate: true });

function go(id, meterIds = null) {
  router.replace({ query: registerQuery(id, meterIds) });
}

const pick = (id) => go(id);
const change = () => go(null);

function isTicked(column) {
  return register.value.shown.includes(column.meter_type.id);
}

// The last tick cannot be cleared: its box is disabled
const isLastTick = (column) => isTicked(column) && register.value.shown.length === 1;

function toggle(column) {
  const id = column.meter_type.id;
  const ticked = new Set(register.value.shown);
  if (!ticked.delete(id)) ticked.add(id);
  const ids = register.value.columns.map((c) => c.meter_type.id).filter((i) => ticked.has(i));
  go(nodeId.value, ids.length === register.value.columns.length ? null : ids);
}

const showAll = () => go(nodeId.value);

const cellText = (cell, column) => formatReading(cell.value, column.meter_type, { unit: false });
</script>

<template>
  <div class="py-3">
    <!-- One picker, hidden while a node shows (not unmounted): Change brings back the search text and matches (CR1-01) -->
    <div v-show="nodeId === null || notFound">
      <div v-if="notFound && nodeId !== null" class="alert alert-warning" role="alert">{{ NOT_FOUND }}</div>
      <EquipmentPicker @pick="pick" />
      <p v-if="nodeId === null" class="text-secondary mt-3" data-testid="register-empty">Find a machine or part to see its readings.</p>
    </div>

    <template v-if="nodeId !== null && !notFound">
      <div v-if="loadError && failedPage === 1" class="alert alert-danger d-flex justify-content-between align-items-center gap-2">
        <span>{{ loadError }}</span>
        <button type="button" class="btn btn-outline-danger" @click="load(failedPage)">Try again</button>
      </div>
      <div v-if="loading && !register" class="text-secondary">Loading…</div>

      <template v-if="register">
        <div class="card mb-3" data-testid="register-node">
          <div class="card-body d-flex flex-wrap align-items-center gap-2">
            <div class="flex-grow-1 text-break">
              <div class="fw-semibold">{{ register.node.code }} — {{ register.node.name }}</div>
              <div class="small text-secondary">{{ register.node.full_path }}</div>
            </div>
            <router-link class="btn btn-outline-secondary" :to="`/equipment/${register.node.id}`">Open equipment page</router-link>
            <button type="button" class="btn btn-outline-secondary" @click="change">Change</button>
          </div>
        </div>

        <p v-if="register.columns.length === 0" class="text-secondary">
          This machine has no meters. Engineers add meters in Masters › Models or on the machine's page.
        </p>

        <template v-else>
          <div class="mb-2">
            <button
              type="button"
              class="btn btn-outline-secondary"
              :aria-expanded="chooserOpen"
              :aria-controls="chooserOpen ? 'register-chooser' : null"
              @click="chooserOpen = !chooserOpen"
            >
              {{ chooserLabel }} <i class="fa-solid ms-1" :class="chooserOpen ? 'fa-chevron-up' : 'fa-chevron-down'" aria-hidden="true"></i>
            </button>
            <div v-if="chooserOpen" id="register-chooser" class="card card-body mt-2 py-2" data-testid="register-chooser">
              <div v-for="column in register.columns" :key="column.meter_type.id" class="d-flex align-items-center gap-2 chooser-row">
                <input
                  :id="`register-meter-${column.meter_type.id}`"
                  class="form-check-input m-0"
                  type="checkbox"
                  :checked="isTicked(column)"
                  :disabled="isLastTick(column) || loading"
                  @change="toggle(column)"
                />
                <label class="form-check-label flex-grow-1 py-2" :for="`register-meter-${column.meter_type.id}`">
                  {{ meterHeader(column.meter_type) }}<span v-if="!column.in_force" class="text-secondary small"> · No longer on this machine</span>
                </label>
              </div>
              <button type="button" class="btn btn-link px-0 text-start" :disabled="allShown || loading" @click="showAll">Show all</button>
            </div>
          </div>

          <p v-if="register.total === 0" class="text-secondary">No readings yet.</p>
          <template v-else>
            <div class="register-frame border rounded" data-testid="register-frame">
              <table class="table table-sm mb-0 register-table">
                <thead>
                  <tr>
                    <th scope="col" class="time-cell">Time</th>
                    <th v-for="column in shownColumns" :key="column.meter_type.id" scope="col" class="meter-cell">
                      {{ meterHeader(column.meter_type) }}
                      <div v-if="!column.in_force" class="small text-secondary fw-normal">No longer on this machine</div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in rows" :key="row.taken_at" data-testid="register-row">
                    <th scope="row" class="time-cell fw-normal">{{ formatDateTime(row.taken_at) }}</th>
                    <td v-for="column in shownColumns" :key="column.meter_type.id" class="meter-cell">
                      <template v-if="row.cells[column.meter_type.id]">
                        <span>{{ cellText(row.cells[column.meter_type.id], column) }}</span>
                        <span
                          v-for="badge in readingBadges(row.cells[column.meter_type.id])"
                          :key="badge"
                          class="badge ms-1"
                          :class="readingBadgeClass(badge)"
                        >{{ badge }}</span>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="loadError && failedPage > 1" class="alert alert-danger d-flex justify-content-between align-items-center gap-2 mt-2" data-testid="register-more-error">
              <span>{{ loadError }}</span>
              <button type="button" class="btn btn-outline-danger" @click="load(failedPage)">Try again</button>
            </div>
            <button v-else-if="canShowMore && !loadError" type="button" class="btn btn-link px-0 mt-1 show-more" :disabled="loading" @click="load(register.page + 1)">
              Show more
            </button>
          </template>
        </template>
      </template>
    </template>
  </div>
</template>

<style scoped>
/* The meter columns scroll sideways inside the frame, never the page (§ 1.5) */
.register-frame {
  max-width: 100%;
  overflow-x: auto;
}

.register-table th,
.register-table td {
  white-space: nowrap;
  vertical-align: top;
}

/* The time column stays in view while the meters scroll */
.time-cell {
  position: sticky;
  left: 0;
  z-index: 1;
  background-color: var(--bs-body-bg);
  border-right: 1px solid var(--bs-border-color);
}

.meter-cell {
  text-align: right;
}

/* A tap target of at least 44 px on a floor screen */
.chooser-row {
  min-height: 44px;
}

.show-more {
  min-height: 44px;
}
</style>
