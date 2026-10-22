<script setup>
/**
 * The planned date and the waiting reason of *Schedule* and *Change plan*
 * (docs/steps/S019-deferred-work/1-brief.md § 1.7, BR1-16, BR2-09): a date input and a
 * select, so the dialog stays date, reason and Save on a phone. The date input offers today
 * to a year ahead; the server checks both rules again (tickets_core.planned_date_error).
 */
import { computed } from "vue";
import { PLANNED_DATE_MAX_DAYS, toLocalDateValue, WAITING_REASON_LABELS } from "../../utils/ticketLabels";

defineProps({
  date: { type: String, default: "" },
  reason: { type: String, default: "" },
  dateError: { type: String, default: "" },
  reasonError: { type: String, default: "" },
  idPrefix: { type: String, required: true },
});
const emit = defineEmits(["update:date", "update:reason"]);

const today = computed(() => toLocalDateValue(new Date()));
const lastDay = computed(() => {
  const day = new Date();
  day.setDate(day.getDate() + PLANNED_DATE_MAX_DAYS);
  return toLocalDateValue(day);
});
</script>

<template>
  <div class="mb-3">
    <label class="form-label" :for="`${idPrefix}-date`">Planned date</label>
    <input
      :id="`${idPrefix}-date`"
      :value="date"
      class="form-control"
      :class="{ 'is-invalid': dateError }"
      type="date"
      :min="today"
      :max="lastDay"
      @input="emit('update:date', $event.target.value)"
    />
    <div v-if="dateError" class="invalid-feedback d-block">{{ dateError }}</div>
  </div>
  <div class="mb-3">
    <label class="form-label" :for="`${idPrefix}-reason`">Why does it wait?</label>
    <select
      :id="`${idPrefix}-reason`"
      :value="reason"
      class="form-select"
      :class="{ 'is-invalid': reasonError }"
      @change="emit('update:reason', $event.target.value)"
    >
      <option value="">—</option>
      <option v-for="(label, code) in WAITING_REASON_LABELS" :key="code" :value="code">{{ label }}</option>
    </select>
    <div v-if="reasonError" class="invalid-feedback d-block">{{ reasonError }}</div>
  </div>
</template>
