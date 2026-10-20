<script setup>
/**
 * Failure causes (S016) — why it failed (ISO 14224 failure cause). Each cause sits in one of
 * ISO's five cause groups, so the plant's own causes still roll up the ISO way: whether
 * failures come from how the machine was made, how it is run and maintained, or how the
 * work is organised. The group may be changed later. Edited by engineers and up, and IT
 * admin (failure_codes:edit).
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureFailureCauses, failureCauses } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

// ISO 14224 Table B.3's groups, in the order the API lists them (failure_causes.cause_group)
const GROUPS = [
  { value: "design", label: "Design" },
  { value: "fabrication", label: "Fabrication / installation" },
  { value: "operation", label: "Operation / maintenance" },
  { value: "management", label: "Management" },
  { value: "misc", label: "Miscellaneous" },
];
const groupLabel = (value) => GROUPS.find((g) => g.value === value)?.label ?? value;

const canEdit = computed(() => userPermissions.value.includes("failure_codes:edit"));
const showInactive = ref(false);
const groupFilter = ref("");
const loadError = ref("");

const rows = computed(() =>
  (failureCauses.value ?? []).filter(
    (c) => (showInactive.value || c.active) && (groupFilter.value === "" || c.cause_group === groupFilter.value)
  )
);

async function reload() {
  loadError.value = "";
  try {
    await ensureFailureCauses({ refresh: true });
  } catch (err) {
    loadError.value = err.message;
  }
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/failure-causes",
    blank: () => ({ cause_group: groupFilter.value, code: "", label: "", description: "" }),
    fromRecord: (c) => ({ cause_group: c.cause_group, code: c.code, label: c.label, description: c.description ?? "" }),
    label: (c) => `${c.code} · ${c.label}`,
    reload,
  });

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span><i class="fa-solid fa-magnifying-glass me-2"></i>Failure causes</span>
      <div class="d-flex align-items-center flex-wrap gap-3">
        <select v-model="groupFilter" class="form-select form-select-sm w-auto" aria-label="Filter by cause group">
          <option value="">All groups</option>
          <option v-for="g in GROUPS" :key="g.value" :value="g.value">{{ g.label }}</option>
        </select>
        <div class="form-check form-switch mb-0">
          <input id="causes-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="causes-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add cause
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="failureCauses === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No failure causes here.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Code</th><th>Cause</th><th>Group</th><th>Status</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="c in rows" :key="c.id" :class="{ 'text-secondary': !c.active }">
              <td class="fw-semibold text-nowrap">{{ c.code }}</td>
              <td>
                {{ c.label }}
                <div v-if="c.description" class="small text-secondary">{{ c.description }}</div>
              </td>
              <td>{{ groupLabel(c.cause_group) }}</td>
              <td><span class="badge" :class="c.active ? 'text-bg-success' : 'text-bg-secondary'">{{ c.active ? "Active" : "Inactive" }}</span></td>
              <td v-if="canEdit" class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="openEdit(c)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add failure cause' : 'Edit failure cause'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="cause-group">Cause group</label>
      <select id="cause-group" v-model="form.cause_group" class="form-select" :class="{ 'is-invalid': fieldError('cause_group') }">
        <option value="" disabled>Select a group…</option>
        <option v-for="g in GROUPS" :key="g.value" :value="g.value">{{ g.label }}</option>
      </select>
      <div class="invalid-feedback">{{ fieldError("cause_group") }}</div>
      <div class="form-text">ISO 14224's five groups: reports roll the plant's own causes up into them.</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="cause-code">Code</label>
      <input id="cause-code" v-model="form.code" class="form-control" :class="{ 'is-invalid': fieldError('code') }" maxlength="8" />
      <div class="invalid-feedback">{{ fieldError("code") }}</div>
      <div class="form-text">Up to 8 letters and digits, parts joined by dots, e.g. 3.4 (ISO's numbers).</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="cause-label">Cause</label>
      <input id="cause-label" v-model="form.label" class="form-control" :class="{ 'is-invalid': fieldError('label') }" maxlength="60" />
      <div class="invalid-feedback">{{ fieldError("label") }}</div>
      <div class="form-text">Why it failed, e.g. Expected wear and tear, Oil contamination.</div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="cause-description">Description <span class="text-secondary">(optional)</span></label>
      <input id="cause-description" v-model="form.description" class="form-control" :class="{ 'is-invalid': fieldError('description') }" maxlength="255" />
      <div class="invalid-feedback">{{ fieldError("description") }}</div>
    </div>
  </FormModal>
</template>
