<script setup>
/**
 * One meter of the end-of-day sheet (docs/steps/S040-readings-sheet/1-brief.md § 1.4-§ 1.6): its
 * name and unit, the last reading, and the input; after a save, the result and Undo.
 * - From 768 px (md) the three are columns of one line; on a phone they stack.
 * - A number meter has the unit beside an input with the phone's decimal keypad; an amount also
 *   explains its period (S039).
 * - A Yes / No meter shows two large toggles instead; a second tap on the picked one clears it.
 *   The sheet's Save readings saves it with the others (decision 9).
 * - A meter read today is greyed with a tick and reads "Today 17:50 · 12,345.6 h" (BR1-05).
 * - Meter reset shows only on a counter row after the server refused it as "Lower than ..."
 *   (BR1-02): the parent sets state.showReset.
 * - A saved row is read-only; Undo shows only where the parent says the user may remove readings.
 * - `locked`: the whole round is saved, so every row is read-only, empty ones too (S040 A1).
 *
 * The state (value, is_reset, phase, message, error, showReset) is the parent's object. The row
 * writes the user's input into it (value through v-model and pick(), is_reset through its tick)
 * and reads the rest; Undo is emitted, because the parent talks to the server.
 */
import { computed } from "vue";
import { formatDateTime } from "../../utils/datetime";
import { formatReading, isToday, LIMIT_STATE_LABELS, RESET_LABEL } from "../../utils/meterLabels";

const props = defineProps({
  meter: { type: Object, required: true },
  state: { type: Object, required: true },
  canUndo: { type: Boolean, default: false },
  // A save is running: Undo waits, the inputs of rows not yet posted stay editable (BR1-10)
  busy: { type: Boolean, default: false },
  now: { type: Date, required: true },
  locked: { type: Boolean, default: false },
  idPrefix: { type: String, required: true },
});
const emit = defineEmits(["undo"]);

const meterType = computed(() => props.meter.meter_type);
const kind = computed(() => meterType.value.kind);
const saved = computed(() => props.state.phase === "saved");
const readOnly = computed(() => saved.value || props.locked);
const lastToday = computed(() => !!props.meter.last && isToday(props.meter.last.taken_at, props.now));
const inputId = computed(() => `${props.idPrefix}-value`);

const lastText = computed(() => {
  const last = props.meter.last;
  if (!last) return "";
  const reading = formatReading(last.value, meterType.value);
  return lastToday.value ? `Today ${last.taken_at.slice(11, 16)} · ${reading}` : `${reading} · ${formatDateTime(last.taken_at)}`;
});

function pick(answer) {
  props.state.value = props.state.value === answer ? "" : answer;
}
</script>

<template>
  <li class="sheet-meter list-group-item" :class="{ 'read-today': lastToday && !saved }" data-testid="sheet-meter">
    <!-- Three columns from md up (meter, last reading, input), fixed widths so they line up from
         meter to meter and card to card; stacked in the same order on a phone -->
    <div class="row gx-3 gy-1 align-items-center">
      <div class="col-12 col-md-4">
        <div class="d-flex flex-wrap align-items-baseline gap-2">
          <label class="fw-semibold" :for="kind === 'yes_no' ? undefined : inputId">{{ meterType.name }}</label>
          <span v-if="kind === 'amount'" class="text-secondary small">Amount per period</span>
        </div>
        <div v-if="kind === 'amount'" class="form-text mt-0">The amount for the period just ended, such as this shift.</div>
      </div>

      <div class="col-12 col-md-4 small text-secondary" data-testid="sheet-last">
        <template v-if="meter.last">
          <i v-if="lastToday" class="fa-solid fa-circle-check text-success me-1" aria-hidden="true"></i>
          {{ lastText }}
          <span v-if="meter.last.limit_state" class="badge text-bg-warning ms-1">{{ LIMIT_STATE_LABELS[meter.last.limit_state] }}</span>
        </template>
        <template v-else>No readings yet</template>
      </div>

      <div class="col-12 col-md-4">
        <div v-if="kind === 'yes_no'" class="d-flex gap-2" role="group" :aria-label="meterType.name">
          <button
            v-for="answer in ['yes', 'no']"
            :key="answer"
            type="button"
            class="btn btn-lg flex-fill answer-button"
            :class="state.value === answer ? 'btn-primary' : 'btn-outline-primary'"
            :aria-pressed="state.value === answer"
            :disabled="readOnly"
            @click="pick(answer)"
          >
            {{ answer === "yes" ? "Yes" : "No" }}
          </button>
        </div>
        <div v-else class="input-group">
          <input
            :id="inputId"
            v-model="state.value"
            class="form-control"
            :class="{ 'is-invalid': state.error }"
            inputmode="decimal"
            autocomplete="off"
            :readonly="readOnly"
          />
          <span class="input-group-text">{{ meterType.unit }}</span>
        </div>
      </div>
    </div>

    <div v-if="state.showReset && !readOnly" class="form-check mt-2">
      <input :id="`${idPrefix}-reset`" v-model="state.is_reset" class="form-check-input" type="checkbox" />
      <label class="form-check-label" :for="`${idPrefix}-reset`">Meter reset</label>
      <div class="form-text mt-0">Tick this only when the meter was replaced or set back to zero</div>
    </div>

    <div v-if="saved" class="d-flex flex-wrap align-items-center gap-2 mt-1">
      <span class="small fw-semibold" :class="state.notOk ? 'text-warning-emphasis' : 'text-success'" role="status">{{ state.message }}</span>
      <span v-if="state.reading?.is_reset" class="badge text-bg-secondary">{{ RESET_LABEL }}</span>
      <button v-if="canUndo" type="button" class="btn btn-outline-secondary btn-sm ms-auto" :disabled="busy || state.undoing" @click="emit('undo')">
        Undo
      </button>
    </div>
    <div v-if="state.error" class="small text-danger mt-1" role="alert">{{ state.error }}</div>
  </li>
</template>

<style scoped>
/* A thumb on a phone (U3): at least 48 px high */
.answer-button {
  min-height: 48px;
}

/* Read today (BR1-05): greyed, still typeable */
.read-today {
  background-color: var(--bs-tertiary-bg);
}
</style>
