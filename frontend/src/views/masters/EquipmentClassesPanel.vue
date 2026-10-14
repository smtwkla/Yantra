<script setup>
/**
 * Equipment classes — what a piece of equipment is (ISO 14224 equipment class).
 * The class code is also the equipment-code prefix. Edited by engineers and up.
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureEquipmentClasses, equipmentClasses } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const showInactive = ref(false);
const loadError = ref("");

const rows = computed(() => (equipmentClasses.value ?? []).filter((c) => showInactive.value || c.active));

async function reload() {
  loadError.value = "";
  try {
    await ensureEquipmentClasses();
  } catch (err) {
    loadError.value = err.message;
  }
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/equipment-classes",
    blank: () => ({ code: "", name: "" }),
    fromRecord: (c) => ({ code: c.code, name: c.name }),
    reload,
  });

onMounted(reload);
</script>

<template>
  <div class="card">
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
            <tr><th>Code (prefix)</th><th>Name</th><th>Status</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="c in rows" :key="c.id" :class="{ 'text-secondary': !c.active }">
              <td class="fw-semibold">{{ c.code }}</td>
              <td>{{ c.name }}</td>
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

  <FormModal ref="modal" :title="editingId === null ? 'Add equipment class' : 'Edit equipment class'" :saving="saving" :error="modalError" @save="save">
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
      <div class="invalid-feedback">{{ fieldError("code") }}</div>
      <div class="form-text">2–4 letters; becomes the prefix of equipment codes (e.g. VBM001). Cannot be changed once in use.</div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="class-name">Name</label>
      <input id="class-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" />
      <div class="invalid-feedback">{{ fieldError("name") }}</div>
    </div>
  </FormModal>
</template>
