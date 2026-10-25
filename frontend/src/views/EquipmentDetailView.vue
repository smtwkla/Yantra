<script setup>
/**
 * Equipment page — one node at any level: path, details, parts and history
 * (docs/steps/S003-equipment-screens/1-brief.md § 4.2; type and notes: S004; documents and
 * photos: S006, loaded separately by DocumentsCards, with the model's: S012; manufacturer and
 * model: S012; Print label: S014). Reloaded from the API after any save. The type name and the model's label come
 * with the node, so no types or models cache is needed here.
 *
 * Tickets (S017): an Open tickets section (the machine's open tickets; on a part, those raised
 * on that part) and a Raise ticket button, each from the node detail's `permissions` (the
 * user's keys at the node's site): the section with ticket:read, the button with ticket:raise
 * on equipment that is not scrapped. The storekeeper holds neither and sees neither.
 *
 * Meters (S038): the Meters card loads the node's meters itself; editing follows canEdit.
 * Readings (S039): Log reading follows reading:log at the node's site (canLogReading), not on a
 * scrapped node; History shows removed readings to equipment:edit holders there.
 *
 * Properties (S043 § 7.4): the class's active properties with the model's values, beside Details,
 * when the class has any. Edit model values opens the Masters model dialog (every item of the
 * model changes), for equipment:edit at any site (canEditModels), on every lifecycle. A
 * component-unit without a model (S033) lists its class's properties with "—", with no model
 * line and no button (BS1-01).
 *
 * This machine's values (S044 § 1.2–1.4): a row shows the item's own value where it has one,
 * marked "· this machine" when the item has a model (on a model-less component-unit every value
 * is its own); the line under the rows then says which values are not the model's. Edit this
 * machine's values follows canEdit (equipment:edit at the node's site, not on a scrapped node) and
 * comes first: the model's button changes every machine of the model, so it stands apart.
 */
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import CriticalityBadge from "../components/CriticalityBadge.vue";
import IntensityBadge from "../components/IntensityBadge.vue";
import LifecycleBadge from "../components/LifecycleBadge.vue";
import DocumentsCards from "../components/documents/DocumentsCards.vue";
import { userPermissions } from "../stores/auth";
import { ensureEquipmentClasses, equipmentClasses } from "../stores/masters";
import { formatDateTime } from "../utils/datetime";
import { LEVEL_LABELS } from "../utils/equipmentLabels";
import { labelsPath } from "../utils/labelSheets";
import { valueText } from "../utils/propertyFormat";
import { ageText, problemText, ticketRowClass } from "../utils/ticketLabels";
import EquipmentFormModal from "./equipment/EquipmentFormModal.vue";
import EquipmentHistory from "./equipment/EquipmentHistory.vue";
import EquipmentMoveModal from "./equipment/EquipmentMoveModal.vue";
import EquipmentLifecycleModal from "./equipment/EquipmentLifecycleModal.vue";
import MetersCard from "./equipment/MetersCard.vue";
import PartsTree from "./equipment/PartsTree.vue";
import ItemPropertiesModal from "./equipment/ItemPropertiesModal.vue";
import ModelPropertiesModal from "./masters/ModelPropertiesModal.vue";

const route = useRoute();
const router = useRouter();

const node = ref(null);
const loading = ref(true);
const notFound = ref(false);
const loadError = ref("");
let loadSeq = 0;

const formModal = ref(null);
const moveModal = ref(null);
const lifecycleModal = ref(null);
const documentsCards = ref(null);
const propertiesModal = ref(null);
const itemPropertiesModal = ref(null);
const propertiesError = ref("");

const scrapped = computed(() => node.value?.lifecycle === "scrapped");
// No actions while another node is loading: they would act on the node still on screen.
// Rights follow the node's site (S011): the API sends the user's keys at that site.
const canEdit = computed(
  () => (node.value?.permissions ?? []).includes("equipment:edit") && !scrapped.value && !loading.value
);
// Model documents are maintained in Masters by equipment:edit held at any site (S012 § 5.5), so
// the "Managed in Masters" hint follows the global permissions, not this node's site
const canEditModels = computed(() => userPermissions.value.includes("equipment:edit"));
const canLogReading = computed(
  () => (node.value?.permissions ?? []).includes("reading:log") && !scrapped.value && !loading.value
);
const canSeeRemovedReadings = computed(() => (node.value?.permissions ?? []).includes("equipment:edit"));
const canReadTickets = computed(() => (node.value?.permissions ?? []).includes("ticket:read"));
const canRaiseTicket = computed(
  () => (node.value?.permissions ?? []).includes("ticket:raise") && !scrapped.value && !loading.value
);
const siteAndUnit = computed(() => node.value.unit.split("."));
// A row with this machine's own value, marked only when the machine has a model to differ from
const markedOwn = (p) => p.source === "item" && node.value.model_id !== null;
const anyMarkedOwn = computed(() => node.value.properties.some(markedOwn));

// The node's open tickets, loaded after the node (its permissions say whether to)
const openTickets = ref(null); // null until loaded
const ticketsError = ref("");
let ticketsSeq = 0;

async function loadTickets(nodeId) {
  const seq = ++ticketsSeq;
  openTickets.value = null;
  ticketsError.value = "";
  try {
    const page = await apiGet(`/api/tickets?equipment_id=${nodeId}&state=open`);
    if (seq === ticketsSeq) openTickets.value = page.items;
  } catch (err) {
    if (seq === ticketsSeq) ticketsError.value = err.message;
  }
}
const classLabel = computed(() => {
  const cls = (equipmentClasses.value ?? []).find((c) => c.id === node.value.class_id);
  return cls ? `${cls.code} — ${cls.name}` : node.value.class_code;
});

async function load() {
  const id = route.params.id;
  if (id === undefined) return; // the route is changing to another page
  const seq = ++loadSeq;
  loading.value = true;
  notFound.value = false;
  loadError.value = "";
  try {
    const [loaded] = await Promise.all([apiGet(`/api/equipment/${id}`), ensureEquipmentClasses()]);
    if (seq === loadSeq) {
      node.value = loaded;
      if (loaded.permissions.includes("ticket:read")) loadTickets(loaded.id);
    }
  } catch (err) {
    if (seq !== loadSeq) return;
    node.value = null;
    if (err.status === 404) notFound.value = true;
    else loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

// Vue Router reuses this component when only :id changes, so follow the route
watch(() => route.params.id, load, { immediate: true });

// Each dialog fetches its stored values first; a failed fetch leaves it closed with the message
async function openPropertiesDialog(open) {
  propertiesError.value = "";
  try {
    await open();
  } catch (err) {
    propertiesError.value = err.message;
  }
}

function editModelValues() {
  return openPropertiesDialog(() =>
    propertiesModal.value.open({ id: node.value.model_id, label: node.value.model_label, class_code: node.value.class_code })
  );
}

function editItemValues() {
  return openPropertiesDialog(() => itemPropertiesModal.value.open({ id: node.value.id, code: node.value.code }));
}

// A new tab, as from the list; anyone who may see the node may print its label (S014)
function printLabel(withParts) {
  window.open(router.resolve(labelsPath([node.value.id], withParts)).href, "_blank");
}

function onSaved({ result, created }) {
  if (created) {
    router.push(`/equipment/${result.id}`);
  } else {
    load();
    // The model may have changed, and with it the inherited documents
    documentsCards.value?.reload();
  }
}
</script>

<template>
  <div class="py-3">
    <div v-if="loading && !node" class="text-secondary">Loading…</div>
    <div v-else-if="notFound" class="alert alert-warning">
      Equipment not found, or not at your units.
      <router-link to="/equipment" class="alert-link ms-1">Back to the list</router-link>
    </div>
    <div v-else-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-sm btn-outline-danger" @click="load">Retry</button>
    </div>

    <template v-else-if="node">
      <nav class="small mb-2" aria-label="Path">
        <span class="text-secondary">{{ siteAndUnit[0] }} › {{ siteAndUnit[1] }}</span>
        <template v-for="a in node.ancestors" :key="a.id">
          <span class="text-secondary"> › </span><router-link :to="`/equipment/${a.id}`">{{ a.code }}</router-link>
        </template>
        <span class="text-secondary"> › {{ node.code }}</span>
      </nav>

      <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
        <h4 class="mb-0 me-2">{{ node.code }} — {{ node.name }}</h4>
        <LifecycleBadge :lifecycle="node.lifecycle" />
        <CriticalityBadge :grade="node.effective_criticality" :inherited="node.criticality === null" />
        <span v-if="loading" class="text-secondary small">Loading…</span>
        <div class="dropdown ms-auto">
          <button
            class="btn btn-sm btn-outline-secondary dropdown-toggle"
            type="button"
            data-bs-toggle="dropdown"
            aria-expanded="false"
            :disabled="loading"
          >
            <i class="fa-solid fa-qrcode me-1"></i>Print label
          </button>
          <ul class="dropdown-menu dropdown-menu-end">
            <li><button class="dropdown-item" type="button" @click="printLabel(false)">This node only</button></li>
            <li>
              <button class="dropdown-item" type="button" :disabled="node.children.length === 0" @click="printLabel(true)">
                This node and all its parts
              </button>
            </li>
          </ul>
        </div>
      </div>

      <router-link v-if="canRaiseTicket" :to="`/tickets/new?equipment=${node.id}`" class="btn btn-danger mb-3">
        <i class="fa-solid fa-triangle-exclamation me-1"></i>Raise ticket
      </router-link>

      <div v-if="scrapped" class="alert alert-secondary">Scrapped — this record is read-only.</div>
      <div v-else-if="canEdit" class="d-flex flex-wrap gap-2 mb-3">
        <button class="btn btn-sm btn-outline-primary" @click="formModal.openEdit(node)">
          <i class="fa-solid fa-pen me-1"></i>Edit
        </button>
        <button v-if="node.level !== 'component'" class="btn btn-sm btn-outline-primary" @click="formModal.openCreatePart(node)">
          <i class="fa-solid fa-plus me-1"></i>Add part
        </button>
        <button class="btn btn-sm btn-outline-primary" @click="moveModal.open(node)">
          <i class="fa-solid fa-right-left me-1"></i>Move
        </button>
        <button class="btn btn-sm btn-outline-primary" @click="lifecycleModal.open(node)">
          <i class="fa-solid fa-toggle-on me-1"></i>Change lifecycle
        </button>
      </div>

      <div v-if="canReadTickets" class="card mb-3">
        <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
          <span>Open tickets</span>
          <router-link :to="`/tickets?equipment_id=${node.id}&state=all`" class="small">All its tickets</router-link>
        </div>
        <div v-if="ticketsError" class="card-body text-danger">Tickets could not be loaded: {{ ticketsError }}</div>
        <div v-else-if="openTickets === null" class="card-body text-secondary">Loading…</div>
        <div v-else-if="openTickets.length === 0" class="card-body text-secondary">No open tickets.</div>
        <div v-else class="list-group list-group-flush">
          <router-link
            v-for="t in openTickets"
            :key="t.id"
            :to="`/tickets/${t.id}`"
            class="list-group-item list-group-item-action"
            :class="ticketRowClass(t)"
          >
            <div class="d-flex flex-wrap align-items-center gap-2">
              <IntensityBadge :intensity="t.intensity" />
              <span class="fw-semibold">{{ t.serial }}</span>
              <span v-if="t.component && t.component.id !== node.id" class="text-secondary">{{ t.component.code }}</span>
              <span class="ms-auto small text-secondary"><i class="fa-regular fa-clock me-1"></i>{{ ageText(t.occurred_at) }}</span>
            </div>
            <div class="ticket-text">{{ problemText(t) }}</div>
          </router-link>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-lg-6">
          <div class="card h-100">
            <div class="card-header">Details</div>
            <div class="card-body">
              <dl class="row mb-0">
                <dt class="col-5">Level</dt><dd class="col-7">{{ LEVEL_LABELS[node.level] }}</dd>
                <dt class="col-5">Class</dt><dd class="col-7">{{ classLabel }}</dd>
                <dt class="col-5">Type</dt><dd class="col-7">{{ node.type_name }}</dd>
                <!-- A component-unit may have no model (S033) -->
                <template v-if="node.model_id !== null">
                  <dt class="col-5">Manufacturer</dt><dd class="col-7">{{ node.manufacturer_name }}</dd>
                </template>
                <dt class="col-5">Model</dt><dd class="col-7">{{ node.model_designation ?? "No model" }}</dd>
                <dt class="col-5">Serial no.</dt><dd class="col-7">{{ node.serial_no }}</dd>
                <dt class="col-5">Year</dt><dd class="col-7">{{ node.year }}</dd>
                <template v-if="node.level === 'equipment'">
                  <dt class="col-5">Unit</dt><dd class="col-7">{{ node.unit }}</dd>
                </template>
                <dt class="col-5">Created</dt>
                <dd class="col-7">{{ formatDateTime(node.created_at) }} · {{ node.created_by }}</dd>
                <dt class="col-5">Updated</dt>
                <dd class="col-7 mb-0">{{ formatDateTime(node.updated_at) }} · {{ node.updated_by }}</dd>
              </dl>
            </div>
          </div>
        </div>
        <div v-if="node.properties.length" class="col-lg-6">
          <div class="card h-100">
            <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
              <span>Properties</span>
              <div class="d-flex flex-wrap gap-2">
                <button v-if="canEdit" class="btn btn-sm btn-outline-primary" @click="editItemValues">
                  <i class="fa-solid fa-pen me-1"></i>Edit this machine's values
                </button>
                <button v-if="canEditModels && node.model_id !== null" class="btn btn-sm btn-outline-primary" :disabled="loading" @click="editModelValues">
                  <i class="fa-solid fa-pen me-1"></i>Edit model values
                </button>
              </div>
            </div>
            <div class="card-body">
              <div v-if="propertiesError" class="alert alert-danger py-2">{{ propertiesError }}</div>
              <dl class="row mb-2">
                <template v-for="p in node.properties" :key="p.property_id">
                  <dt class="col-6">{{ p.name }}</dt>
                  <dd class="col-6">
                    {{ valueText(p.display) }}<small v-if="markedOwn(p)" class="text-secondary"> · this machine</small>
                  </dd>
                </template>
              </dl>
              <div v-if="node.model_id !== null" class="small text-secondary">
                <template v-if="anyMarkedOwn">Values from model {{ node.model_label }}, except those marked this machine.</template>
                <template v-else>Values from model {{ node.model_label }}.</template>
              </div>
            </div>
          </div>
        </div>
        <div class="col-lg-6">
          <div class="card h-100">
            <div class="card-header">Parts</div>
            <div class="card-body"><PartsTree :children="node.children" /></div>
          </div>
        </div>
      </div>

      <MetersCard :node="node" :can-edit="canEdit" :can-log="canLogReading" :can-see-removed="canSeeRemovedReadings" @changed="load" />

      <div v-if="node.notes" class="card mt-3">
        <div class="card-header">Notes</div>
        <!-- pre-wrap: shown as entered, line breaks and aligned spacing kept -->
        <div class="card-body notes-text">{{ node.notes }}</div>
      </div>

      <div class="card mt-3">
        <div class="card-header">History</div>
        <div class="card-body history-text"><EquipmentHistory :events="node.events" /></div>
      </div>

      <DocumentsCards
        ref="documentsCards"
        :base-path="`/api/equipment/${node.id}/documents`"
        :can-edit="canEdit"
        :show-managed-in="canEditModels"
      />
    </template>

    <EquipmentFormModal ref="formModal" @saved="onSaved" />
    <EquipmentMoveModal ref="moveModal" @saved="load" />
    <EquipmentLifecycleModal ref="lifecycleModal" @saved="load" />
    <ModelPropertiesModal ref="propertiesModal" @saved="load" />
    <ItemPropertiesModal ref="itemPropertiesModal" @saved="load" />
  </div>
</template>

<style scoped>
.notes-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.ticket-text,
.history-text {
  overflow-wrap: anywhere;
}
</style>
