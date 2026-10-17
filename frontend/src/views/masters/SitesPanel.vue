<script setup>
/** Sites — the facilities (ISO 14224 installation level). Edited by IT admin. */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureSites, sites } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("masters:edit"));
const showInactive = ref(false);
const loadError = ref("");

const rows = computed(() => (sites.value ?? []).filter((s) => showInactive.value || s.active));

async function reload() {
  loadError.value = "";
  try {
    await ensureSites({ refresh: true });
  } catch (err) {
    loadError.value = err.message;
  }
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/sites",
    blank: () => ({ code: "", name: "", address: "", is_default: false }),
    fromRecord: (s) => ({ code: s.code, name: s.name, address: s.address ?? "", is_default: s.is_default }),
    reload,
  });

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span><i class="fa-solid fa-location-dot me-2"></i>Sites</span>
      <div class="d-flex align-items-center gap-3">
        <div class="form-check form-switch mb-0">
          <input id="sites-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="sites-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add site
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="sites === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No sites yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Code</th><th>Name</th><th>Address</th><th>Status</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="s in rows" :key="s.id" :class="{ 'text-secondary': !s.active }">
              <td class="fw-semibold">{{ s.code }} <span v-if="s.is_default" class="badge text-bg-primary ms-1">Default</span></td>
              <td>{{ s.name }}</td>
              <td>{{ s.address }}</td>
              <td><span class="badge" :class="s.active ? 'text-bg-success' : 'text-bg-secondary'">{{ s.active ? "Active" : "Inactive" }}</span></td>
              <td v-if="canEdit" class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="openEdit(s)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add site' : 'Edit site'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="site-code">Code</label>
      <input id="site-code" v-model="form.code" class="form-control" :class="{ 'is-invalid': fieldError('code') }" maxlength="20" />
      <div class="invalid-feedback">{{ fieldError("code") }}</div>
      <div class="form-text">Cannot be changed once in use.</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="site-name">Name</label>
      <input id="site-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" />
      <div class="invalid-feedback">{{ fieldError("name") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="site-address">Address</label>
      <input id="site-address" v-model="form.address" class="form-control" :class="{ 'is-invalid': fieldError('address') }" maxlength="255" />
      <div class="invalid-feedback">{{ fieldError("address") }}</div>
    </div>
    <div class="form-check mb-0">
      <input id="site-default" v-model="form.is_default" class="form-check-input" :class="{ 'is-invalid': fieldError('is_default') }" type="checkbox" />
      <label class="form-check-label" for="site-default">Default</label>
      <div class="invalid-feedback">{{ fieldError("is_default") }}</div>
      <div class="form-text">Preselected wherever a site is chosen. Only one site can be the default.</div>
    </div>
  </FormModal>
</template>
