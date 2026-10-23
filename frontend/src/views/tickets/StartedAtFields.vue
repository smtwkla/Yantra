<script setup>
/**
 * *When did work start?* on back in service after the fact (docs/steps/S018-work-tickets/1-brief.md
 * § 1, BR4-06): a date and an empty time, because one datetime-local cannot hold a date
 * without a time. The parent sends `started_at` only when the time is filled.
 *
 * The date follows the back-in-service date (`restoredAt`; null = now, so today) for as long as
 * the user has not picked another one: a night-shift start before midnight is entered by
 * changing the date. Used by MoveDialog and the raise screen's *Already fixed* (A1, BS2-03).
 */
import { computed, watch } from "vue";
import { daysAgoHint, toLocalDateValue } from "../../utils/ticketLabels";

const props = defineProps({
  restoredAt: { type: String, default: null },
  date: { type: String, default: "" },
  time: { type: String, default: "" },
  error: { type: String, default: "" },
  idPrefix: { type: String, required: true },
});
const emit = defineEmits(["update:date", "update:time"]);

// Only when both the date and the time are filled (the parent sends `started_at` the same way)
const hint = computed(() => (props.date && props.time ? daysAgoHint(`${props.date}T${props.time}`, new Date()) : ""));

function dayOf(restoredAt) {
  return restoredAt ? restoredAt.slice(0, 10) : toLocalDateValue(new Date());
}

// The day the date last followed.  Remembered, not recomputed from the old time: a screen open
// across midnight would otherwise take "today" for another day than the date shows (CR3-02)
let followedDay = props.date;

// The date still shows the followed day -> the user has not changed it: follow.  A parent that
// has already put the new day there (a dialog opened again) only re-syncs.
watch(() => props.restoredAt, (value) => {
  const day = dayOf(value);
  if (props.date === followedDay && props.date !== day) emit("update:date", day);
  if (props.date === followedDay || props.date === day) followedDay = day;
});
</script>

<template>
  <div class="mb-3">
    <label class="form-label" :for="`${idPrefix}-time`">When did work start? <span class="text-secondary">(if known)</span></label>
    <div class="d-flex gap-2">
      <input
        :value="date"
        class="form-control"
        type="date"
        aria-label="Start date"
        @input="emit('update:date', $event.target.value)"
      />
      <input
        :id="`${idPrefix}-time`"
        :value="time"
        class="form-control"
        :class="{ 'is-invalid': error }"
        type="time"
        @input="emit('update:time', $event.target.value)"
      />
    </div>
    <div v-if="error" class="invalid-feedback d-block">{{ error }}</div>
    <div v-if="hint" class="form-text">{{ hint }}</div>
  </div>
</template>
