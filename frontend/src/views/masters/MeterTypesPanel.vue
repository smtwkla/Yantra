<script setup>
/**
 * Meter types — the catalogue of quantities a model or a machine can carry later (S037):
 * run hours, strokes, oil temperature, "oil level above min". A kind says how readings behave
 * (counter, gauge, amount per period, yes / no). Edited by engineers and up, and IT admin
 * (equipment:edit), like models; everyone with masters:read sees the list.
 */
import { computed, onMounted, ref } from "vue";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { userPermissions } from "../../stores/auth";
import { ensureMeterTypes, meterTypes } from "../../stores/masters";
import { KIND_LABELS } from "../../utils/meterLabels";
import { useMasterForm } from "./useMasterForm";

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const showInactive = ref(false);
const loadError = ref("");

const rows = computed(() => (meterTypes.value ?? []).filter((m) => showInactive.value || m.active));

const KINDS = [
  { value: "counter", label: KIND_LABELS.counter, help: "A running total that only goes up, such as run hours or strokes." },
  { value: "gauge", label: KIND_LABELS.gauge, help: "A level that goes up and down, such as a temperature." },
  { value: "amount", label: KIND_LABELS.amount, help: "How much in the period just ended, such as a shift's production." },
  { value: "yes_no", label: KIND_LABELS.yes_no, help: "A check with two answers, such as Oil level above min." },
];
const DECIMAL_CHOICES = [0, 1, 2, 3];

function kindText(m) {
  if (m.kind === "yes_no") return `Yes / No, expects ${m.expected_answer === "yes" ? "Yes" : "No"}`;
  return KIND_LABELS[m.kind] ?? m.kind;
}

async function reload() {
  loadError.value = "";
  try {
    await ensureMeterTypes({ refresh: true });
  } catch (err) {
    loadError.value = err.message;
  }
}

// Always all five fields, so a change of kind never meets a value hidden from the screen
function toBody(f) {
  const yesNo = f.kind === "yes_no";
  return {
    name: f.name,
    kind: f.kind,
    unit: yesNo ? null : f.unit,
    decimals: yesNo ? 0 : f.decimals,
    expected_answer: yesNo ? f.expected_answer : null,
  };
}

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} =
  useMasterForm({
    path: "/api/masters/meter-types",
    blank: () => ({ name: "", unit: "", kind: "counter", expected_answer: null, decimals: 0 }),
    fromRecord: (m) => ({
      name: m.name, unit: m.unit ?? "", kind: m.kind, expected_answer: m.expected_answer, decimals: m.decimals,
    }),
    toBody,
    label: (m) => m.name,
    reload,
  });

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span><i class="fa-solid fa-gauge me-2"></i>Meter types</span>
      <div class="d-flex align-items-center gap-3">
        <div class="form-check form-switch mb-0">
          <input id="meter-types-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="meter-types-inactive">Show inactive</label>
        </div>
        <button v-if="canEdit" class="btn btn-sm btn-primary" @click="openCreate">
          <i class="fa-solid fa-plus me-1"></i>Add meter type
        </button>
      </div>
    </div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="meterTypes === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows.length === 0 && !loadError" class="text-secondary">No meter types yet.</div>
      <div v-else-if="rows.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr><th>Name</th><th>Unit</th><th>Kind</th><th>Decimals</th><th>Active</th><th v-if="canEdit"></th></tr>
          </thead>
          <tbody>
            <tr v-for="m in rows" :key="m.id" :class="{ 'text-secondary': !m.active }">
              <td class="fw-semibold">{{ m.name }}</td>
              <td>{{ m.unit ?? "—" }}</td>
              <td>{{ kindText(m) }}</td>
              <td>{{ m.kind === "yes_no" ? "—" : m.decimals }}</td>
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

  <FormModal ref="modal" :title="editingId === null ? 'Add meter type' : 'Edit meter type'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
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
      <label class="form-label" for="meter-type-name">Name</label>
      <input id="meter-type-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="60" />
      <div v-if="fieldError('name')" class="invalid-feedback d-block">{{ fieldError("name") }}</div>
      <div class="form-text">What is measured, such as Run hours. For a Yes / No type, the question, such as Oil level above min.</div>
    </div>
    <div class="mb-3">
      <div class="form-label">Kind</div>
      <div v-for="k in KINDS" :key="k.value" class="mb-1">
        <div class="form-check">
          <input :id="`meter-type-kind-${k.value}`" v-model="form.kind" class="form-check-input" type="radio" name="meter-type-kind" :value="k.value" />
          <label class="form-check-label" :for="`meter-type-kind-${k.value}`">{{ k.label }}</label>
        </div>
        <div class="form-text mt-0 ms-4">{{ k.help }}</div>
      </div>
      <div v-if="fieldError('kind')" class="invalid-feedback d-block">{{ fieldError("kind") }}</div>
    </div>
    <template v-if="form.kind === 'yes_no'">
      <div class="mb-0">
        <div class="form-label">Expected answer</div>
        <div class="form-check form-check-inline">
          <input id="meter-type-answer-yes" v-model="form.expected_answer" class="form-check-input" type="radio" name="meter-type-answer" value="yes" />
          <label class="form-check-label" for="meter-type-answer-yes">Yes</label>
        </div>
        <div class="form-check form-check-inline">
          <input id="meter-type-answer-no" v-model="form.expected_answer" class="form-check-input" type="radio" name="meter-type-answer" value="no" />
          <label class="form-check-label" for="meter-type-answer-no">No</label>
        </div>
        <div v-if="fieldError('expected_answer')" class="invalid-feedback d-block">{{ fieldError("expected_answer") }}</div>
        <div class="form-text">The answer that means all is well.</div>
      </div>
    </template>
    <template v-else>
      <div class="mb-3">
        <label class="form-label" for="meter-type-unit">Unit</label>
        <input id="meter-type-unit" v-model="form.unit" class="form-control" :class="{ 'is-invalid': fieldError('unit') }" maxlength="20" />
        <div v-if="fieldError('unit')" class="invalid-feedback d-block">{{ fieldError("unit") }}</div>
        <div class="form-text">The unit of measure, as written on the meter, such as h, kWh, °C.</div>
      </div>
      <div class="mb-0">
        <label class="form-label" for="meter-type-decimals">Decimals</label>
        <select id="meter-type-decimals" v-model="form.decimals" class="form-select" :class="{ 'is-invalid': fieldError('decimals') }">
          <option v-for="n in DECIMAL_CHOICES" :key="n" :value="n">{{ n }}</option>
        </select>
        <div v-if="fieldError('decimals')" class="invalid-feedback d-block">{{ fieldError("decimals") }}</div>
        <div class="form-text">How many decimals a reading may have: 1 for 62.5 °C, 0 for strokes.</div>
      </div>
    </template>
  </FormModal>
</template>
