<script setup>
/**
 * Equipment classes — what a piece of equipment is (ISO 14224 equipment class).
 * The class code is also the equipment-code prefix. Edited by engineers and up.
 *
 * Properties (S043 § 7.2): a row's Properties button replaces the table with that class's
 * properties, as Models shows a model's Documents; Back brings the table back. Shown to every
 * reader; the view hides Add property… and Remove without equipment:edit (U8, BS1-04).
 *
 * Category (S063 § 5.2): each class may be in one equipment category. The dialog lists the active
 * categories, plus the class's own when it is inactive, so an edit of the name never clears it.
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureEquipmentCategories, ensureEquipmentClasses, equipmentCategories, equipmentClasses } from "../../stores/masters";
import ClassPropertiesView from "./ClassPropertiesView.vue";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const showInactive = ref(false);
const loadError = ref("");
const propertiesFor = ref(null); // the class whose properties are shown instead of the table

const rows = computed(() => (equipmentClasses.value ?? []).filter((c) => showInactive.value || c.active));

async function reload() {
  loadError.value = "";
  try {
    await Promise.all([ensureEquipmentClasses({ refresh: true }), ensureEquipmentCategories({ refresh: true })]);
  } catch (err) {
    loadError.value = err.message;
  }
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/equipment-classes",
    blank: () => ({ code: "", name: "", category_id: "" }),
    fromRecord: (c) => ({ code: c.code, name: c.name, category_id: c.category_id ?? "" }),
    toBody,
    reload,
  });

// "No category" is sent as null
function toBody(body) {
  return { ...body, category_id: body.category_id === "" ? null : body.category_id };
}

// Active categories by name; the class's own inactive one last, marked, so it is kept on save
const categoryChoices = computed(() => {
  const all = equipmentCategories.value ?? [];
  const choices = all.filter((c) => c.active);
  const own = all.find((c) => c.id === form.value.category_id && !c.active);
  return own ? [...choices, own] : choices;
});

onMounted(reload);
</script>

<template>
  <ClassPropertiesView v-if="propertiesFor" :cls="propertiesFor" @back="propertiesFor = null" />
  <div v-else class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span><i class="fa-solid fa-shapes me-2"></i>Equipment classes</span>
      <div class="d-flex align-items-center gap-3">
        <div class="form-check form-switch mb-0">
          <input id="classes-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="classes-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add class
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="equipmentClasses === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No equipment classes yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Code (prefix)</th><th>Name</th><th>Category</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="c in rows" :key="c.id" :class="{ 'text-secondary': !c.active }">
              <td class="fw-semibold">{{ c.code }}</td>
              <td>{{ c.name }}</td>
              <td>{{ c.category_name ?? "—" }}</td>
              <td><span class="badge" :class="c.active ? 'text-bg-success' : 'text-bg-secondary'">{{ c.active ? "Active" : "Inactive" }}</span></td>
              <td class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary me-1" title="Properties" aria-label="Properties" @click="propertiesFor = c">
                  <i class="fa-solid fa-list-ul"></i>
                </button>
                <button v-if="canEdit" class="btn btn-sm btn-outline-secondary" title="Edit" @click="openEdit(c)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add equipment class' : 'Edit equipment class'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="class-code">Code</label>
      <input id="class-code" v-model="form.code" class="form-control" :class="{ 'is-invalid': fieldError('code') }" maxlength="4" />
      <div v-if="fieldError('code')" class="invalid-feedback d-block">{{ fieldError("code") }}</div>
      <div class="form-text">2–4 letters; becomes the prefix of equipment codes (e.g. VBM001). Cannot be changed once in use.</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="class-name">Name</label>
      <input id="class-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" />
      <div v-if="fieldError('name')" class="invalid-feedback d-block">{{ fieldError("name") }}</div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="class-category">Category</label>
      <select id="class-category" v-model="form.category_id" class="form-select" :class="{ 'is-invalid': fieldError('category_id') }">
        <option value="">No category</option>
        <option v-for="c in categoryChoices" :key="c.id" :value="c.id">{{ c.name }}{{ c.active ? "" : " (inactive)" }}</option>
      </select>
      <div v-if="fieldError('category_id')" class="invalid-feedback d-block">{{ fieldError("category_id") }}</div>
      <div class="form-text">The group this class belongs to, e.g. Lifting equipment. Add categories in Masters › Categories.</div>
    </div>
  </FormModal>
</template>
