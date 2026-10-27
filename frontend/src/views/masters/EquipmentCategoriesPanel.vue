<script setup>
/**
 * Equipment categories (S063) — a group of equipment classes, ISO 14224's equipment category
 * (Lifting equipment, Conveyors, …). A name only; each class picks its category in Equip Class.
 * Edited by engineers and up (equipment:edit, as classes). Deactivating is refused while an
 * active class is in the category; the refusal shows at the top of the dialog.
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureEquipmentCategories, equipmentCategories } from "../../stores/masters";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const showInactive = ref(false);
const loadError = ref("");

const rows = computed(() => (equipmentCategories.value ?? []).filter((c) => showInactive.value || c.active));

async function reload() {
  loadError.value = "";
  try {
    await ensureEquipmentCategories({ refresh: true });
  } catch (err) {
    loadError.value = err.message;
  }
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/equipment-categories",
    blank: () => ({ name: "" }),
    fromRecord: (c) => ({ name: c.name }),
    label: (c) => c.name,
    reload,
  });

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span><i class="fa-solid fa-layer-group me-2"></i>Equipment categories</span>
      <div class="d-flex align-items-center gap-3">
        <div class="form-check form-switch mb-0">
          <input id="categories-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="categories-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add category
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="equipmentCategories === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">
        <template v-if="equipmentCategories.length">No active categories. Turn on Show inactive to see the others.</template>
        <template v-else-if="canEdit">No equipment categories yet. Add one, then pick it for each class in Equip Class.</template>
        <template v-else>No equipment categories yet.</template>
      </div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Name</th><th>Classes</th><th>Status</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="c in rows" :key="c.id" :class="{ 'text-secondary': !c.active }">
              <td class="fw-semibold">{{ c.name }}</td>
              <td>{{ c.class_count }}</td>
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

  <FormModal ref="modal" :title="editingId === null ? 'Add equipment category' : 'Edit equipment category'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="category-name">Name</label>
      <input id="category-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="50" />
      <div v-if="fieldError('name')" class="invalid-feedback d-block">{{ fieldError("name") }}</div>
      <div class="form-text">A group of classes, e.g. Lifting equipment, Conveyors, Power tools. Each class can be in one category.</div>
    </div>
  </FormModal>
</template>
