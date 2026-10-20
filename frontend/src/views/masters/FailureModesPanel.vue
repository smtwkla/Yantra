<script setup>
/**
 * Failure modes (S016) — what is seen when something fails (ISO 14224 failure mode; the
 * operator picks it as the symptom). A mode belongs to one equipment class, or is General
 * and shown for every class; the class is fixed once created. Labels are unique within
 * what one picker shows (a class's modes plus the General ones): the API refuses a clash.
 * Edited by engineers and up, and IT admin (failure_codes:edit).
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureEquipmentClasses, ensureFailureModes, equipmentClasses, failureModes } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const GENERAL = "general";

const canEdit = computed(() => userPermissions.value.includes("failure_codes:edit"));
const showInactive = ref(false);
const classFilter = ref(""); // "" all, GENERAL, or a class id
const loadError = ref("");
const editingClass = ref(""); // the edit dialog shows the class as text: it cannot change

function matchesFilter(m) {
  if (classFilter.value === "") return true;
  if (classFilter.value === GENERAL) return m.class_id === null;
  return m.class_id === classFilter.value;
}

const rows = computed(() => (failureModes.value ?? []).filter((m) => (showInactive.value || m.active) && matchesFilter(m)));
// New modes go under an active class only (or General)
const classChoices = computed(() => (equipmentClasses.value ?? []).filter((c) => c.active));

async function reload() {
  loadError.value = "";
  try {
    await Promise.all([ensureEquipmentClasses({ refresh: true }), ensureFailureModes({ refresh: true })]);
  } catch (err) {
    loadError.value = err.message;
  }
}

// A new mode starts under the class being filtered on, when it is an active one
function filteredActiveClassId() {
  return classChoices.value.some((c) => c.id === classFilter.value) ? classFilter.value : null;
}

function classText(classId, fallbackCode) {
  if (classId === null) return "General — every class";
  const cls = (equipmentClasses.value ?? []).find((c) => c.id === classId);
  return cls ? `${cls.code} — ${cls.name}` : fallbackCode;
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/failure-modes",
    blank: () => ({ class_id: filteredActiveClassId(), code: "", label: "", description: "" }),
    // class_id is never sent on edit: it is fixed; activation goes through ActiveToggle
    fromRecord: (m) => ({ code: m.code, label: m.label, description: m.description ?? "" }),
    label: (m) => `${m.code} · ${m.label}`,
    reload,
  });

function editMode(m) {
  editingClass.value = classText(m.class_id, m.class_code);
  openEdit(m);
}

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span><i class="fa-solid fa-triangle-exclamation me-2"></i>Failure modes (symptoms)</span>
      <div class="d-flex align-items-center flex-wrap gap-3">
        <select v-model="classFilter" class="form-select form-select-sm w-auto" aria-label="Filter by class">
          <option value="">All</option>
          <option :value="GENERAL">General</option>
          <option v-for="c in equipmentClasses ?? []" :key="c.id" :value="c.id">{{ c.code }}</option>
        </select>
        <div class="form-check form-switch mb-0">
          <input id="modes-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="modes-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add mode
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="failureModes === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No failure modes here.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Code</th><th>Symptom</th><th>Class</th><th>Status</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="m in rows" :key="m.id" :class="{ 'text-secondary': !m.active }">
              <td class="fw-semibold text-nowrap">{{ m.code }}</td>
              <td>
                {{ m.label }}
                <div v-if="m.description" class="small text-secondary">{{ m.description }}</div>
              </td>
              <td class="text-nowrap">{{ m.class_code ?? "General" }}</td>
              <td><span class="badge" :class="m.active ? 'text-bg-success' : 'text-bg-secondary'">{{ m.active ? "Active" : "Inactive" }}</span></td>
              <td v-if="canEdit" class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="editMode(m)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add failure mode' : 'Edit failure mode'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="mode-class">Class</label>
      <template v-if="editingId === null">
        <select id="mode-class" v-model="form.class_id" class="form-select" :class="{ 'is-invalid': fieldError('class_id') }">
          <option :value="null">General — every class</option>
          <option v-for="c in classChoices" :key="c.id" :value="c.id">{{ c.code }} — {{ c.name }}</option>
        </select>
        <div class="invalid-feedback">{{ fieldError("class_id") }}</div>
        <div class="form-text">General symptoms (noise, leak) are offered for every class. Cannot be changed later.</div>
      </template>
      <div v-else id="mode-class" class="form-control-plaintext fw-semibold">{{ editingClass }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="mode-code">Code</label>
      <input id="mode-code" v-model="form.code" class="form-control" :class="{ 'is-invalid': fieldError('code') }" maxlength="8" />
      <div class="invalid-feedback">{{ fieldError("code") }}</div>
      <div class="form-text">Up to 8 letters and digits, e.g. NOI or NBP (ISO 14224 codes where one fits).</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="mode-label">Symptom</label>
      <input id="mode-label" v-model="form.label" class="form-control" :class="{ 'is-invalid': fieldError('label') }" maxlength="60" />
      <div class="invalid-feedback">{{ fieldError("label") }}</div>
      <div class="form-text">What the operator sees, in plain words, e.g. Not building pressure.</div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="mode-description">Description <span class="text-secondary">(optional)</span></label>
      <input id="mode-description" v-model="form.description" class="form-control" :class="{ 'is-invalid': fieldError('description') }" maxlength="255" />
      <div class="invalid-feedback">{{ fieldError("description") }}</div>
      <div class="form-text">Help text: the ISO name, or what to look for.</div>
    </div>
  </FormModal>
</template>
