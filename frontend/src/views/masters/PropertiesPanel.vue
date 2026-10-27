<script setup>
/**
 * Properties (S043 § 7.1) — the technical data a class of equipment has (ISO 14224 Annex A
 * equipment-specific data): a name, a data type, a unit for a number, the options of a choice.
 * Defined once and linked to any number of classes in Classes; valued on models. Edited by
 * the keepers of classes and models (equipment:edit). Never deleted: deactivated.
 *
 * The dialog: a new property is one POST with its first options. An edit is a PUT of the
 * property, then a PUT per changed option and a POST per new one (send(request), as the Team
 * dialog); an option's refusal shows under the options list. The data type is fixed once the
 * property has an option or a value, the unit once it has a value (the API refuses; the inputs
 * say so first, BR2-01).
 *
 * S061: two tick boxes. Applies to every class: the property shows on every machine without a
 * link. Value set on each machine: installation data such as where the machine stands, left out of
 * the model's dialog; turning it on is refused while a model has a value (the message shows under
 * its box). The table marks them Every class and Each machine.
 */
import { computed, onMounted, ref } from "vue";
import { apiPost, apiPut } from "../../api";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureProperties, properties, resetMasters } from "../../stores/masters";
import { DATA_TYPES, typeSummary } from "../../utils/propertyFormat";
import { useMasterForm } from "./useMasterForm";

const PATH = "/api/masters/properties";

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const showInactive = ref(false);
const loadError = ref("");
const editing = ref(null); // the stored property of the edit dialog
// The edit dialog's options as saved, by id: kept across a refused Save, so a retry sends only
// what is still unsaved
let savedOptions = new Map();

const rows = computed(() => (properties.value ?? []).filter((p) => showInactive.value || p.active));

async function reload() {
  loadError.value = "";
  try {
    await ensureProperties({ refresh: true });
  } catch (err) {
    loadError.value = err.message;
  }
}

// A new property's body: a unit only for a number, options only for a choice
function toBody(form) {
  const body = {
    name: form.name, data_type: form.data_type, description: form.description,
    all_classes: form.all_classes, per_item_only: form.per_item_only,
  };
  if (form.data_type === "number") body.unit = form.unit;
  if (form.data_type === "choice") body.options = form.options.map((o) => o.label);
  return body;
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, send, changeActive,
} =
  useMasterForm({
    path: PATH,
    blank: () => ({ name: "", data_type: "", unit: "", description: "", all_classes: false, per_item_only: false, options: [] }),
    fromRecord: (p) => ({
      name: p.name,
      data_type: p.data_type,
      unit: p.unit ?? "",
      description: p.description ?? "",
      all_classes: Boolean(p.all_classes),
      per_item_only: Boolean(p.per_item_only),
      options: p.options.map((o) => ({ id: o.id, label: o.label, active: Boolean(o.active) })),
    }),
    label: (p) => p.name,
    toBody,
    reload,
  });

const typeFixed = computed(() => editing.value !== null && (editing.value.options.length > 0 || editing.value.value_count > 0));
const unitFixed = computed(() => editing.value !== null && editing.value.value_count > 0);

function addProperty() {
  editing.value = null;
  openCreate();
}

function editProperty(p) {
  editing.value = p;
  savedOptions = new Map(p.options.map((o) => [o.id, { label: o.label, active: Boolean(o.active) }]));
  openEdit(p);
}

function addOption() {
  form.value.options.push({ id: null, label: "", active: true });
}

// Only a row not saved yet can be taken away; a saved option is deactivated instead (CR1-03)
function removeNewOption(index) {
  form.value.options.splice(index, 1);
}

// An option's refusal (a duplicate label) names `label`; the dialog shows it under the options
async function optionRequest(request) {
  try {
    return await request();
  } catch (err) {
    err.field = "options";
    throw err;
  }
}

async function saveEdit() {
  const id = editingId.value;
  const body = {
    name: form.value.name, data_type: form.value.data_type, description: form.value.description,
    all_classes: form.value.all_classes, per_item_only: form.value.per_item_only,
  };
  if (form.value.data_type === "number") body.unit = form.value.unit;
  const saved = await apiPut(`${PATH}/${id}`, body);
  // Options belong to a choice only: rows left from before a type change are not sent (CR1-02)
  if (form.value.data_type !== "choice") return saved;
  try {
    await saveOptions(id);
  } catch (err) {
    // The property itself is saved: the list must show it now, even if the user then discards
    // the dialog (CR1-02).  The dialog stays open with the option's message.
    resetMasters();
    await reload();
    editing.value = (properties.value ?? []).find((p) => p.id === id) ?? editing.value;
    throw err;
  }
  return saved;
}

async function saveOptions(id) {
  for (const option of form.value.options) {
    if (option.id === null) {
      // The new id is kept at once, so a second Save after a refusal does not add it twice
      option.id = (await optionRequest(() => apiPost(`${PATH}/${id}/options`, { label: option.label }))).id;
      savedOptions.set(option.id, { label: option.label, active: true });
      continue;
    }
    const before = savedOptions.get(option.id);
    if (before.label !== option.label || before.active !== option.active) {
      const body = { label: option.label, active: option.active };
      await optionRequest(() => apiPut(`/api/masters/property-options/${option.id}`, body));
      savedOptions.set(option.id, body);
    }
  }
}

function submit() {
  return editingId.value === null ? save() : send(saveEdit);
}

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span><i class="fa-solid fa-list-ul me-2"></i>Properties</span>
      <div class="d-flex align-items-center gap-3">
        <div class="form-check form-switch mb-0">
          <input id="properties-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="properties-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="addProperty">
          <i class="fa-solid fa-plus me-1"></i>Add property
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="properties === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No properties yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Name</th><th>Type</th><th>Classes</th><th>Active</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="p in rows" :key="p.id" :class="{ 'text-secondary': !p.active }">
              <td class="fw-semibold">
                {{ p.name }}
                <span v-if="p.all_classes" class="badge text-bg-info fw-normal ms-1">Every class</span>
                <span v-if="p.per_item_only" class="badge text-bg-secondary fw-normal ms-1">Each machine</span>
              </td>
              <td>{{ typeSummary(p) }}</td>
              <td>{{ p.class_count }}</td>
              <td><span class="badge" :class="p.active ? 'text-bg-success' : 'text-bg-secondary'">{{ p.active ? "Active" : "Inactive" }}</span></td>
              <td v-if="canEdit" class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="editProperty(p)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add property' : 'Edit property'" :saving="saving" :dirty="dirty" :error="modalError" @save="submit">
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
    <div class="mb-3">
      <label class="form-label" for="property-name">Name</label>
      <input id="property-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="80" />
      <div v-if="fieldError('name')" class="invalid-feedback d-block">{{ fieldError("name") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="property-type">Data type</label>
      <select id="property-type" v-model="form.data_type" class="form-select" :class="{ 'is-invalid': fieldError('data_type') }" :disabled="typeFixed">
        <option value="" disabled>Select a data type…</option>
        <option v-for="t in DATA_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
      </select>
      <div v-if="fieldError('data_type')" class="invalid-feedback d-block">{{ fieldError("data_type") }}</div>
      <div v-if="typeFixed" class="form-text">This property has options or values, so its data type is fixed.</div>
      <div class="form-text">How the equipment is built (centrifugal, open execution) is its type: use Masters › Types for that.</div>
    </div>
    <div v-if="form.data_type === 'number'" class="mb-3">
      <label class="form-label" for="property-unit">Unit</label>
      <input id="property-unit" v-model="form.unit" class="form-control" :class="{ 'is-invalid': fieldError('unit') }" maxlength="20" :disabled="unitFixed" />
      <div v-if="fieldError('unit')" class="invalid-feedback d-block">{{ fieldError("unit") }}</div>
      <div v-if="unitFixed" class="form-text">This property has values, so its unit is fixed.</div>
    </div>
    <div v-else-if="fieldError('unit')" class="invalid-feedback d-block mb-3">{{ fieldError("unit") }}</div>
    <div v-if="form.data_type === 'choice'" class="mb-3">
      <div class="form-label">Options</div>
      <div v-for="(option, index) in form.options" :key="option.id ?? `new-${index}`" class="d-flex align-items-center gap-2 mb-2">
        <input
          v-model="option.label"
          class="form-control"
          :aria-label="`Option ${index + 1}`"
          maxlength="60"
        />
        <div v-if="option.id !== null" class="form-check form-switch mb-0 text-nowrap">
          <input :id="`option-active-${option.id}`" v-model="option.active" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" :for="`option-active-${option.id}`">Active</label>
        </div>
        <button
          v-else
          type="button"
          class="btn btn-sm btn-outline-secondary"
          title="Remove option"
          :aria-label="`Remove option ${index + 1}`"
          @click="removeNewOption(index)"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <button type="button" class="btn btn-sm btn-outline-secondary" @click="addOption">
        <i class="fa-solid fa-plus me-1"></i>Add option
      </button>
      <div v-if="fieldError('options')" class="invalid-feedback d-block">{{ fieldError("options") }}</div>
    </div>
    <div v-else-if="fieldError('options')" class="invalid-feedback d-block mb-3">{{ fieldError("options") }}</div>
    <div class="mb-3">
      <div class="form-check">
        <input id="property-all-classes" v-model="form.all_classes" class="form-check-input" type="checkbox" />
        <label class="form-check-label" for="property-all-classes">Applies to every class</label>
      </div>
      <div class="form-text mt-0">Shows on every machine. No need to add it to each class.</div>
      <div v-if="fieldError('all_classes')" class="invalid-feedback d-block">{{ fieldError("all_classes") }}</div>
    </div>
    <div class="mb-3">
      <div class="form-check">
        <input id="property-per-item" v-model="form.per_item_only" class="form-check-input" type="checkbox" :class="{ 'is-invalid': fieldError('per_item_only') }" />
        <label class="form-check-label" for="property-per-item">Value set on each machine</label>
      </div>
      <div class="form-text mt-0">Each machine gets its own value, for example where it stands. Models do not hold it.</div>
      <div v-if="fieldError('per_item_only')" class="invalid-feedback d-block">{{ fieldError("per_item_only") }}</div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="property-description">Description</label>
      <textarea id="property-description" v-model="form.description" class="form-control" :class="{ 'is-invalid': fieldError('description') }" rows="2" maxlength="300"></textarea>
      <div v-if="fieldError('description')" class="invalid-feedback d-block">{{ fieldError("description") }}</div>
      <div class="form-text">What the property means and where to read it. Optional.</div>
    </div>
  </FormModal>
</template>
