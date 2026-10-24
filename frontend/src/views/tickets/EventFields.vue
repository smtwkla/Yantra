<script setup>
/**
 * The two fields every move and re-grade dialog has (docs/steps/S018-work-tickets/1-brief.md
 * § 1, BR3-09, BR4-01):
 * - the event time as "Now · Change": `time` stays null — the server's clock — until the user
 *   edits the input that *Change* opens, filled with the phone's now (§ 5.1: a phone a few
 *   minutes off never gets a refusal for a time nobody typed);
 * - the remark, behind *Add remark* where it is optional, open where the move requires it;
 *   left out with `withRemark: false` (the raise screen's *Already fixed*, S018 A1, BS2-03).
 */
import { ref, watch } from "vue";
import { daysAgoHint, toLocalInputValue } from "../../utils/ticketLabels";

const REMARK_MAX = 1000;

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

const changing = ref(false);
const draft = ref("");
const remarkShown = ref(false);

// A dialog opened again starts at "Now" with the remark folded
watch(() => props.time, (value) => {
  if (value === null) changing.value = false;
});
watch(() => props.remark, (value) => {
  if (!value) remarkShown.value = false;
});

function change() {
  draft.value = toLocalInputValue(new Date());
  changing.value = true;
}

function backToNow() {
  changing.value = false;
  emit("update:time", null);
}

function onInput(event) {
  draft.value = event.target.value;
  // A cleared input means "now", like an untouched one
  emit("update:time", draft.value || null);
}
</script>

<template>
  <div class="mb-3">
    <label class="form-label" :for="`${idPrefix}-time`">{{ timeLabel }}</label>
    <div v-if="!changing" class="d-flex align-items-center gap-2">
      <span class="fw-semibold">Now</span>
      <button v-if="!locked" type="button" class="btn btn-link p-0" @click="change">Change</button>
    </div>
    <div v-else class="d-flex align-items-center gap-2">
      <input
        :id="`${idPrefix}-time`"
        :value="draft"
        class="form-control"
        :class="{ 'is-invalid': timeError }"
        type="datetime-local"
        :readonly="locked"
        @input="onInput"
      />
      <button v-if="!locked" type="button" class="btn btn-link p-0" @click="backToNow">Now</button>
    </div>
    <div v-if="timeError" class="invalid-feedback d-block">{{ timeError }}</div>
    <div v-if="changing && daysAgoHint(draft, new Date())" class="form-text">{{ daysAgoHint(draft, new Date()) }}</div>
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
