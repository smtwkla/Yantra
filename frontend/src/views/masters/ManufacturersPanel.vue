<script setup>
/**
 * Manufacturers — the makers that equipment models belong to (docs/steps/S012-equipment-models,
 * ISO 14224 "manufacturer's name"). One record per maker, one spelling: the name is unique
 * without regard to case or repeated spaces. "Generic" (maker unknown) and "SMTW (in-house)"
 * are ordinary records. Edited by engineers and up (equipment:edit at any site).
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureManufacturers, ensureModels, manufacturers } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const showInactive = ref(false);
const loadError = ref("");

const rows = computed(() => (manufacturers.value ?? []).filter((m) => showInactive.value || m.active));

async function reload() {
  loadError.value = "";
  try {
    // Model labels carry the maker name: a rename must reach the equipment form's picker
    await Promise.all([ensureManufacturers({ refresh: true }), ensureModels({ refresh: true })]);
  } catch (err) {
    loadError.value = err.message;
  }
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/manufacturers",
    blank: () => ({ name: "" }),
    fromRecord: (m) => ({ name: m.name }),
    label: (m) => m.name,
    reload,
  });

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span><i class="fa-solid fa-industry me-2"></i>Manufacturers</span>
      <div class="d-flex align-items-center gap-3">
        <div class="form-check form-switch mb-0">
          <input id="makers-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="makers-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add manufacturer
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="manufacturers === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No manufacturers yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Name</th><th>Status</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="m in rows" :key="m.id" :class="{ 'text-secondary': !m.active }">
              <td class="fw-semibold">{{ m.name }}</td>
              <td><span class="badge" :class="m.active ? 'text-bg-success' : 'text-bg-secondary'">{{ m.active ? "Active" : "Inactive" }}</span></td>
              <td v-if="canEdit" class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="openEdit(m)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add manufacturer' : 'Edit manufacturer'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
    <div class="mb-0">
      <label class="form-label" for="maker-name">Name</label>
      <input id="maker-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" />
      <div v-if="fieldError('name')" class="invalid-feedback d-block">{{ fieldError("name") }}</div>
      <div class="form-text">
        The maker as it should always be spelled, e.g. Atlas Copco. A rename shows at once on its models and
        equipment. To deactivate it, deactivate its models first.
      </div>
    </div>
  </FormModal>
</template>
