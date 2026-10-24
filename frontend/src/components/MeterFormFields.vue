<script setup>
/**
 * The fields of a meter dialog (S038 § 1.1, § 1.3), shared by the model's and the node's: the
 * meter type select (on add only) and, for a gauge, Min and Max. The rules (decimals, Min not
 * above Max, no limits on other kinds) are the backend's; a refusal is shown beside its field.
 */
import { computed } from "vue";
import { meterTypeOption } from "../utils/meterLabels";

const props = defineProps({
  // The types that may be added; null when the dialog sets limits on an existing meter
  choices: { type: Array, default: null },
  // The meter type the limits are for (the chosen one, or the existing meter's)
  meterType: { type: Object, default: null },
  // Shown in place of the select when nothing is left to add
  emptyText: { type: String, required: true },
  fieldError: { type: Function, required: true },
  idPrefix: { type: String, required: true },
});

const meterTypeId = defineModel("meterTypeId", { type: [Number, String], default: "" });
const minValue = defineModel("minValue", { type: String, default: "" });
const maxValue = defineModel("maxValue", { type: String, default: "" });

const isGauge = computed(() => props.meterType?.kind === "gauge");
const decimalsHelp = computed(() => {
  const decimals = props.meterType?.decimals ?? 0;
  if (decimals === 0) return "Whole numbers.";
  return `Up to ${decimals} decimal${decimals > 1 ? "s" : ""}.`;
});
</script>

<template>
  <div v-if="choices" class="mb-3">
    <template v-if="choices.length">
      <label class="form-label" :for="`${idPrefix}-type`">Meter type</label>
      <select :id="`${idPrefix}-type`" v-model="meterTypeId" class="form-select" :class="{ 'is-invalid': fieldError('meter_type_id') }">
        <option value="" disabled>Select a meter type…</option>
        <option v-for="t in choices" :key="t.id" :value="t.id">{{ meterTypeOption(t) }}</option>
      </select>
    </template>
    <div v-else class="text-secondary">{{ emptyText }}</div>
    <div v-if="fieldError('meter_type_id')" class="invalid-feedback d-block">{{ fieldError("meter_type_id") }}</div>
  </div>
  <div v-if="isGauge" class="row g-3">
    <div class="col-6">
      <label class="form-label" :for="`${idPrefix}-min`">Min</label>
      <div class="input-group">
        <input :id="`${idPrefix}-min`" v-model="minValue" class="form-control" :class="{ 'is-invalid': fieldError('min_value') }" inputmode="decimal" autocomplete="off" />
        <span class="input-group-text">{{ meterType.unit }}</span>
      </div>
      <div v-if="fieldError('min_value')" class="invalid-feedback d-block">{{ fieldError("min_value") }}</div>
    </div>
    <div class="col-6">
      <label class="form-label" :for="`${idPrefix}-max`">Max</label>
      <div class="input-group">
        <input :id="`${idPrefix}-max`" v-model="maxValue" class="form-control" :class="{ 'is-invalid': fieldError('max_value') }" inputmode="decimal" autocomplete="off" />
        <span class="input-group-text">{{ meterType.unit }}</span>
      </div>
      <div v-if="fieldError('max_value')" class="invalid-feedback d-block">{{ fieldError("max_value") }}</div>
    </div>
    <div class="col-12 form-text mt-1">The range of a good reading. Leave a box empty for no limit on that side. {{ decimalsHelp }}</div>
  </div>
</template>
