<script setup>
/**
 * *Mark job done* (docs/steps/S098-pm-job-phone/1-brief.md § 5.10): one field, *Done* (the S051 time field with
 * its *Now* tick; up to 7 days back, not before *Started*: the server judges), the line "Started … · n of n
 * filled" and the consequence. Call contract (settings: Self-check (13)): `blank()` takes no seed and
 * `openCreate()` is called without one; the save sends `{done_at}` through `send`. `afterSave` keeps the answer,
 * and FormModal's `closed` event hands it to the page after the fade (the S077 rule), as `done(job)`. A refusal
 * on `done_at` shows beside the field; `not_all_filled` (another person's change) has no field and shows above it.
 */
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { formatDateTime } from "../../utils/datetime";
import { filledText } from "../../utils/pmLabels";
import EventFields from "../tickets/EventFields.vue";

const props = defineProps({
  job: { type: Object, required: true },
});
const emit = defineEmits(["done"]);

const path = () => `/api/pm/jobs/${props.job.id}/done`;
const toBody = (form) => ({ done_at: form.done_at });
let saved = null; // the job the save answered, handed over once the dialog is hidden

const { modal, form, saving, dirty, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: () => ({ done_at: null }),
  toBody,
  afterSave: (job) => {
    saved = job;
  },
  label: () => props.job.serial,
});

function save() {
  return send(() => apiPost(path(), toBody(form.value)));
}

function onClosed() {
  if (saved) emit("done", saved);
  saved = null;
}

defineExpose({ open: () => openCreate() });
</script>

<template>
  <FormModal
    ref="modal"
    title="Mark job done"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    save-label="Mark job done"
    @save="save"
    @closed="onClosed"
  >
    <p class="small text-secondary">
      Started {{ formatDateTime(job.started_at) }} · {{ filledText(job.filled_count, job.item_count) }}
    </p>
    <EventFields
      v-model:time="form.done_at"
      :with-remark="false"
      time-label="Done"
      id-prefix="pm-done"
      :time-error="fieldError('done_at')"
    />
    <!-- S099 BS1-08: a job of a plan that needs verification can still be sent back by an engineer -->
    <p class="fw-semibold mb-0">
      {{ job.plan.needs_verification
        ? "You cannot change the job after this, unless an engineer sends it back."
        : "The job can no longer be changed." }}
    </p>
  </FormModal>
</template>
