<script setup>
/**
 * *Verify job* and *Send back job* (docs/steps/S099-pm-verify/1-brief.md § 5.8, D6): the facts, the consequence and
 * a remark, so a mis-tap on a phone never closes a job. One component, `mode` "verify" or "send_back"; the page
 * mounts it once per mode. Call contract (settings: Self-check (13)): `blank()` takes no seed and `openCreate()` is
 * called without one; the save sends `{remark}` through `send`. `afterSave` keeps the answer, and FormModal's
 * `closed` event hands it to the page after the fade (the S077 rule), as `saved(job)`. A refusal on `remark` shows
 * beside the field; a 409 (another engineer acted first) shows above it, and the page reloads the job on close
 * (`stale`).
 */
import { computed } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { userPersonId } from "../../stores/auth";
import { formatDateTime } from "../../utils/datetime";
import { findingsText } from "../../utils/pmLabels";

const REMARK_MAX = 500; // pm_work_core.REMARK_MAX

const props = defineProps({
  job: { type: Object, required: true },
  mode: { type: String, required: true, validator: (value) => ["verify", "send_back"].includes(value) },
});
const emit = defineEmits(["saved", "stale"]);

const sendBack = computed(() => props.mode === "send_back");
const path = () => `/api/pm/jobs/${props.job.id}/${sendBack.value ? "send-back" : "verify"}`;
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

const performer = computed(() => props.job.performed_by?.name ?? "");
const facts = computed(() => {
  const job = props.job;
  const by = performer.value ? ` by ${performer.value}` : "";
  return `${job.serial} · done ${formatDateTime(job.done_at)}${by} · ${findingsText(job.findings)}`;
});
const consequence = computed(() => (sendBack.value
  ? `The job goes back to In progress. ${performer.value} fixes it and marks it done again. The answers he changes`
    + " replace the ones shown here; your remark stays on the history."
  : "The job is then closed. It cannot be changed or sent back."));
const extraLine = computed(() => {
  const job = props.job;
  if (!sendBack.value) {
    return userPersonId.value && job.performed_by?.id === userPersonId.value
      ? "You did this job. The record will say you verified your own work." : "";
  }
  return job.open_job?.state === "due"
    ? `The plan's open job ${job.open_job.serial} is not started. It is cancelled, and made again from the latest`
      + " done time."
    : "";
});
const title = computed(() => (sendBack.value ? "Send back job" : "Verify job"));

function save() {
  return send(() => apiPost(path(), toBody(form.value)));
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
    :title="title"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :save-label="title"
    @save="save"
    @closed="onClosed"
  >
    <p class="small text-secondary">{{ facts }}</p>
    <p>{{ consequence }}</p>
    <p v-if="extraLine" class="fw-semibold">{{ extraLine }}</p>
    <div class="mb-1">
      <label class="form-label" :for="`pm-${mode}-remark`">
        {{ sendBack ? "What must be done again?" : "Remark (optional)" }}
      </label>
      <textarea
        :id="`pm-${mode}-remark`"
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
