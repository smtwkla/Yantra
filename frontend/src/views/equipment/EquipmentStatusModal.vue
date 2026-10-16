<script setup>
/**
 * Change-status dialog (docs/steps/S003-equipment-screens/1-brief.md § 4.5). Sends only
 * `status`. Scrapping is final, so choosing it replaces Save with an inline Yes / No:
 * Yes is the only way to save it.
 *
 * The parent calls open(node) through a template ref and handles @saved.
 */
import { computed, ref } from "vue";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { STATUS_HELP, STATUS_LABELS } from "../../utils/equipmentLabels";

const emit = defineEmits(["saved"]);

const STATUS_ORDER = ["in_service", "standby", "out_of_use", "scrapped"];

const node = ref(null);

const { modal, form, saving, dirty, fieldError, modalError, openEdit, save } = useFormModal({
  path: "/api/equipment",
  blank: () => ({ status: "in_service" }),
  fromRecord: (record) => ({ status: record.status }),
  afterSave: (result) => emit("saved", result),
});

const scrapping = computed(() => form.value.status === "scrapped");
const saveDisabledReason = computed(() => {
  if (scrapping.value) return "Confirm with Yes";
  return form.value.status === node.value?.status ? "No change" : "";
});

function open(target) {
  node.value = target;
  openEdit(target);
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    :title="`Change status of ${node?.code ?? ''}`"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :save-disabled-reason="saveDisabledReason"
    @save="save"
  >
    <div class="mb-0">
      <label class="form-label" for="status-choice">Status</label>
      <select id="status-choice" v-model="form.status" class="form-select" :class="{ 'is-invalid': fieldError('status') }">
        <option v-for="s in STATUS_ORDER" :key="s" :value="s">{{ STATUS_LABELS[s] }}</option>
      </select>
      <div class="invalid-feedback">{{ fieldError("status") }}</div>
      <div class="form-text">{{ STATUS_HELP[form.status] }}</div>
    </div>
    <div v-if="scrapping" class="alert alert-warning d-flex flex-wrap align-items-center gap-2 mt-3 mb-0">
      <span>Scrap <strong>{{ node?.code }}</strong>? This is final — the record becomes read-only.</span>
      <button type="button" class="btn btn-sm btn-danger" :disabled="saving" @click="save">Yes</button>
      <button type="button" class="btn btn-sm btn-outline-secondary" @click="form.status = node.status">No</button>
    </div>
  </FormModal>
</template>
