<script setup>
/**
 * Unit access — which units each user may work at (ISO 27001 A.5.15: the "where"
 * of access control; roles are the "what"). Read needs masters:read_senior,
 * edit needs masters:edit. Yantra cannot list Keycloak users, so the table shows
 * users who already have access and a new user is added by typing a username.
 */
import { computed, nextTick, onMounted, ref } from "vue";
import { apiGet, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureUnits, units } from "../../stores/masters";
import { formSnapshot } from "../../utils/formSnapshot";

const canEdit = computed(() => userPermissions.value.includes("masters:edit"));
const items = ref(null);
const loadError = ref("");

const modal = ref(null);
const username = ref("");
const isNewUser = ref(true);
const selected = ref(new Set());
const saving = ref(false);
const error = ref(null); // {field, message}

// Offer the active units, plus inactive ones the user already holds (so they can be revoked)
// Fixed when the dialog opens, so unticking one by mistake does not make it vanish.
const heldInactiveIds = ref(new Set());
const choices = computed(() =>
  (units.value ?? []).filter((u) => u.active || heldInactiveIds.value.has(u.id))
);

async function reload() {
  loadError.value = "";
  try {
    const [list] = await Promise.all([apiGet("/api/masters/user-units"), ensureUnits()]);
    items.value = list.items;
  } catch (err) {
    loadError.value = err.message;
  }
}

function load(name, heldUnits, isNew) {
  username.value = name;
  isNewUser.value = isNew;
  selected.value = new Set(heldUnits.map((u) => u.id));
  heldInactiveIds.value = new Set(heldUnits.filter((u) => !u.active).map((u) => u.id));
  error.value = null;
}

// This dialog does not use useFormModal, so it keeps its own snapshot (see there for the why)
const snapshot = ref(null);
const dirty = computed(
  () => snapshot.value !== null && formSnapshot({ username: username.value, selected: selected.value }) !== snapshot.value
);
const markClean = () => {
  snapshot.value = formSnapshot({ username: username.value, selected: selected.value });
};

function open(name, heldUnits, isNew) {
  load(name, heldUnits, isNew);
  snapshot.value = null;
  modal.value.open();
  nextTick(markClean);
}

function toggle(unitId) {
  const next = new Set(selected.value);
  if (next.has(unitId)) next.delete(unitId);
  else next.add(unitId);
  selected.value = next;
}

async function save() {
  const name = username.value.trim().toLowerCase();
  // A PUT replaces the whole set, so "Add user" for someone who already has access
  // would silently revoke their other units: show their current set instead.
  const existing = isNewUser.value ? items.value?.find((i) => i.username === name) : null;
  if (existing) {
    load(existing.username, existing.units, false);
    nextTick(markClean); // the dialog was re-filled by code: what is shown now is the baseline
    error.value = {
      field: "username",
      message: "This user already has unit access; their current units are shown. Review and save.",
    };
    return;
  }
  saving.value = true;
  error.value = null;
  try {
    await apiPut(`/api/masters/user-units/${encodeURIComponent(name)}`, { unit_ids: [...selected.value] });
  } catch (err) {
    error.value = { field: err.field, message: err.message };
    return;
  } finally {
    saving.value = false;
  }
  modal.value.close();
  await reload();
}

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span><i class="fa-solid fa-user-lock me-2"></i>Unit access</span>
      <button v-if="canEdit" class="btn btn-sm btn-primary" @click="open('', [], true)">
        <i class="fa-solid fa-plus me-1"></i>Add user
      </button>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-else-if="items === null" class="text-secondary">Loading…</div>
      <div v-else-if="items.length === 0" class="text-secondary">No user has unit access yet.</div>
      <div v-else class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>User</th><th>Units</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.username">
              <td class="fw-semibold">{{ item.username }}</td>
              <td>
                <span
                  v-for="u in item.units"
                  :key="u.id"
                  class="badge me-1"
                  :class="u.active ? 'text-bg-primary' : 'text-bg-secondary opacity-50'"
                  :title="u.active ? u.name : `${u.name} (inactive)`"
                >{{ u.full_code }}</span>
              </td>
              <td v-if="canEdit" class="text-end">
                <button class="btn btn-sm btn-outline-secondary" title="Edit" @click="open(item.username, item.units, false)">
                  <i class="fa-solid fa-pen"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <FormModal
    ref="modal"
    :title="isNewUser ? 'Add user' : `Unit access — ${username}`"
    :saving="saving"
    :dirty="dirty"
    :error="error && error.field !== 'username' && error.field !== 'unit_ids' ? error.message : ''"
    @save="save"
  >
    <div class="mb-3">
      <label class="form-label" for="ua-username">Username</label>
      <input
        id="ua-username"
        v-model="username"
        class="form-control"
        :class="{ 'is-invalid': error?.field === 'username' }"
        :readonly="!isNewUser"
        maxlength="100"
      />
      <div class="invalid-feedback">{{ error?.message }}</div>
      <div class="form-text">The Keycloak username, in lower case. It is not checked against Keycloak.</div>
    </div>
    <div class="mb-0">
      <div class="form-label">Units</div>
      <div v-if="error?.field === 'unit_ids'" class="alert alert-danger py-2">{{ error.message }}</div>
      <div v-if="units === null" class="text-secondary">Loading…</div>
      <div v-else-if="choices.length === 0" class="text-secondary">No units exist yet.</div>
      <div
        v-for="u in choices"
        :key="u.id"
        class="form-check"
        :class="{ 'text-secondary': !u.active }"
      >
        <input :id="`ua-unit-${u.id}`" class="form-check-input" type="checkbox" :checked="selected.has(u.id)" @change="toggle(u.id)" />
        <label class="form-check-label" :for="`ua-unit-${u.id}`">
          {{ u.full_code }} — {{ u.name }}<span v-if="!u.active"> (inactive)</span>
        </label>
      </div>
      <div class="form-text">Unticking every unit removes the user from this list.</div>
    </div>
  </FormModal>
</template>
