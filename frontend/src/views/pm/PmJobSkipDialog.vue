<script setup>
/**
 * *Skip job* (docs/steps/S101-pm-reschedule-skip/1-brief.md § 5.7; R03.9): the facts, the consequence and a
 * required reason, so a mis-tap on a phone never closes a job. Call contract (settings: Self-check (13)): `blank()`
 * takes no seed; `openCreate()` is called without one; the save sends `{remark}` through `send`. `afterSave` keeps
 * the answer, and FormModal's `closed` event hands it to the page after the fade (the S077 rule), as `saved(job)`;
 * a 409 (the job changed meanwhile) makes the page reload on close (`stale`).
 */
import { computed } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { daysPastText, dueText } from "../../utils/pmLabels";

const REMARK_MAX = 500; // pm_work_core.REMARK_MAX

const props = defineProps({
  job: { type: Object, required: true },
});
const emit = defineEmits(["saved", "stale"]);

const toBody = (form) => ({ remark: form.remark });
let saved = null; // the job the save answered, handed over once the dialog is hidden

const { modal, form, saving, dirty, error, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: () => ({ remark: "" }),
  toBody,
  afterSave: (job) => {
    saved = job;
  },
  label: () => props.job.serial,
});

const facts = computed(() => {
  const job = props.job;
  const point = dueText(job.due_on, job.due_meter, job.meter?.meter_type);
  return `${job.serial}${point ? ` · due ${point}` : ""}${daysPastText(job.days_past)}`;
});

function save() {
  return send(() => apiPost(`/api/pm/jobs/${props.job.id}/skip`, toBody(form.value)));
}

function onClosed() {
  if (saved) emit("saved", saved);
  else if (error.value?.status === 409) emit("stale");
  saved = null;
}

defineExpose({ open: () => openCreate() });
</script>

<template>
  <FormModal
    ref="modal"
    title="Skip job"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    save-label="Skip job"
    @save="save"
    @closed="onClosed"
  >
    <p class="small text-secondary">{{ facts }}</p>
    <p data-testid="pm-skip-consequence">
      The job is closed as skipped and counts as not done. The next job counts from today. You cannot undo this.
    </p>
    <div class="mb-1">
      <label class="form-label" for="pm-skip-remark">Why is the job skipped?</label>
      <textarea
        id="pm-skip-remark"
        v-model="form.remark"
        class="form-control"
        :class="{ 'is-invalid': fieldError('remark') }"
        rows="3"
        :maxlength="REMARK_MAX"
      ></textarea>
      <div v-if="fieldError('remark')" class="invalid-feedback d-block">{{ fieldError("remark") }}</div>
    </div>
  </FormModal>
</template>
