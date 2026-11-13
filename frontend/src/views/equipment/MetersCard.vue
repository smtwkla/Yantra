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
 * Open register (S050 § 1.4) opens /readings?tab=register&node=<id>: every reading of the node as
 * a table. It shows while the node has a meter in force.
 *
 * Emits @changed after a meter write, so the page reloads the node's history (a reading writes
 * no equipment history).
 *
 * Meter links (S104 A1.6.7): a part (not a machine) may use the meter of a node above it. A linked
 * meter is a row among the others, badge "From PR-07", with the source's limits and last reading
 * (its History opens the source's readings) and "Read on PR-07 — Press 7. Log readings there.":
 * no Log reading, no Set limits. A link not in use says why. Editors get *Use a meter from above*
 * in the header and *Remove link* on the row (asked first, naming the PM plans that use it); an own
 * meter's Remove question names the parts that link it. Open register shows while the node has a
 * meter of its own.
 */
import { computed, ref, watch } from "vue";
import { apiDelete, apiGet, apiPut } from "../../api";
import { formatDateTime } from "../../utils/datetime";
import {
  formatReading, goodReadingText, LIMIT_STATE_LABELS, linkedByText, meterRowKey, notInUseText, registerQuery,
  removeLinkQuestion, savedMessage, sourceBadge, unitAndKind,
} from "../../utils/meterLabels";
import MeterLinkDialog from "./MeterLinkDialog.vue";
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
const confirmingKey = ref(null); // the row (meterRowKey) whose Remove or Remove link asks first
const removing = ref(false);
const removeError = ref("");
const meterModal = ref(null);
const readingModal = ref(null);
const historyModal = ref(null);
const linkModal = ref(null);
const linkOpening = ref(false);
const linkError = ref("");
const notices = ref({}); // meter type id -> "Saved. Above the limit of 60 °C." after a save
let loadSeq = 0;

const isLinked = (meter) => meter.source === "linked";
// The node's own and model meters: the register and the Add meter dialog's list
const ownMeters = computed(() => (meters.value ?? []).filter((m) => !isLinked(m)));
// A part has a node above it; a machine has none (A1.6.1)
const isPart = computed(() => props.node.level !== "equipment");

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

// Another node, or this node's model changed (its meters follow the model, § 1.6), or its parent
// (a move may remove its meter links, S104 A1.6.4).  A multi-source watch compares each value, so
// a page reload that replaces `node` with the same id, model and parent does not blank the card.
watch([() => props.node.id, () => props.node.model_id, () => props.node.parent_id], () => {
  meters.value = null;
  confirmingKey.value = null;
  notices.value = {};
  linkError.value = "";
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

// A linked meter's History shows the source's readings: the dialog reads only the node's id
function openHistory(meter) {
  historyModal.value.open(isLinked(meter) ? meter.linked_from : props.node, meter);
}

function askRemove(meter) {
  confirmingKey.value = meterRowKey(meter);
  removeError.value = "";
}

// Remove (an own meter: set inactive) or Remove link (the link row goes), after the question in the row
async function remove(meter) {
  removing.value = true;
  removeError.value = "";
  try {
    const url = `/api/equipment/${props.node.id}`;
    const rows = isLinked(meter)
      ? await apiDelete(`${url}/meter-links/${meter.meter_type.id}`)
      : await apiPut(`${url}/meters/${meter.meter_type.id}`, { active: false });
    confirmingKey.value = null;
    saved(rows);
  } catch (err) {
    removeError.value = err.message;
  } finally {
    removing.value = false;
  }
}

// The choices first, so the dialog opens with the one choice picked when there is only one
async function openLink() {
  linkOpening.value = true;
  linkError.value = "";
  try {
    const { items } = await apiGet(`/api/equipment/${props.node.id}/meter-links/choices`);
    linkModal.value.open(items);
  } catch (err) {
    linkError.value = err.message;
  } finally {
    linkOpening.value = false;
  }
}
</script>

<template>
  <div class="card mt-3">
    <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
      <span>Meters</span>
      <span class="d-flex flex-wrap gap-1">
        <!-- S050: every reading of this node as a table; shown while a meter of its own is in force (BR1-15; A1) -->
        <router-link v-if="ownMeters.length" class="btn btn-outline-secondary touch-target" :to="{ path: '/readings', query: registerQuery(node.id) }">
          <i class="fa-solid fa-table me-1"></i>Open register
        </router-link>
        <button v-if="canEdit && isPart" class="btn btn-sm btn-outline-primary" :disabled="meters === null || linkOpening" @click="openLink">
          <i class="fa-solid fa-link me-1"></i>Use a meter from above
        </button>
        <button v-if="canEdit" class="btn btn-sm btn-outline-primary" :disabled="meters === null" @click="meterModal.openAdd(node, meters)">
          <i class="fa-solid fa-plus me-1"></i>Add meter
        </button>
      </span>
    </div>
    <div v-if="linkError" class="card-body text-danger py-2">The meters above could not be loaded: {{ linkError }}</div>
    <div v-if="loadError" class="card-body text-danger">Meters could not be loaded: {{ loadError }}</div>
    <div v-else-if="meters === null" class="card-body text-secondary">Loading…</div>
    <div v-else-if="meters.length === 0" class="card-body text-secondary">No meters.</div>
    <ul v-else class="list-group list-group-flush">
      <li v-for="meter in meters" :key="meterRowKey(meter)" class="list-group-item" data-testid="node-meter" :data-source="meter.source">
        <div class="d-flex flex-wrap align-items-center gap-2">
          <span class="fw-semibold">{{ meter.meter_type.name }}</span>
          <span class="text-secondary small">{{ unitAndKind(meter.meter_type) }}</span>
          <span class="badge" :class="meter.source === 'model' ? 'text-bg-light border' : 'text-bg-info'">{{ sourceBadge(meter) }}</span>
          <span v-if="(canLog || canEdit) && confirmingKey !== meterRowKey(meter)" class="ms-auto d-flex flex-wrap justify-content-end gap-1">
            <!-- A linked meter is read on its source: no Log reading, no Set limits here (A1.6.7) -->
            <template v-if="isLinked(meter)">
              <button v-if="canEdit" class="btn btn-sm btn-outline-danger touch-target" @click="askRemove(meter)">Remove link</button>
            </template>
            <template v-else>
              <button v-if="canLog" class="btn btn-outline-primary touch-target" @click="openLog(meter)">Log reading</button>
              <template v-if="canEdit">
                <button v-if="meter.meter_type.kind === 'gauge'" class="btn btn-sm btn-outline-secondary" @click="meterModal.openLimits(node, meter)">
                  Set limits
                </button>
                <button v-if="meter.source === 'node'" class="btn btn-sm btn-outline-danger" @click="askRemove(meter)">Remove</button>
              </template>
            </template>
          </span>
        </div>
        <div v-if="isLinked(meter) && !meter.in_use" class="small text-warning-emphasis mt-1" data-testid="link-not-in-use">
          {{ notInUseText(meter, node.code) }}
        </div>
        <template v-else>
          <div v-if="goodReadingText(meter)" class="small">
            {{ goodReadingText(meter) }}<span v-if="meter.overridden" class="text-secondary"> · set on this machine</span>
          </div>
          <button
            v-if="meter.last"
            type="button"
            class="btn btn-link py-2 px-0 mt-1 w-100 d-flex touch-target align-items-center gap-2 text-start text-decoration-none text-body"
            data-testid="last-reading"
            @click="openHistory(meter)"
          >
            <span class="visually-hidden">History:</span>
            <span>{{ lastText(meter) }}</span>
            <span v-if="meter.last.limit_state" class="badge text-bg-warning">{{ LIMIT_STATE_LABELS[meter.last.limit_state] }}</span>
            <i class="fa-solid fa-chevron-right ms-auto text-secondary" aria-hidden="true"></i>
          </button>
          <div v-else class="small text-secondary mt-1">No readings yet</div>
        </template>
        <div v-if="isLinked(meter)" class="small text-secondary" data-testid="linked-read-on">
          Read on <router-link :to="`/equipment/${meter.linked_from.id}`">{{ meter.linked_from.code }}</router-link>
          — {{ meter.linked_from.name }}. Log readings there.
        </div>
        <div v-if="notices[meter.meter_type.id] && !isLinked(meter)" class="small fw-semibold text-warning-emphasis mt-1" role="status">
          {{ notices[meter.meter_type.id] }}
        </div>
        <div v-if="canEdit && meter.source === 'model'" class="small text-secondary">
          Comes from the model {{ node.model_label }}. Remove it in Masters › Models, or change this machine's model.
        </div>
        <template v-if="confirmingKey === meterRowKey(meter)">
          <div class="d-flex flex-wrap align-items-center justify-content-end gap-2 mt-2" data-testid="meter-remove-question">
            <span v-if="isLinked(meter)">{{ removeLinkQuestion(meter, node.code) }}</span>
            <span v-else>
              Remove {{ meter.meter_type.name }} from this machine? Readings stay in history.
              <template v-if="linkedByText(meter)">{{ linkedByText(meter) }}</template>
            </span>
            <button class="btn btn-sm btn-danger" :disabled="removing" @click="remove(meter)">
              {{ isLinked(meter) ? "Remove link" : "Remove" }}
            </button>
            <button class="btn btn-sm btn-outline-secondary" @click="confirmingKey = null">Keep</button>
          </div>
          <div v-if="removeError" class="text-danger small mt-1">{{ removeError }}</div>
        </template>
      </li>
    </ul>
    <NodeMeterFormModal ref="meterModal" @saved="saved" />
    <ReadingFormModal ref="readingModal" @saved="readingSaved" />
    <ReadingHistoryModal ref="historyModal" :can-see-removed="canSeeRemoved" @changed="load" />
    <MeterLinkDialog ref="linkModal" :node="node" @saved="saved" />
  </div>
</template>

<style scoped>
/* A glove on a floor screen (U3): at least 44 px high */
.touch-target {
  min-height: 44px;
}
</style>
