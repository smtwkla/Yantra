<script setup>
/**
 * Maintenance actions (S016) — what was done to put it right (ISO 14224 maintenance
 * activity, Table B.5: replace, repair, adjust, …). Edited by engineers and up, and IT
 * admin (failure_codes:edit).
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureMaintenanceActions, maintenanceActions } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("failure_codes:edit"));
const showInactive = ref(false);
const loadError = ref("");

const rows = computed(() => (maintenanceActions.value ?? []).filter((a) => showInactive.value || a.active));

async function reload() {
  loadError.value = "";
  try {
    await ensureMaintenanceActions({ refresh: true });
  } catch (err) {
    loadError.value = err.message;
  }
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/maintenance-actions",
    blank: () => ({ code: "", label: "", description: "" }),
    fromRecord: (a) => ({ code: a.code, label: a.label, description: a.description ?? "" }),
    label: (a) => `${a.code} · ${a.label}`,
    reload,
  });

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span><i class="fa-solid fa-wrench me-2"></i>Maintenance actions</span>
      <div class="d-flex align-items-center flex-wrap gap-3">
        <div class="form-check form-switch mb-0">
          <input id="actions-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="actions-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add action
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="maintenanceActions === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No maintenance actions yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Code</th><th>Action</th><th>Status</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="a in rows" :key="a.id" :class="{ 'text-secondary': !a.active }">
              <td class="fw-semibold text-nowrap">{{ a.code }}</td>
              <td>
                {{ a.label }}
                <div v-if="a.description" class="small text-secondary">{{ a.description }}</div>
              </td>
              <td><span class="badge" :class="a.active ? 'text-bg-success' : 'text-bg-secondary'">{{ a.active ? "Active" : "Inactive" }}</span></td>
              <td v-if="canEdit" class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="openEdit(a)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add maintenance action' : 'Edit maintenance action'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="action-code">Code</label>
      <input id="action-code" v-model="form.code" class="form-control" :class="{ 'is-invalid': fieldError('code') }" maxlength="8" />
      <div v-if="fieldError('code')" class="invalid-feedback d-block">{{ fieldError("code") }}</div>
      <div class="form-text">Up to 8 letters and digits, parts joined by dots, e.g. 7 (ISO's numbers).</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="action-label">Action</label>
      <input id="action-label" v-model="form.label" class="form-control" :class="{ 'is-invalid': fieldError('label') }" maxlength="60" />
      <div v-if="fieldError('label')" class="invalid-feedback d-block">{{ fieldError("label") }}</div>
      <div class="form-text">What was done, e.g. Replace, Adjust, Service.</div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="action-description">Description <span class="text-secondary">(optional)</span></label>
      <input id="action-description" v-model="form.description" class="form-control" :class="{ 'is-invalid': fieldError('description') }" maxlength="255" />
      <div v-if="fieldError('description')" class="invalid-feedback d-block">{{ fieldError("description") }}</div>
    </div>
  </FormModal>
</template>
