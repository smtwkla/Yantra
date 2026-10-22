<script setup>
/**
 * Re-grade a ticket's intensity (docs/steps/S018-work-tickets/1-brief.md § 1 Re-grade):
 * - open("stopped"): the operator's *Machine stopped* on a defect — no choice of grades,
 *   "Breakdown from: Now · Change", the optional remark, Save *Machine stopped* (BR4-07);
 * - open("change"): *Change severity* for ticket:work holders — the raise screen's large
 *   intensity buttons, only the grades the detail's `regrade_to` allows; the remark open and
 *   required when the chosen grade is lower (lowering ends downtime, BR4-01).
 * The API decides every refusal.  One it cannot show beside a field — in "stopped" mode the
 * intensity field is not shown, e.g. "Already a breakdown" when another operator was first —
 * shows at the top, and the page reloads the ticket (S025 § 1.7).
 */
import { computed, ref, watch } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { BREAKDOWN_INTENSITY, INTENSITY_CHOICES, isLowering } from "../../utils/ticketLabels";
import EventFields from "./EventFields.vue";

const props = defineProps({
  ticket: { type: Object, required: true },
});
const emit = defineEmits(["saved", "reload"]);

const PICKED_CLASS = { critical: "btn-danger", degraded: "btn-warning", initial: "btn-secondary" };
const SHOWN_FIELDS = ["intensity", "occurred_at", "remark"];
const STOPPED_SHOWN_FIELDS = ["occurred_at", "remark"];

const stopped = ref(false);

const { modal, form, saving, dirty, error, fieldError, openCreate, send } = useFormModal({
  path: null,
  blank: (seed) => ({ intensity: "", occurred_at: null, remark: "", ...seed }),
  afterSave: (result) => emit("saved", result),
});

const choices = computed(() => INTENSITY_CHOICES.filter((c) => props.ticket.regrade_to.includes(c.value)));
const lowering = computed(() => Boolean(form.value.intensity) && isLowering(props.ticket.intensity, form.value.intensity));
const shownFields = computed(() => (stopped.value ? STOPPED_SHOWN_FIELDS : SHOWN_FIELDS));
const shownBesideField = (value) => shownFields.value.includes(value.field);
// A server refusal no field shows (a stale state, or someone else changed the severity first):
// the page behind is out of date, so ask the parent to reload it
watch(error, (value) => {
  if (value && [400, 409].includes(value.status) && !shownBesideField(value)) emit("reload");
});
const opens = ref(0); // EventFields is keyed on it: every opening starts at "Now" (CR1-03)
const topError = computed(() => (error.value && !shownBesideField(error.value) ? error.value.message : ""));

function open(mode) {
  stopped.value = mode === "stopped";
  opens.value += 1;
  openCreate({ intensity: stopped.value ? BREAKDOWN_INTENSITY : "", occurred_at: null, remark: "" });
}

function save() {
  const f = form.value;
  if (!f.intensity) {
    error.value = { field: "intensity", message: "Choose how bad it is" };
    return;
  }
  if (lowering.value && !f.remark.trim()) {
    error.value = { field: "remark", message: "Say why the machine runs" };
    return;
  }
  const body = { intensity: f.intensity };
  if (f.occurred_at) body.occurred_at = f.occurred_at;
  if (f.remark.trim()) body.remark = f.remark.trim();
  return send(() => apiPost(`/api/tickets/${props.ticket.id}/regrade`, body));
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    :title="stopped ? 'Machine stopped' : 'Change severity'"
    :saving="saving"
    :dirty="dirty"
    :error="topError"
    :save-label="stopped ? 'Machine stopped' : 'Save'"
    @save="save"
  >
    <fieldset v-if="!stopped" class="mb-3">
      <legend class="form-label fs-6 mb-2">How bad is it now?</legend>
      <div class="d-grid gap-2">
        <button
          v-for="c in choices"
          :key="c.value"
          type="button"
          class="btn btn-lg text-start"
          :class="form.intensity === c.value ? PICKED_CLASS[c.value] : 'btn-outline-secondary'"
          :aria-pressed="form.intensity === c.value"
          @click="form.intensity = c.value"
        >
          <span class="fw-semibold">{{ c.label }}</span>
          <span class="d-block small">{{ c.hint }}</span>
        </button>
      </div>
      <div v-if="fieldError('intensity')" class="invalid-feedback d-block">{{ fieldError("intensity") }}</div>
    </fieldset>

    <EventFields
      :key="opens"
      v-model:time="form.occurred_at"
      v-model:remark="form.remark"
      :time-label="stopped || form.intensity === 'critical' ? 'Breakdown from' : 'When'"
      :remark-required="lowering"
      :remark-label="lowering ? 'Why does the machine run?' : 'Remark'"
      :time-error="fieldError('occurred_at')"
      :remark-error="fieldError('remark')"
      id-prefix="regrade"
    />
  </FormModal>
</template>
