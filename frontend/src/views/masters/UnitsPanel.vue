<script setup>
/** Units — areas within a site (ISO 14224 plant/unit). Full code is SITE.UNIT. Edited by IT admin. */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { defaultSiteId, ensureSites, ensureUnits, sites, units } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("masters:edit"));
const showInactive = ref(false);
const siteFilter = ref("");
const loadError = ref("");

const rows = computed(() =>
  (units.value ?? []).filter(
    (u) => (showInactive.value || u.active) && (siteFilter.value === "" || u.site_id === siteFilter.value)
  )
);
// A unit can only be placed under an active site; when editing, its current site stays selectable
const siteChoices = computed(() => (sites.value ?? []).filter((s) => s.active || s.id === form.value.site_id));

async function reload() {
  loadError.value = "";
  try {
    await Promise.all([ensureSites(), ensureUnits()]);
  } catch (err) {
    loadError.value = err.message;
  }
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/units",
    blank: () => ({ site_id: siteFilter.value || defaultSiteId() || "", code: "", name: "", oneerp_warehouse: "" }),
    fromRecord: (u) => ({ site_id: u.site_id, code: u.code, name: u.name, oneerp_warehouse: u.oneerp_warehouse ?? "" }),
    reload,
  });

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span><i class="fa-solid fa-warehouse me-2"></i>Units</span>
      <div class="d-flex align-items-center gap-3">
        <select v-model="siteFilter" class="form-select form-select-sm w-auto" aria-label="Filter by site">
          <option value="">All sites</option>
          <option v-for="s in sites ?? []" :key="s.id" :value="s.id">{{ s.code }}</option>
        </select>
        <div class="form-check form-switch mb-0">
          <input id="units-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="units-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add unit
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="units === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No units yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Code</th><th>Name</th><th>OneERP warehouse</th><th>Status</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="u in rows" :key="u.id" :class="{ 'text-secondary': !u.active }">
              <td class="fw-semibold">{{ u.full_code }}</td>
              <td>{{ u.name }}</td>
              <td>{{ u.oneerp_warehouse }}</td>
              <td><span class="badge" :class="u.active ? 'text-bg-success' : 'text-bg-secondary'">{{ u.active ? "Active" : "Inactive" }}</span></td>
              <td v-if="canEdit" class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="openEdit(u)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add unit' : 'Edit unit'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="unit-site">Site</label>
      <select id="unit-site" v-model="form.site_id" class="form-select" :class="{ 'is-invalid': fieldError('site_id') }">
        <option value="" disabled>Select a site…</option>
        <option v-for="s in siteChoices" :key="s.id" :value="s.id">{{ s.code }} — {{ s.name }}</option>
      </select>
      <div class="invalid-feedback">{{ fieldError("site_id") }}</div>
      <div class="form-text">Cannot be changed once the unit is in use.</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="unit-code">Code</label>
      <input id="unit-code" v-model="form.code" class="form-control" :class="{ 'is-invalid': fieldError('code') }" maxlength="20" />
      <div class="invalid-feedback">{{ fieldError("code") }}</div>
      <div class="form-text">The part after the dot (e.g. FWMILL in SMTW.FWMILL). Cannot be changed once in use.</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="unit-name">Name</label>
      <input id="unit-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" />
      <div class="invalid-feedback">{{ fieldError("name") }}</div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="unit-warehouse">OneERP warehouse</label>
      <input id="unit-warehouse" v-model="form.oneerp_warehouse" class="form-control" :class="{ 'is-invalid': fieldError('oneerp_warehouse') }" maxlength="140" />
      <div class="invalid-feedback">{{ fieldError("oneerp_warehouse") }}</div>
      <div class="form-text">Optional. Exact OneERP warehouse name; one warehouse maps to one unit.</div>
    </div>
  </FormModal>
</template>
