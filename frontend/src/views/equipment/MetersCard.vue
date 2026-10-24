<script setup>
/**
 * The Meters card on the equipment page (S038 § 1.2, § 1.3): the node's meters — its model's,
 * marked "From the model", and its own, "This machine only" — each with what a good reading
 * is (a gauge's limits in force, a Yes / No meter's expected answer). Editors add own meters,
 * set a gauge's limits and remove own meters (asked first); a model meter is removed in
 * Masters. The list comes from its own API call, so the node detail is unchanged.
 *
 * Emits @changed after a write, so the page reloads the node's history.
 */
import { ref, watch } from "vue";
import { apiGet, apiPut } from "../../api";
import { goodReadingText, SOURCE_LABELS, unitAndKind } from "../../utils/meterLabels";
import NodeMeterFormModal from "./NodeMeterFormModal.vue";

const props = defineProps({
  node: { type: Object, required: true },
  canEdit: { type: Boolean, default: false },
});
const emit = defineEmits(["changed"]);

const meters = ref(null); // null while loading
const loadError = ref("");
const confirmingId = ref(null); // the meter type whose Remove asks first
const removing = ref(false);
const removeError = ref("");
const meterModal = ref(null);
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
  load();
}, { immediate: true });

function saved(rows) {
  meters.value = rows;
  emit("changed");
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
          <span v-if="canEdit && confirmingId !== meter.meter_type.id" class="ms-auto text-nowrap">
            <button v-if="meter.meter_type.kind === 'gauge'" class="btn btn-sm btn-outline-secondary me-1" @click="meterModal.openLimits(node, meter)">
              Set limits
            </button>
            <button v-if="meter.source === 'node'" class="btn btn-sm btn-outline-danger" @click="askRemove(meter)">Remove</button>
          </span>
        </div>
        <div v-if="goodReadingText(meter)" class="small">
          {{ goodReadingText(meter) }}<span v-if="meter.overridden" class="text-secondary"> · set on this machine</span>
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
  </div>
</template>
