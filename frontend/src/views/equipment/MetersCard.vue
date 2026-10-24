<script setup>
/**
 * The Meters card on the equipment page (S038 § 1.2, § 1.3): the node's meters — its model's,
 * marked "From the model", and its own, "This machine only" — each with what a good reading
 * is (a gauge's limits in force, a Yes / No meter's expected answer). Editors add own meters,
 * set a gauge's limits and remove own meters (asked first); a model meter is removed in
 * Masters. The list comes from its own API call, so the node detail is unchanged.
 *
 * Readings (S039 § 1.3): each meter's last reading, "12,345.6 h · 23-10-2026 18:00" with a
 * High / Low / Not OK mark, opens its History; Log reading (reading:log holders) opens the
 * reading dialog. After a save outside what is good, the card says so on the meter's row.
 *
 * Emits @changed after a meter write, so the page reloads the node's history (a reading writes
 * no equipment history).
 */
import { ref, watch } from "vue";
import { apiGet, apiPut } from "../../api";
import { formatDateTime } from "../../utils/datetime";
import {
  formatReading, goodReadingText, LIMIT_STATE_LABELS, savedMessage, SOURCE_LABELS, unitAndKind,
} from "../../utils/meterLabels";
import NodeMeterFormModal from "./NodeMeterFormModal.vue";
import ReadingFormModal from "./ReadingFormModal.vue";
import ReadingHistoryModal from "./ReadingHistoryModal.vue";

const props = defineProps({
  node: { type: Object, required: true },
  canEdit: { type: Boolean, default: false },
  canLog: { type: Boolean, default: false },
  // equipment:edit at the node's site, scrapped or not: History may show the removed readings
  canSeeRemoved: { type: Boolean, default: false },
});
const emit = defineEmits(["changed"]);

const meters = ref(null); // null while loading
const loadError = ref("");
const confirmingId = ref(null); // the meter type whose Remove asks first
const removing = ref(false);
const removeError = ref("");
const meterModal = ref(null);
const readingModal = ref(null);
const historyModal = ref(null);
const notices = ref({}); // meter type id -> "Saved. Above the limit of 60 °C." after a save
let loadSeq = 0;

async function load() {
  const seq = ++loadSeq;
  loadError.value = "";
  try {
    const rows = await apiGet(`/api/equipment/${props.node.id}/meters`);
    if (seq === loadSeq) meters.value = rows;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  }
}

// Another node, or this node's model changed (its meters follow the model, § 1.6).  A
// multi-source watch compares each value, so a page reload that replaces `node` with the same
// id and model does not blank the card.
watch([() => props.node.id, () => props.node.model_id], () => {
  meters.value = null;
  confirmingId.value = null;
  notices.value = {};
  load();
}, { immediate: true });

function saved(rows) {
  meters.value = rows;
  emit("changed");
}

function openLog(meter) {
  notices.value = { ...notices.value, [meter.meter_type.id]: null };
  readingModal.value.open(props.node, meter);
}

// The dialog has closed; the card reloads its meters (a back-dated reading is not the last), then
// words the message with the limits of that reload, not of the list loaded before the save: an
// engineer may have changed them meanwhile (CR1-06).
async function readingSaved({ meter, reading }) {
  await load();
  const current = meters.value?.find((m) => m.meter_type.id === meter.meter_type.id) ?? meter;
  notices.value = { ...notices.value, [meter.meter_type.id]: savedMessage(current, reading) };
}

function lastText(meter) {
  return `${formatReading(meter.last.value, meter.meter_type)} · ${formatDateTime(meter.last.taken_at)}`;
}

function askRemove(meter) {
  confirmingId.value = meter.meter_type.id;
  removeError.value = "";
}

async function remove(meter) {
  removing.value = true;
  removeError.value = "";
  try {
    const rows = await apiPut(`/api/equipment/${props.node.id}/meters/${meter.meter_type.id}`, { active: false });
    confirmingId.value = null;
    saved(rows);
  } catch (err) {
    removeError.value = err.message;
  } finally {
    removing.value = false;
  }
}
</script>

<template>
  <div class="card mt-3">
    <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
      <span>Meters</span>
      <button v-if="canEdit" class="btn btn-sm btn-outline-primary" :disabled="meters === null" @click="meterModal.openAdd(node, meters)">
        <i class="fa-solid fa-plus me-1"></i>Add meter
      </button>
    </div>
    <div v-if="loadError" class="card-body text-danger">Meters could not be loaded: {{ loadError }}</div>
    <div v-else-if="meters === null" class="card-body text-secondary">Loading…</div>
    <div v-else-if="meters.length === 0" class="card-body text-secondary">No meters.</div>
    <ul v-else class="list-group list-group-flush">
      <li v-for="meter in meters" :key="meter.meter_type.id" class="list-group-item" data-testid="node-meter">
        <div class="d-flex flex-wrap align-items-center gap-2">
          <span class="fw-semibold">{{ meter.meter_type.name }}</span>
          <span class="text-secondary small">{{ unitAndKind(meter.meter_type) }}</span>
          <span class="badge" :class="meter.source === 'model' ? 'text-bg-light border' : 'text-bg-info'">{{ SOURCE_LABELS[meter.source] }}</span>
          <span v-if="(canLog || canEdit) && confirmingId !== meter.meter_type.id" class="ms-auto d-flex flex-wrap justify-content-end gap-1">
            <button v-if="canLog" class="btn btn-outline-primary touch-target" @click="openLog(meter)">Log reading</button>
            <template v-if="canEdit">
              <button v-if="meter.meter_type.kind === 'gauge'" class="btn btn-sm btn-outline-secondary" @click="meterModal.openLimits(node, meter)">
                Set limits
              </button>
              <button v-if="meter.source === 'node'" class="btn btn-sm btn-outline-danger" @click="askRemove(meter)">Remove</button>
            </template>
          </span>
        </div>
        <div v-if="goodReadingText(meter)" class="small">
          {{ goodReadingText(meter) }}<span v-if="meter.overridden" class="text-secondary"> · set on this machine</span>
        </div>
        <button
          v-if="meter.last"
          type="button"
          class="btn btn-link py-2 px-0 mt-1 w-100 d-flex touch-target align-items-center gap-2 text-start text-decoration-none text-body"
          data-testid="last-reading"
          @click="historyModal.open(node, meter)"
        >
          <span class="visually-hidden">History:</span>
          <span>{{ lastText(meter) }}</span>
          <span v-if="meter.last.limit_state" class="badge text-bg-warning">{{ LIMIT_STATE_LABELS[meter.last.limit_state] }}</span>
          <i class="fa-solid fa-chevron-right ms-auto text-secondary" aria-hidden="true"></i>
        </button>
        <div v-else class="small text-secondary mt-1">No readings yet</div>
        <div v-if="notices[meter.meter_type.id]" class="small fw-semibold text-warning-emphasis mt-1" role="status">
          {{ notices[meter.meter_type.id] }}
        </div>
        <div v-if="canEdit && meter.source === 'model'" class="small text-secondary">
          Comes from the model {{ node.model_label }}. Remove it in Masters › Models, or change this machine's model.
        </div>
        <template v-if="confirmingId === meter.meter_type.id">
          <div class="d-flex flex-wrap align-items-center justify-content-end gap-2 mt-2">
            <span>Remove {{ meter.meter_type.name }} from this machine? Readings stay in history.</span>
            <button class="btn btn-sm btn-danger" :disabled="removing" @click="remove(meter)">Remove</button>
            <button class="btn btn-sm btn-outline-secondary" @click="confirmingId = null">Keep</button>
          </div>
          <div v-if="removeError" class="text-danger small mt-1">{{ removeError }}</div>
        </template>
      </li>
    </ul>
    <NodeMeterFormModal ref="meterModal" @saved="saved" />
    <ReadingFormModal ref="readingModal" @saved="readingSaved" />
    <ReadingHistoryModal ref="historyModal" :can-see-removed="canSeeRemoved" @changed="load" />
  </div>
</template>

<style scoped>
/* A glove on a floor screen (U3): at least 44 px high */
.touch-target {
  min-height: 44px;
}
</style>
