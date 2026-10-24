<script setup>
/**
 * Add a meter to a model, or set a model meter's limits (S038 § 1.1). Add offers the active
 * meter types not yet on the model; a gauge takes optional Min and Max, the defaults every
 * machine of the model shows until one overrides them.
 *
 * The parent calls openAdd(model, meters) or openLimits(model, meter) through a template ref
 * and handles @saved.
 */
import { computed, ref } from "vue";
import { apiPost, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import MeterFormFields from "../../components/MeterFormFields.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ensureMeterTypes } from "../../stores/masters";
import { limitsBody } from "../../utils/meterLabels";

const emit = defineEmits(["saved"]);

const model = ref(null);
const editingMeter = ref(null); // the model meter whose limits are set; null on add
const choices = ref([]);

const { modal, form, saving, dirty, fieldError, modalError, openCreate, openEdit, send } = useFormModal({
  path: "/api/masters/model-meters",
  blank: () => ({ meter_type_id: "", min_value: "", max_value: "" }),
  fromRecord: (meter) => ({ min_value: meter.min_value ?? "", max_value: meter.max_value ?? "" }),
  label: (meter) => meter.meter_type.name,
  afterSave: (result) => emit("saved", result),
});

const meterType = computed(() =>
  editingMeter.value ? editingMeter.value.meter_type : choices.value.find((t) => t.id === form.value.meter_type_id) ?? null
);
const saveDisabledReason = computed(() => (editingMeter.value || choices.value.length ? "" : "No meter type to add"));

async function openAdd(target, meters) {
  model.value = target;
  editingMeter.value = null;
  const onModel = new Set(meters.map((m) => m.meter_type.id));
  const types = await ensureMeterTypes({ refresh: true });
  choices.value = types.filter((t) => t.active && !onModel.has(t.id));
  openCreate();
}

function openLimits(target, meter) {
  model.value = target;
  editingMeter.value = meter;
  choices.value = [];
  openEdit(meter);
}

function save() {
  if (editingMeter.value) {
    return send(() => apiPut(`/api/masters/model-meters/${editingMeter.value.id}`, limitsBody(form.value, meterType.value)));
  }
  const body = { meter_type_id: form.value.meter_type_id === "" ? null : form.value.meter_type_id,
                 ...limitsBody(form.value, meterType.value) };
  return send(() => apiPost(`/api/masters/equipment-models/${model.value.id}/meters`, body));
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
    <p class="text-secondary small">{{ model?.label }}</p>
    <MeterFormFields
      v-model:meter-type-id="form.meter_type_id"
      v-model:min-value="form.min_value"
      v-model:max-value="form.max_value"
      :choices="editingMeter ? null : choices"
      :meter-type="meterType"
      empty-text="Every meter type is on this model already. Add meter types in Masters › Meter types."
      :field-error="fieldError"
      id-prefix="model-meter"
    />
  </FormModal>
</template>
