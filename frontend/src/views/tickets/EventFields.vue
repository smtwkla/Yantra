<script setup>
/**
 * The two fields every move and re-grade dialog has (docs/steps/S018-work-tickets/1-brief.md
 * § 1, BR3-09, BR4-01; docs/steps/S051-time-field-now-tick/1-brief.md):
 * - the event time: a date-and-time input with a *Now* check box to its right.
 *   - *Now* ticked (the default): the input is read-only and shows the phone's clock, moved on
 *     every 30 seconds. `time` stays null: the server's clock decides (S018 § 5.1: a phone a few
 *     minutes off never gets a refusal for a time nobody typed).
 *   - *Now* unticked: the input is editable. Until the first edit it keeps following the clock
 *     and `time` stays null (the shown time is then the one the server will record). From the
 *     first edit on, the clock stops and `time` is what the user typed.
 *   - A cleared input stays unticked and editable (Chrome reports "" while one part is being
 *     retyped) and sends null. *Now* is ticked again by the user, or when the screen resets
 *     `time` to null.
 *   - `locked` (the readings sheet after a full save, S040 A1): check box disabled, input
 *     read-only, the clock stopped at the time of the lock.
 * - the remark, behind *Add remark* where it is optional, open where the move requires it;
 *   left out with `withRemark: false` (the raise screen's *Already fixed*, S018 A1, BS2-03).
 */
import { onBeforeUnmount, ref, watch } from "vue";
import { daysAgoHint, toLocalInputValue } from "../../utils/ticketLabels";

const REMARK_MAX = 1000;
const CLOCK_REFRESH_MS = 30_000;

const props = defineProps({
  time: { type: String, default: null },
  remark: { type: String, default: "" },
  withRemark: { type: Boolean, default: true },
  timeLabel: { type: String, default: "When" },
  remarkRequired: { type: Boolean, default: false },
  remarkLabel: { type: String, default: "Remark" },
  remarkHelp: { type: String, default: "" },
  timeError: { type: String, default: "" },
  remarkError: { type: String, default: "" },
  idPrefix: { type: String, required: true },
  // The time is shown but cannot be changed (the readings sheet after a full save, S040 A1)
  locked: { type: Boolean, default: false },
});
const emit = defineEmits(["update:time", "update:remark"]);

const nowTicked = ref(true);
const edited = ref(false); // the user has typed in the input since it was last following the clock
const shown = ref(toLocalInputValue(new Date()));
const remarkShown = ref(false);
let lastEmitted = props.time;

function emitTime(value) {
  lastEmitted = value;
  emit("update:time", value);
}

// The clock moves the shown time on until the user has typed or the field is locked
const clock = setInterval(() => {
  if (!props.locked && !edited.value) shown.value = toLocalInputValue(new Date());
}, CLOCK_REFRESH_MS);
onBeforeUnmount(() => clearInterval(clock));

// A dialog opened again starts at Now with the remark folded. Our own null (a cleared input)
// is not a reset.
watch(() => props.time, (value) => {
  if (value === null && lastEmitted !== null) {
    nowTicked.value = true;
    edited.value = false;
    shown.value = toLocalInputValue(new Date());
  }
  lastEmitted = value;
});
watch(() => props.remark, (value) => {
  if (!value) remarkShown.value = false;
});
// The clock stops at the time of the lock, and starts again with the time of the unlock
watch(() => props.locked, () => {
  if (!edited.value) shown.value = toLocalInputValue(new Date());
});

function onNowChange(event) {
  nowTicked.value = event.target.checked;
  if (nowTicked.value) {
    edited.value = false;
    shown.value = toLocalInputValue(new Date());
    emitTime(null);
  }
}

function onInput(event) {
  edited.value = true;
  shown.value = event.target.value;
  // A cleared input sends nothing: the server's clock, like an untouched one
  emitTime(shown.value || null);
}
</script>

<template>
  <div class="mb-3">
    <label class="form-label" :for="`${idPrefix}-time`">{{ timeLabel }}</label>
    <div class="d-flex align-items-center gap-3">
      <input
        :id="`${idPrefix}-time`"
        :value="shown"
        class="form-control"
        :class="{ 'is-invalid': timeError }"
        type="datetime-local"
        :readonly="locked || nowTicked"
        @input="onInput"
      />
      <label class="now-tick d-flex align-items-center gap-2" :for="`${idPrefix}-now`">
        <input
          :id="`${idPrefix}-now`"
          class="form-check-input m-0"
          type="checkbox"
          :checked="nowTicked"
          :disabled="locked"
          @change="onNowChange"
        />
        Now
      </label>
    </div>
    <div v-if="timeError" class="invalid-feedback d-block">{{ timeError }}</div>
    <div v-if="!nowTicked && daysAgoHint(shown, new Date())" class="form-text">{{ daysAgoHint(shown, new Date()) }}</div>
  </div>

  <div v-if="withRemark" class="mb-3">
    <template v-if="remarkRequired || remarkShown || remark">
      <label class="form-label" :for="`${idPrefix}-remark`">{{ remarkLabel }}</label>
      <textarea
        :id="`${idPrefix}-remark`"
        :value="remark"
        class="form-control"
        :class="{ 'is-invalid': remarkError }"
        rows="2"
        :maxlength="REMARK_MAX"
        @input="emit('update:remark', $event.target.value)"
      ></textarea>
      <div v-if="remarkHelp" class="form-text">{{ remarkHelp }}</div>
      <div v-if="remarkError" class="invalid-feedback d-block">{{ remarkError }}</div>
    </template>
    <button v-else type="button" class="btn btn-link p-0" @click="remarkShown = true">
      <i class="fa-solid fa-plus me-1"></i>Add remark
    </button>
  </div>
</template>

<style scoped>
/* The label is the tap target: at least 44 px high on a phone (S040 rule for floor screens) */
.now-tick {
  min-height: 44px;
  padding: 0 0.5rem;
  flex: none;
}
</style>
