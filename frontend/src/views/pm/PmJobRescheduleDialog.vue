<script setup>
/**
 * *Reschedule job* (docs/steps/S101-pm-reschedule-skip/1-brief.md § 5.7; R03.9): a new due date and/or a new due
 * meter value, and a required reason. The bounds (today to a year ahead, the meter above its latest reading and at
 * most one interval past it) are the server's (pm_work_core.reschedule_override); each refusal shows beside its
 * field. Call contract (settings: Self-check (13)): `blank()` takes no seed and reads the job at each open;
 * `openCreate()` is called without one; the save sends `{due_on, due_meter, remark}` through `send` (an empty date
 * or value as null). `afterSave` keeps the answer, and FormModal's `closed` event hands it to the page after the
 * fade (the S077 rule), as `saved(job)`; a 409 (the job changed meanwhile) makes the page reload on close (`stale`).
 */
import { computed } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { formatReading } from "../../utils/meterLabels";
import { daysPastText, dueText } from "../../utils/pmLabels";

const REMARK_MAX = 500; // pm_work_core.REMARK_MAX

const props = defineProps({
  job: { type: Object, required: true },
});
const emit = defineEmits(["saved", "stale"]);

const textOrNull = (value) => String(value ?? "").trim() || null;
const toBody = (form) => ({ due_on: form.due_on || null, due_meter: textOrNull(form.due_meter), remark: form.remark });
let saved = null; // the job the save answered, handed over once the dialog is hidden

const { modal, form, saving, dirty, error, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: () => ({ due_on: props.job.due_on ?? "", due_meter: props.job.due_meter ?? "", remark: "" }),
  toBody,
  afterSave: (job) => {
    saved = job;
  },
  label: () => props.job.serial,
});

const meterType = computed(() => props.job.meter?.meter_type ?? null);
const facts = computed(() => {
  const job = props.job;
  const point = dueText(job.due_on, job.due_meter, meterType.value);
  return `${job.serial}${point ? ` · due ${point}` : ""}${daysPastText(job.days_past)}`;
});
const meterNow = computed(() => {
  const counted = props.job.meter?.value_counted;
  return counted != null ? `Now ${formatReading(counted, meterType.value)}.` : "";
});

function save() {
  return send(() => apiPost(`/api/pm/jobs/${props.job.id}/reschedule`, toBody(form.value)));
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
    title="Reschedule job"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    save-label="Reschedule job"
    @save="save"
    @closed="onClosed"
  >
    <p class="small text-secondary">{{ facts }}</p>
    <div v-if="job.due_on" class="mb-3">
      <label class="form-label" for="pm-move-date">New due date</label>
      <input
        id="pm-move-date"
        v-model="form.due_on"
        type="date"
        class="form-control"
        :class="{ 'is-invalid': fieldError('due_on') }"
      />
      <div v-if="fieldError('due_on')" class="invalid-feedback d-block">{{ fieldError("due_on") }}</div>
    </div>
    <div v-if="job.meter" class="mb-3">
      <label class="form-label" for="pm-move-meter">
        New due value<template v-if="meterType.unit"> ({{ meterType.unit }})</template>
      </label>
      <input
        id="pm-move-meter"
        v-model="form.due_meter"
        class="form-control"
        :class="{ 'is-invalid': fieldError('due_meter') }"
        inputmode="decimal"
      />
      <div v-if="fieldError('due_meter')" class="invalid-feedback d-block">{{ fieldError("due_meter") }}</div>
      <div v-else-if="meterNow" class="form-text">{{ meterNow }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="pm-move-remark">Why is the job moved?</label>
      <textarea
        id="pm-move-remark"
        v-model="form.remark"
        class="form-control"
        :class="{ 'is-invalid': fieldError('remark') }"
        rows="3"
        :maxlength="REMARK_MAX"
      ></textarea>
      <div v-if="fieldError('remark')" class="invalid-feedback d-block">{{ fieldError("remark") }}</div>
    </div>
    <p class="mb-1">
      The job is on time if it is done by the new due date or meter value. The move is counted in the PM report.
    </p>
  </FormModal>
</template>
