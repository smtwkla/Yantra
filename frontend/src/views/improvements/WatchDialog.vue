<script setup>
/**
 * The dialog *Watch* (docs/steps/S073-verified-close-screens/1-brief.md § 5.4): the watch's length,
 * 30 to 365 days, through S067's PUT. The end date shown is computed from the watch's start
 * the server gives (`watch.from`); the screen has no start of its own.
 */
import { computed } from "vue";
import { apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { formatDate } from "../../utils/datetime";
import { WATCH_DAYS_MAX, WATCH_DAYS_MIN, watchEndDate } from "../../utils/improvementLabels";

const DEFAULT_WATCH_DAYS = 90;

const props = defineProps({
  improvement: { type: Object, required: true },
});
const emit = defineEmits(["saved"]);

const { modal, form, saving, dirty, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: (seed = {}) => ({ watch_days: seed.improvement?.watch.days ?? DEFAULT_WATCH_DAYS }),
  afterSave: (result) => emit("saved", result),
});

// Only for a number in range: a half-typed value shows no date
const endsOn = computed(() => {
  const days = Number(form.value.watch_days);
  const inRange = Number.isInteger(days) && days >= WATCH_DAYS_MIN && days <= WATCH_DAYS_MAX;
  const date = inRange ? watchEndDate(props.improvement.watch.from, days) : "";
  return date ? formatDate(date) : "";
});

function open() {
  openCreate({ improvement: props.improvement });
}

function save() {
  return send(() => apiPut(`/api/improvements/${props.improvement.id}`, { watch_days: Number(form.value.watch_days) }));
}

defineExpose({ open });
</script>

<template>
  <FormModal ref="modal" title="Watch" :saving="saving" :dirty="dirty" :error="modalError" save-label="Save watch" @save="save">
    <div class="mb-3">
      <label class="form-label" for="watch-days">Watch for (days)</label>
      <input
        id="watch-days"
        v-model="form.watch_days"
        type="number"
        class="form-control"
        :class="{ 'is-invalid': fieldError('watch_days') }"
        :min="WATCH_DAYS_MIN"
        :max="WATCH_DAYS_MAX"
        inputmode="numeric"
        aria-describedby="watch-days-help"
      />
      <div v-if="fieldError('watch_days')" class="invalid-feedback d-block">{{ fieldError("watch_days") }}</div>
      <div id="watch-days-help" class="form-text">
        How long Yantra watches for the failure after the last fix on the machine is done. A lesson or a spread does not
        move the start. {{ WATCH_DAYS_MIN }} to {{ WATCH_DAYS_MAX }} days; dust builds up over months, so 90 is the default.
      </div>
      <div v-if="endsOn" class="mt-2" data-testid="watch-ends">Ends on {{ endsOn }}</div>
    </div>
  </FormModal>
</template>
