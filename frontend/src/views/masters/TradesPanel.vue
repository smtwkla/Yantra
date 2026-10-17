<script setup>
/**
 * Trades — the kinds of maintenance work a person can do (electrician, fitter, …).
 * ISO 14224 calls this the maintenance "discipline"; SMRP calls it a craft. Edited by
 * engineers and up, and IT admin (people:edit).
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureTrades, trades } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("people:edit"));
const showInactive = ref(false);
const loadError = ref("");

const rows = computed(() => (trades.value ?? []).filter((t) => showInactive.value || t.active));

async function reload() {
  loadError.value = "";
  try {
    await ensureTrades({ refresh: true });
  } catch (err) {
    loadError.value = err.message;
  }
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/trades",
    blank: () => ({ name: "" }),
    fromRecord: (t) => ({ name: t.name }),
    label: (t) => t.name,
    reload,
  });

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span><i class="fa-solid fa-screwdriver-wrench me-2"></i>Trades</span>
      <div class="d-flex align-items-center gap-3">
        <div class="form-check form-switch mb-0">
          <input id="trades-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="trades-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add trade
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="trades === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No trades yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Name</th><th>Status</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="t in rows" :key="t.id" :class="{ 'text-secondary': !t.active }">
              <td class="fw-semibold">{{ t.name }}</td>
              <td><span class="badge" :class="t.active ? 'text-bg-success' : 'text-bg-secondary'">{{ t.active ? "Active" : "Inactive" }}</span></td>
              <td v-if="canEdit" class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="openEdit(t)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add trade' : 'Edit trade'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="trade-name">Name</label>
      <input id="trade-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="50" />
      <div class="invalid-feedback">{{ fieldError("name") }}</div>
      <div class="form-text">The kind of work, e.g. Electrician, Fitter (trade, or craft). A deactivated trade stays on the people who hold it.</div>
    </div>
  </FormModal>
</template>
