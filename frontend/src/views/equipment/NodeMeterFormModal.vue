<script setup>
/**
 * A node's meter dialog (S038 § 1.3): Add meter (an own meter: an active type not already on
 * this machine), or Set limits on a gauge — an override of the model's limits, or an own
 * gauge's. Use the model's limits (footer, only while overridden) clears the override.
 *
 * The parent calls openAdd(node, meters) or openLimits(node, meter) through a template ref
 * and handles @saved (the API answers with the node's meters).
 */
import { computed, ref } from "vue";
import { apiPost, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import MeterFormFields from "../../components/MeterFormFields.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ensureMeterTypes } from "../../stores/masters";
import { limitsBody } from "../../utils/meterLabels";

const emit = defineEmits(["saved"]);

const node = ref(null);
const editingMeter = ref(null); // the node's meter whose limits are set; null on add
const choices = ref([]);

const { modal, form, saving, dirty, fieldError, modalError, openCreate, openEdit, send } = useFormModal({
  path: "/api/equipment",
  blank: () => ({ meter_type_id: "", min_value: "", max_value: "" }),
  fromRecord: (meter) => ({ min_value: meter.min_value ?? "", max_value: meter.max_value ?? "" }),
  label: (meter) => meter.meter_type.name,
  afterSave: (result) => emit("saved", result),
});

const meterType = computed(() =>
  editingMeter.value ? editingMeter.value.meter_type : choices.value.find((t) => t.id === form.value.meter_type_id) ?? null
);
const saveDisabledReason = computed(() => (editingMeter.value || choices.value.length ? "" : "No meter type to add"));
const meterUrl = () => `/api/equipment/${node.value.id}/meters/${editingMeter.value.meter_type.id}`;

async function openAdd(target, meters) {
  node.value = target;
  editingMeter.value = null;
  const inForce = new Set(meters.map((m) => m.meter_type.id));
  const types = await ensureMeterTypes({ refresh: true });
  choices.value = types.filter((t) => t.active && !inForce.has(t.id));
  openCreate();
}

function openLimits(target, meter) {
  node.value = target;
  editingMeter.value = meter;
  choices.value = [];
  // useFormModal keys an edit by id; a node's meter is keyed by its meter type (S038 § 7.3)
  openEdit({ ...meter, id: meter.meter_type.id });
}

function save() {
  if (editingMeter.value) {
    return send(() => apiPut(meterUrl(), limitsBody(form.value, meterType.value)));
  }
  const body = { meter_type_id: form.value.meter_type_id === "" ? null : form.value.meter_type_id,
                 ...limitsBody(form.value, meterType.value) };
  return send(() => apiPost(`/api/equipment/${node.value.id}/meters`, body));
}

function useModelLimits() {
  return send(() => apiPut(meterUrl(), { use_model_limits: true }));
}

defineExpose({ openAdd, openLimits });
</script>

<template>
  <FormModal
    ref="modal"
    :title="editingMeter ? `Set limits · ${editingMeter.meter_type.name}` : 'Add meter'"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :save-disabled-reason="saveDisabledReason"
    @save="save"
  >
    <template v-if="editingMeter?.overridden" #footer-left>
      <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="saving" @click="useModelLimits">
        Use the model's limits
      </button>
    </template>
    <p class="text-secondary small">
      {{ node?.code }} — {{ node?.name }}
      <template v-if="editingMeter?.source === 'model'"><br />Model default — {{ editingMeter.model_limits_text }}</template>
    </p>
    <MeterFormFields
      v-model:meter-type-id="form.meter_type_id"
      v-model:min-value="form.min_value"
      v-model:max-value="form.max_value"
      :choices="editingMeter ? null : choices"
      :meter-type="meterType"
      empty-text="Every meter type is on this machine already. Add meter types in Masters › Meter types."
      :field-error="fieldError"
      id-prefix="node-meter"
    />
  </FormModal>
</template>
