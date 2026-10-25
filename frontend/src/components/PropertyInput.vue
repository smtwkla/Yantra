<script setup>
/**
 * PropertyInput — one input for one equipment property, by its data type (S043 § 7.3; S044
 * reuses it for an item's own values). The value is what the API takes: a number as typed text,
 * text, an option id, true / false; "" (or "—", Not set) means no value. The parent shows the
 * server's refusal through `error`. The checks themselves are the backend's. `hint` (S044) is a
 * small grey line under the input, after the refusal so the refusal stays beside its field:
 * the item dialog's "Model: 7.5 kW".
 */
import { computed } from "vue";

const props = defineProps({
  // {property_id, name, data_type, unit, options: [{id, label, active}]}
  property: { type: Object, required: true },
  modelValue: { type: [String, Number, Boolean], default: "" },
  error: { type: String, default: "" },
  hint: { type: String, default: "" },
});
const emit = defineEmits(["update:modelValue"]);

const id = computed(() => `property-${props.property.property_id}`);
const value = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});
const YES_NO = [
  { value: true, label: "Yes" },
  { value: false, label: "No" },
  { value: "", label: "Not set" },
];
</script>

<template>
  <div class="mb-3">
    <label v-if="property.data_type !== 'yes_no'" class="form-label" :for="id">{{ property.name }}</label>
    <div v-if="property.data_type === 'number'" class="input-group">
      <input
        :id="id"
        v-model="value"
        class="form-control"
        :class="{ 'is-invalid': error }"
        type="text"
        inputmode="decimal"
        autocomplete="off"
      />
      <span v-if="property.unit" class="input-group-text">{{ property.unit }}</span>
    </div>
    <select v-else-if="property.data_type === 'choice'" :id="id" v-model="value" class="form-select" :class="{ 'is-invalid': error }">
      <option value="">—</option>
      <option v-for="o in property.options" :key="o.id" :value="o.id">{{ o.label }}</option>
    </select>
    <input
      v-else-if="property.data_type === 'text'"
      :id="id"
      v-model="value"
      class="form-control"
      :class="{ 'is-invalid': error }"
      maxlength="100"
    />
    <template v-else>
      <div :id="`${id}-label`" class="form-label">{{ property.name }}</div>
      <div class="btn-group" role="group" :aria-labelledby="`${id}-label`">
        <button
          v-for="choice in YES_NO"
          :key="choice.label"
          type="button"
          class="btn"
          :class="[value === choice.value ? 'btn-primary' : 'btn-outline-secondary', { 'is-invalid': error && choice.value === value }]"
          :aria-pressed="value === choice.value"
          @click="value = choice.value"
        >
          {{ choice.label }}
        </button>
      </div>
    </template>
    <div v-if="error" class="invalid-feedback d-block">{{ error }}</div>
    <div v-if="hint" class="form-text">{{ hint }}</div>
  </div>
</template>
