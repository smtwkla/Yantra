<script setup>
/**
 * Equipment page — one node at any level: path, details, parts and history
 * (docs/steps/S003-equipment-screens/1-brief.md § 4.2; type and notes: S004). Reloaded from the API
 * after any save. The type name comes with the node, so no types cache is needed here.
 */
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import CriticalityBadge from "../components/CriticalityBadge.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { userPermissions } from "../stores/auth";
import { ensureEquipmentClasses, equipmentClasses } from "../stores/masters";
import { formatDateTime } from "../utils/datetime";
import { LEVEL_LABELS } from "../utils/equipmentLabels";
import EquipmentFormModal from "./equipment/EquipmentFormModal.vue";
import EquipmentHistory from "./equipment/EquipmentHistory.vue";
import EquipmentMoveModal from "./equipment/EquipmentMoveModal.vue";
import EquipmentStatusModal from "./equipment/EquipmentStatusModal.vue";
import PartsTree from "./equipment/PartsTree.vue";

const route = useRoute();
const router = useRouter();

const node = ref(null);
const loading = ref(true);
const notFound = ref(false);
const loadError = ref("");
let loadSeq = 0;

const formModal = ref(null);
const moveModal = ref(null);
const statusModal = ref(null);

const scrapped = computed(() => node.value?.status === "scrapped");
// No actions while another node is loading: they would act on the node still on screen
const canEdit = computed(() => userPermissions.value.includes("equipment:edit") && !scrapped.value && !loading.value);
const siteAndUnit = computed(() => node.value.unit.split("."));
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
    if (seq === loadSeq) node.value = loaded;
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

function onSaved({ result, created }) {
  if (created) router.push(`/equipment/${result.id}`);
  else load();
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
        <StatusBadge :status="node.status" />
        <CriticalityBadge :grade="node.effective_criticality" :inherited="node.criticality === null" />
        <span v-if="loading" class="text-secondary small">Loading…</span>
      </div>

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
        <button class="btn btn-sm btn-outline-primary" @click="statusModal.open(node)">
          <i class="fa-solid fa-toggle-on me-1"></i>Change status
        </button>
      </div>

      <div class="row g-3">
        <div class="col-lg-4">
          <div class="card h-100">
            <div class="card-header">Details</div>
            <div class="card-body">
              <dl class="row mb-0">
                <dt class="col-5">Level</dt><dd class="col-7">{{ LEVEL_LABELS[node.level] }}</dd>
                <dt class="col-5">Class</dt><dd class="col-7">{{ classLabel }}</dd>
                <dt class="col-5">Type</dt><dd class="col-7">{{ node.type_name }}</dd>
                <dt class="col-5">Make</dt><dd class="col-7">{{ node.make }}</dd>
                <dt class="col-5">Model</dt><dd class="col-7">{{ node.model }}</dd>
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
        <div class="col-lg-4">
          <div class="card h-100">
            <div class="card-header">Parts</div>
            <div class="card-body"><PartsTree :children="node.children" /></div>
          </div>
        </div>
        <div class="col-lg-4">
          <div class="card h-100">
            <div class="card-header">History</div>
            <div class="card-body"><EquipmentHistory :events="node.events" /></div>
          </div>
        </div>
      </div>

      <div v-if="node.notes" class="card mt-3">
        <div class="card-header">Notes</div>
        <!-- pre-wrap: shown as entered, line breaks and aligned spacing kept -->
        <div class="card-body notes-text">{{ node.notes }}</div>
      </div>
    </template>

    <EquipmentFormModal ref="formModal" @saved="onSaved" />
    <EquipmentMoveModal ref="moveModal" @saved="load" />
    <EquipmentStatusModal ref="statusModal" @saved="load" />
  </div>
</template>

<style scoped>
.notes-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
