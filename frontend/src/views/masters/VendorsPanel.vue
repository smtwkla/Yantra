<script setup>
/**
 * Vendors — the outside firms the plant buys maintenance from (docs/steps/S079-vendor-master,
 * ISO 9001 § 8.4, ISO 55001 § 8.3). One record per firm, one spelling: the name is unique without
 * regard to case or repeated spaces. A contractor's Team record names its vendor (Team dialog).
 * Edited by engineers and up (equipment:edit at any site); the API sends the phone only to them.
 * A vendor may be deactivated while people are linked: the links stay as history (S079 D5).
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureVendors, vendors } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const showInactive = ref(false);
const loadError = ref("");

const rows = computed(() => (vendors.value ?? []).filter((v) => showInactive.value || v.active));

/** The phone, then the note, joined by " · " (only what is set). */
function details(v) {
  return [v.phone, v.note].filter(Boolean).join(" · ");
}

async function reload() {
  loadError.value = "";
  try {
    // Fresh each time the tab opens, so the People count is current
    await ensureVendors({ refresh: true });
  } catch (err) {
    loadError.value = err.message;
  }
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/vendors",
    blank: () => ({ name: "", phone: "", note: "" }),
    fromRecord: (v) => ({ name: v.name, phone: v.phone ?? "", note: v.note ?? "" }),
    toBody: (f) => ({ name: f.name, phone: f.phone.trim() || null, note: f.note.trim() || null }),
    label: (v) => v.name,
    reload,
  });

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span><i class="fa-solid fa-handshake me-2"></i>Vendors</span>
      <div class="d-flex align-items-center gap-3">
        <div class="form-check form-switch mb-0">
          <input id="vendors-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="vendors-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add vendor
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="vendors === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError && vendors.length === 0" class="text-secondary">
        No vendors yet. Add the first one with <em>Add vendor</em>.
      </div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">
        No active vendors. Turn on <em>Show inactive</em> to see the others.
      </div>
      <template v-else-if="rows.length">
        <div class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead>
              <tr><th>Name</th><th class="text-end">People</th><th>Status</th><th v-if="canEdit"></th></tr>
            </thead>
            <tbody>
              <tr v-for="v in rows" :key="v.id" :class="{ 'text-secondary': !v.active }">
                <td>
                  <div class="fw-semibold">{{ v.name }}</div>
                  <div v-if="details(v)" class="small text-secondary">{{ details(v) }}</div>
                </td>
                <td class="text-end">
                  <span v-if="v.people_count">{{ v.people_count }}</span>
                  <span v-else class="text-secondary">None</span>
                </td>
                <td><span class="badge" :class="v.active ? 'text-bg-success' : 'text-bg-secondary'">{{ v.active ? "Active" : "Inactive" }}</span></td>
                <td v-if="canEdit" class="text-end text-nowrap">
                  <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="openEdit(v)">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="form-text mt-2">
          People: the active Team records linked to the vendor. A vendor with no people cannot be assigned to
          tickets. Link one in Team.
        </div>
      </template>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add vendor' : 'Edit vendor'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="vendor-name">Name</label>
      <input id="vendor-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" />
      <div v-if="fieldError('name')" class="invalid-feedback d-block">{{ fieldError("name") }}</div>
      <div class="form-text">The firm, as it should always be spelled, e.g. Atlas Copco.</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="vendor-phone">Phone (optional)</label>
      <input id="vendor-phone" v-model="form.phone" type="tel" inputmode="tel" class="form-control" :class="{ 'is-invalid': fieldError('phone') }" maxlength="20" />
      <div v-if="fieldError('phone')" class="invalid-feedback d-block">{{ fieldError("phone") }}</div>
      <div class="form-text">
        The firm's office number. The breakdown number goes on the contract (Masters › Contracts).
      </div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="vendor-note">Note (optional)</label>
      <input id="vendor-note" v-model="form.note" class="form-control" :class="{ 'is-invalid': fieldError('note') }" maxlength="255" />
      <div v-if="fieldError('note')" class="invalid-feedback d-block">{{ fieldError("note") }}</div>
      <div class="form-text">What the firm maintains, e.g. Screw compressors, MCC2. Do not enter prices here.</div>
    </div>
  </FormModal>
</template>
