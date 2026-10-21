<script setup>
/**
 * Equipment models — a manufacturer's product, e.g. Atlas Copco GA37 (docs/steps/S012-equipment-models;
 * ISO 14224 "manufacturer's model designation"). A model belongs to one class and optionally one
 * type of it, fixed for life: a wrong one is deactivated and made again; only the designation can
 * be edited. Equipment picks its model and takes its class and type from it. Generic and in-house
 * models are ordinary records. Edited by engineers and up (equipment:edit at any site).
 *
 * Documents (S012, S009's in-panel view): a row's Documents button replaces the table with that
 * model's Documents and Photos cards, in this panel; Back brings the table back. Not a dialog,
 * because the cards open dialogs of their own. Model documents show on every machine of the
 * model, at every site.
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import DocumentsCards from "../../components/documents/DocumentsCards.vue";
import { userPermissions } from "../../stores/auth";
import {
  ensureEquipmentClasses, ensureEquipmentTypes, ensureManufacturers, ensureModels, equipmentClasses,
  equipmentModels, equipmentTypes, manufacturers,
} from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const showInactive = ref(false);
const classFilter = ref("");
const makerFilter = ref("");
const loadError = ref("");
const editingFixed = ref(""); // the edit dialog shows manufacturer, class and type as text: they cannot change
const documentsFor = ref(null); // the model whose documents are shown instead of the table

const rows = computed(() =>
  (equipmentModels.value ?? []).filter(
    (m) =>
      (showInactive.value || m.active) &&
      (classFilter.value === "" || m.class_id === classFilter.value) &&
      (makerFilter.value === "" || m.manufacturer_id === makerFilter.value)
  )
);
// New models go under an active manufacturer and class, with an active type of that class
const makerChoices = computed(() => (manufacturers.value ?? []).filter((m) => m.active));
const classChoices = computed(() => (equipmentClasses.value ?? []).filter((c) => c.active));
const typeChoices = computed(() =>
  (equipmentTypes.value ?? []).filter((t) => t.active && t.class_id === form.value.class_id)
);

async function reload() {
  loadError.value = "";
  try {
    await Promise.all([
      ensureModels({ refresh: true }), ensureManufacturers({ refresh: true }),
      ensureEquipmentClasses({ refresh: true }), ensureEquipmentTypes({ refresh: true }),
    ]);
  } catch (err) {
    loadError.value = err.message;
  }
}

const activeOr = (choices, id) => (choices.some((c) => c.id === id) ? id : "");

// "— none —" is sent as a null type
function toBody(form) {
  return form.type_id === undefined ? form : { ...form, type_id: form.type_id === "" ? null : form.type_id };
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/equipment-models",
    blank: () => ({
      manufacturer_id: activeOr(makerChoices.value, makerFilter.value),
      designation: "",
      class_id: activeOr(classChoices.value, classFilter.value),
      type_id: "",
    }),
    // Only the designation is edited; activation goes through ActiveToggle; the fixed ids are never sent
    fromRecord: (m) => ({ designation: m.designation }),
    label: (m) => m.label,
    toBody,
    reload,
  });

function editModel(m) {
  editingFixed.value = `${m.manufacturer_name} · ${m.class_code} — ${m.class_name} · ${m.type_name ?? "no type"}`;
  openEdit(m);
}

onMounted(reload);
</script>

<template>
  <div class="card">
    <div v-if="documentsFor" class="card-header d-flex flex-wrap align-items-center gap-1">
      <button class="btn btn-sm btn-link p-0 text-decoration-none" @click="documentsFor = null">
        <i class="fa-solid fa-arrow-left me-1"></i>Models
      </button>
      <span>· {{ documentsFor.label }} · Documents</span>
    </div>
    <div v-else class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span><i class="fa-solid fa-tag me-2"></i>Models</span>
      <div class="d-flex align-items-center flex-wrap gap-3">
        <select v-model="classFilter" class="form-select form-select-sm w-auto" aria-label="Filter by class">
          <option value="">All classes</option>
          <option v-for="c in equipmentClasses ?? []" :key="c.id" :value="c.id">{{ c.code }}</option>
        </select>
        <select v-model="makerFilter" class="form-select form-select-sm w-auto" aria-label="Filter by manufacturer">
          <option value="">All manufacturers</option>
          <option v-for="m in manufacturers ?? []" :key="m.id" :value="m.id">{{ m.name }}</option>
        </select>
        <div class="form-check form-switch mb-0">
          <input id="models-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="models-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add model
        </button>
      </div>
    </div>
    <div v-if="documentsFor" class="card-body">
      <DocumentsCards
        :base-path="`/api/masters/equipment-models/${documentsFor.id}/documents`"
        :can-edit="canEdit"
        every-site="model"
      />
    </div>
    <div v-else class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="equipmentModels === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No models yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Model</th><th>Class</th><th>Type</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="m in rows" :key="m.id" :class="{ 'text-secondary': !m.active }">
              <td class="fw-semibold">{{ m.label }}</td>
              <td>{{ m.class_code }}</td>
              <td>{{ m.type_name }}</td>
              <td><span class="badge" :class="m.active ? 'text-bg-success' : 'text-bg-secondary'">{{ m.active ? "Active" : "Inactive" }}</span></td>
              <td class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary me-1" title="Documents" @click="documentsFor = m">
                  <i class="fa-solid fa-paperclip"></i>
                </button>
                <button v-if="canEdit" class="btn btn-sm btn-outline-secondary" title="Edit" @click="editModel(m)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add model' : 'Edit model'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
    <template v-if="editingId !== null" #footer-left>
      <ActiveToggle
        :active="editingActive"
        :label="editingLabel"
        :confirming="confirmingDeactivate"
        :disabled="saving"
        @ask="confirmingDeactivate = true"
        @cancel="confirmingDeactivate = false"
        @change="changeActive"
      />
    </template>
    <template v-if="editingId === null">
      <div class="mb-3">
        <label class="form-label" for="model-maker">Manufacturer</label>
        <select id="model-maker" v-model="form.manufacturer_id" class="form-select" :class="{ 'is-invalid': fieldError('manufacturer_id') }">
          <option value="" disabled>Select a manufacturer…</option>
          <option v-for="m in makerChoices" :key="m.id" :value="m.id">{{ m.name }}</option>
        </select>
        <div v-if="fieldError('manufacturer_id')" class="invalid-feedback d-block">{{ fieldError("manufacturer_id") }}</div>
        <div class="form-text">"Generic" when the maker is unknown; "SMTW (in-house)" for our own designs (add them in Manufacturers).</div>
      </div>
      <div class="row g-3 mb-3">
        <div class="col-sm-6">
          <label class="form-label" for="model-class">Class</label>
          <!-- @change, not a watch: the type list follows the class -->
          <select
            id="model-class"
            v-model="form.class_id"
            class="form-select"
            :class="{ 'is-invalid': fieldError('class_id') }"
            @change="form.type_id = ''"
          >
            <option value="" disabled>Select a class…</option>
            <option v-for="c in classChoices" :key="c.id" :value="c.id">{{ c.code }} — {{ c.name }}</option>
          </select>
          <div v-if="fieldError('class_id')" class="invalid-feedback d-block">{{ fieldError("class_id") }}</div>
        </div>
        <div class="col-sm-6">
          <label class="form-label" for="model-type">Type</label>
          <select id="model-type" v-model="form.type_id" class="form-select" :class="{ 'is-invalid': fieldError('type_id') }">
            <option value="">— none —</option>
            <option v-for="t in typeChoices" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <div v-if="fieldError('type_id')" class="invalid-feedback d-block">{{ fieldError("type_id") }}</div>
        </div>
      </div>
      <div class="form-text mb-3">Manufacturer, class and type cannot be changed later. Equipment of this model takes its class and type.</div>
    </template>
    <div v-else class="mb-3">
      <label class="form-label">Manufacturer · class · type</label>
      <div class="form-control-plaintext fw-semibold py-0">{{ editingFixed }}</div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="model-designation">Designation</label>
      <input id="model-designation" v-model="form.designation" class="form-control" :class="{ 'is-invalid': fieldError('designation') }" maxlength="80" />
      <div v-if="fieldError('designation')" class="invalid-feedback d-block">{{ fieldError("designation") }}</div>
      <div class="form-text">The maker's name for the product, e.g. GA37; for a Generic model what it is, e.g. Generic gear pump. Unique per manufacturer.</div>
    </div>
  </FormModal>
</template>
