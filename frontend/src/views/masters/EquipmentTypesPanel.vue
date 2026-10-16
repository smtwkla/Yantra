<script setup>
/**
 * Equipment types — how an equipment of a class is built (ISO 14224 equipment type,
 * e.g. RPP → Closed execution). A type belongs to one class for good; a type made
 * under the wrong class is deactivated and made again. Edited by engineers and up.
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureEquipmentClasses, ensureEquipmentTypes, equipmentClasses, equipmentTypes } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const showInactive = ref(false);
const classFilter = ref("");
const loadError = ref("");
const editingClass = ref(""); // the edit dialog shows the class as text: it cannot change

const rows = computed(() =>
  (equipmentTypes.value ?? []).filter(
    (t) => (showInactive.value || t.active) && (classFilter.value === "" || t.class_id === classFilter.value)
  )
);
// New types go under an active class only
const classChoices = computed(() => (equipmentClasses.value ?? []).filter((c) => c.active));

async function reload() {
  loadError.value = "";
  try {
    await Promise.all([ensureEquipmentClasses(), ensureEquipmentTypes()]);
  } catch (err) {
    loadError.value = err.message;
  }
}

function filteredActiveClassId() {
  return classChoices.value.some((c) => c.id === classFilter.value) ? classFilter.value : "";
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/equipment-types",
    blank: () => ({ class_id: filteredActiveClassId(), name: "" }),
    // Only the name is edited; activation goes through ActiveToggle, and class_id is never sent
    fromRecord: (t) => ({ name: t.name }),
    label: (t) => `${t.class_code} · ${t.name}`,
    reload,
  });

function editType(t) {
  const cls = (equipmentClasses.value ?? []).find((c) => c.id === t.class_id);
  editingClass.value = cls ? `${cls.code} — ${cls.name}` : t.class_code;
  openEdit(t);
}

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span><i class="fa-solid fa-sitemap me-2"></i>Equipment types</span>
      <div class="d-flex align-items-center gap-3">
        <select v-model="classFilter" class="form-select form-select-sm w-auto" aria-label="Filter by class">
          <option value="">All classes</option>
          <option v-for="c in equipmentClasses ?? []" :key="c.id" :value="c.id">{{ c.code }}</option>
        </select>
        <div class="form-check form-switch mb-0">
          <input id="types-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="types-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add type
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="equipmentTypes === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No equipment types yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Class</th><th>Type</th><th>Status</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="t in rows" :key="t.id" :class="{ 'text-secondary': !t.active }">
              <td class="fw-semibold">{{ t.class_code }}</td>
              <td>{{ t.name }}</td>
              <td><span class="badge" :class="t.active ? 'text-bg-success' : 'text-bg-secondary'">{{ t.active ? "Active" : "Inactive" }}</span></td>
              <td v-if="canEdit" class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="editType(t)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add equipment type' : 'Edit equipment type'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="type-class">Class</label>
      <template v-if="editingId === null">
        <select id="type-class" v-model="form.class_id" class="form-select" :class="{ 'is-invalid': fieldError('class_id') }">
          <option value="" disabled>Select a class…</option>
          <option v-for="c in classChoices" :key="c.id" :value="c.id">{{ c.code }} — {{ c.name }}</option>
        </select>
        <div class="invalid-feedback">{{ fieldError("class_id") }}</div>
        <div class="form-text">Cannot be changed later.</div>
      </template>
      <div v-else id="type-class" class="form-control-plaintext fw-semibold">{{ editingClass }}</div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="type-name">Name</label>
      <input id="type-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" />
      <div class="invalid-feedback">{{ fieldError("name") }}</div>
      <div class="form-text">How this kind is built, e.g. Closed execution. Unique within its class.</div>
    </div>
  </FormModal>
</template>
