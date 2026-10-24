<script setup>
/**
 * The waiting reason and the date of *Defer* / *Put on hold* and *Change plan*
 * (docs/steps/S019-deferred-work/1-brief.md § 1.7, BR1-16, BR2-09): a select and a date input,
 * so the dialog stays reason, date and Save on a phone. S034: the reason comes first because
 * it decides what the date means (ticketLabels.planDateKind): "Planned for" or "Check again
 * by" with a help line; three quick picks (In 7, 14, 30 days) fill the date. The date input offers today
 * to a year ahead; the server checks both rules again (tickets_core.planned_date_error).
 */
import { computed } from "vue";
import {
  PLAN_DATE_HELP, PLAN_QUICK_DAYS, PLANNED_DATE_MAX_DAYS, planDateKind, planDateLabel, toLocalDateValue, WAITING_REASON_LABELS,
} from "../../utils/ticketLabels";

defineProps({
  date: { type: String, default: "" },
  reason: { type: String, default: "" },
  dateError: { type: String, default: "" },
  reasonError: { type: String, default: "" },
  idPrefix: { type: String, required: true },
});
const emit = defineEmits(["update:date", "update:reason"]);

const today = computed(() => toLocalDateValue(new Date()));
/** A quick pick: today plus `days`, in the phone's local date as the input's min. */
function pickDays(days) {
  const day = new Date();
  day.setDate(day.getDate() + days);
  emit("update:date", toLocalDateValue(day));
}
const lastDay = computed(() => {
  const day = new Date();
  day.setDate(day.getDate() + PLANNED_DATE_MAX_DAYS);
  return toLocalDateValue(day);
});
</script>

<template>
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
  <div class="mb-3">
    <label class="form-label" :for="`${idPrefix}-date`">{{ planDateLabel(reason) }}</label>
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
    <div v-if="planDateKind(reason) === 'check'" class="form-text">{{ PLAN_DATE_HELP }}</div>
    <div class="d-flex flex-wrap gap-2 mt-2">
      <button
        v-for="days in PLAN_QUICK_DAYS"
        :key="days"
        type="button"
        class="btn btn-sm btn-outline-secondary"
        @click="pickDays(days)"
      >In {{ days }} days</button>
    </div>
    <div v-if="dateError" class="invalid-feedback d-block">{{ dateError }}</div>
  </div>
</template>
