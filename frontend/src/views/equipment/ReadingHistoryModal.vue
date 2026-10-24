<script setup>
/**
 * A meter's History (S039 § 1.3, § 1.4): its readings, newest first, a page at a time (the API's default size) with
 * Show more. Each row: time, value, its marks (High / Low / Not OK / Reset), who
 * entered it and the note. Remove shows only where the API says the user may remove the reading
 * (can_remove: equipment:edit at the node's site, not a reset with later readings), and asks first
 * in the row. Holders of equipment:edit may show the removed readings too.
 *
 * The parent calls open(node, meter) through a template ref; @changed after a removal, so the card
 * reloads its last readings.
 */
import { computed, ref, watch } from "vue";
import { apiDelete, apiGet } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { formatDateTime } from "../../utils/datetime";
import { formatReading, readingBadges, RESET_LABEL } from "../../utils/meterLabels";

defineProps({
  canSeeRemoved: { type: Boolean, default: false },
});
const emit = defineEmits(["changed"]);

const modal = ref(null);
const node = ref(null);
const meter = ref(null);
const items = ref([]);
const total = ref(0);
const loading = ref(false);
const loadError = ref("");
const showRemoved = ref(false);
const confirmingId = ref(null); // the reading whose Remove asks first
const removing = ref(false);
const removeError = ref("");
let loadSeq = 0;
const page = ref(0); // the last page loaded

const meterType = computed(() => meter.value?.meter_type ?? null);
const canShowMore = computed(() => items.value.length < total.value);

async function load(nextPage) {
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const query = new URLSearchParams({ meter_type_id: meterType.value.id, page: nextPage });
    if (showRemoved.value) query.set("include_removed", "1");
    const result = await apiGet(`/api/equipment/${node.value.id}/readings?${query}`);
    if (seq !== loadSeq) return;
    // A reading logged meanwhile shifts the pages by one: never show a row twice
    const kept = nextPage === 1 ? [] : items.value;
    const seen = new Set(kept.map((r) => r.id));
    items.value = [...kept, ...result.items.filter((r) => !seen.has(r.id))];
    total.value = result.total;
    page.value = nextPage;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

function open(target, targetMeter) {
  node.value = target;
  meter.value = targetMeter;
  items.value = [];
  total.value = 0;
  showRemoved.value = false;
  confirmingId.value = null;
  removeError.value = "";
  modal.value.open();
  load(1);
}

// The switch reloads from the first page; open() sets it back to false before its own load
watch(showRemoved, (shown, before) => {
  if (shown === before || !meter.value) return;
  confirmingId.value = null;
  load(1);
});

function askRemove(reading) {
  confirmingId.value = reading.id;
  removeError.value = "";
}

async function remove(reading) {
  removing.value = true;
  removeError.value = "";
  try {
    await apiDelete(`/api/equipment/${node.value.id}/readings/${reading.id}`);
    confirmingId.value = null;
    emit("changed");
    await load(1);
  } catch (err) {
    removeError.value = err.message;
  } finally {
    removing.value = false;
  }
}

const badgeClass = (label) => (label === RESET_LABEL ? "text-bg-info" : "text-bg-warning");

defineExpose({ open });
</script>

<template>
  <FormModal ref="modal" :title="meterType ? `History · ${meterType.name}` : 'History'" close-only>
    <div v-if="canSeeRemoved" class="form-check form-switch mb-2">
      <input id="readings-show-removed" v-model="showRemoved" class="form-check-input" type="checkbox" role="switch" />
      <label class="form-check-label" for="readings-show-removed">Show removed</label>
    </div>
    <div v-if="loadError" class="text-danger">Readings could not be loaded: {{ loadError }}</div>
    <div v-else-if="loading && items.length === 0" class="text-secondary">Loading…</div>
    <div v-else-if="items.length === 0" class="text-secondary">No readings.</div>
    <ul v-if="items.length" class="list-group list-group-flush">
      <li v-for="reading in items" :key="reading.id" class="list-group-item px-0" data-testid="reading-row">
        <div class="d-flex flex-wrap align-items-center gap-2">
          <span class="text-secondary small">{{ formatDateTime(reading.taken_at) }}</span>
          <span class="fw-semibold" :class="{ 'text-decoration-line-through': reading.removed_at }">{{ formatReading(reading.value, meterType) }}</span>
          <span v-for="badge in readingBadges(reading)" :key="badge" class="badge" :class="badgeClass(badge)">{{ badge }}</span>
          <span v-if="reading.removed_at" class="badge text-bg-secondary">Removed</span>
          <button
            v-if="reading.can_remove && confirmingId !== reading.id"
            type="button"
            class="btn btn-sm btn-outline-danger ms-auto"
            @click="askRemove(reading)"
          >
            Remove
          </button>
        </div>
        <div class="small text-secondary">
          {{ reading.created_by }}<template v-if="reading.note"> · {{ reading.note }}</template>
        </div>
        <div v-if="reading.removed_at" class="small text-secondary">
          Removed {{ formatDateTime(reading.removed_at) }} · {{ reading.removed_by }}
        </div>
        <template v-if="confirmingId === reading.id">
          <div class="d-flex flex-wrap align-items-center justify-content-end gap-2 mt-2">
            <span>
              Remove the reading of {{ formatDateTime(reading.taken_at) }} ({{ formatReading(reading.value, meterType) }})?
              It no longer counts. You cannot undo this.
            </span>
            <button type="button" class="btn btn-sm btn-danger" :disabled="removing" @click="remove(reading)">Remove</button>
            <button type="button" class="btn btn-sm btn-outline-secondary" @click="confirmingId = null">Keep</button>
          </div>
          <div v-if="removeError" class="text-danger small mt-1">{{ removeError }}</div>
        </template>
      </li>
    </ul>
    <button v-if="canShowMore && !loadError" type="button" class="btn btn-link px-0" :disabled="loading" @click="load(page + 1)">
      Show more
    </button>
  </FormModal>
</template>
