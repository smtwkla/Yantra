<script setup>
/**
 * Change-lifecycle dialog (docs/steps/S003-equipment-screens/1-brief.md § 4.5; renamed from
 * status in S030). Sends only `lifecycle`. Scrapping is final, so choosing it replaces Save
 * with an inline Yes / No: Yes is the only way to save it.
 *
 * The parent calls open(node) through a template ref and handles @saved.
 */
import { computed, ref } from "vue";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { LIFECYCLE_HELP, LIFECYCLE_LABELS } from "../../utils/equipmentLabels";

const emit = defineEmits(["saved"]);

const LIFECYCLE_ORDER = ["in_service", "standby", "out_of_use", "scrapped"];

const node = ref(null);

const { modal, form, saving, dirty, fieldError, modalError, openEdit, save } = useFormModal({
  path: "/api/equipment",
  blank: () => ({ lifecycle: "in_service" }),
  fromRecord: (record) => ({ lifecycle: record.lifecycle }),
  afterSave: (result) => emit("saved", result),
});

const scrapping = computed(() => form.value.lifecycle === "scrapped");
const saveDisabledReason = computed(() => {
  if (scrapping.value) return "Confirm with Yes";
  return form.value.lifecycle === node.value?.lifecycle ? "No change" : "";
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
    :title="`Change lifecycle of ${node?.code ?? ''}`"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :save-disabled-reason="saveDisabledReason"
    @save="save"
  >
    <div class="mb-0">
      <label class="form-label" for="lifecycle-choice">Lifecycle</label>
      <select id="lifecycle-choice" v-model="form.lifecycle" class="form-select" :class="{ 'is-invalid': fieldError('lifecycle') }">
        <option v-for="s in LIFECYCLE_ORDER" :key="s" :value="s">{{ LIFECYCLE_LABELS[s] }}</option>
      </select>
      <div v-if="fieldError('lifecycle')" class="invalid-feedback d-block">{{ fieldError("lifecycle") }}</div>
      <div class="form-text">{{ LIFECYCLE_HELP[form.lifecycle] }}</div>
    </div>
    <div v-if="scrapping" class="alert alert-warning d-flex flex-wrap align-items-center gap-2 mt-3 mb-0">
      <span>Scrap <strong>{{ node?.code }}</strong>? This is final — the record becomes read-only.</span>
      <button type="button" class="btn btn-sm btn-danger" :disabled="saving" @click="save">Yes</button>
      <button type="button" class="btn btn-sm btn-outline-secondary" @click="form.lifecycle = node.lifecycle">No</button>
    </div>
  </FormModal>
</template>
