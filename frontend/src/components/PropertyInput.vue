<script setup>
/**
 * PropertyInput — one input for one equipment property, by its data type (S043 § 7.3; S044
 * reuses it for an item's own values). The value is what the API takes: a number as typed text,
 * text, an option id, true / false; "" (or "—", Not set) means no value. The parent shows the
 * server's refusal through `error`. The checks themselves are the backend's. `hint` (S044) is a
 * small grey line under the input, after the refusal so the refusal stays beside its field:
 * the item dialog's "Model: 7.5 kW".
 *
 * Location (S061 § 5.2, D3): a text input for "latitude, longitude" (typed or pasted, e.g. from
 * Google Maps) and Use my current location: one browser reading on a tap (high accuracy, 20 s, no
 * cached position), shown only in a secure context with the Geolocation API. The reading fills the
 * input; the line under it says how accurate it was, or why no position came.
 */
import { computed, ref } from "vue";
import { accuracyText, locationErrorText, positionText } from "../utils/propertyFormat";

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

// Location: one reading per tap (S061 D3)
const GEO_OPTIONS = { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 };
const canLocate = typeof window !== "undefined" && window.isSecureContext && "geolocation" in navigator;
const locating = ref(false);
const locateNote = ref("");
const locateError = ref("");
const locatedText = ref(""); // what the reading put in the input; the accuracy line shows only while it stands
const accuracyShown = computed(() => (locateNote.value && value.value === locatedText.value ? locateNote.value : ""));

function useMyLocation() {
  locating.value = true;
  locateNote.value = "";
  locateError.value = "";
  navigator.geolocation.getCurrentPosition(
    (position) => {
      locating.value = false;
      locatedText.value = positionText(position.coords);
      value.value = locatedText.value;
      locateNote.value = accuracyText(position.coords.accuracy);
    },
    (err) => {
      locating.value = false;
      locateError.value = locationErrorText(err.code);
    },
    GEO_OPTIONS
  );
}
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
    <template v-else-if="property.data_type === 'geo'">
      <input
        :id="id"
        v-model="value"
        class="form-control"
        :class="{ 'is-invalid': error }"
        type="text"
        autocomplete="off"
        placeholder="11.016823, 76.955812"
      />
    </template>
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
    <template v-if="property.data_type === 'geo'">
      <button v-if="canLocate" type="button" class="btn btn-outline-secondary mt-2" :disabled="locating" @click="useMyLocation">
        <i class="fa-solid fa-location-crosshairs me-1"></i>{{ locating ? "Finding the location…" : "Use my current location" }}
      </button>
      <div v-if="locateError" class="invalid-feedback d-block">{{ locateError }}</div>
      <div v-if="accuracyShown" class="form-text">{{ accuracyShown }}</div>
    </template>
    <div v-if="hint" class="form-text">{{ hint }}</div>
  </div>
</template>
