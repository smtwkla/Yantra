<script setup>
/**
 * One dialog for every move of a ticket (docs/steps/S018-work-tickets/1-brief.md § 1, § 3):
 * acknowledge, start, back in service, send back, close, not a fault. The parent opens it
 * with an entry of the detail's `moves` ({name, default_person?, recording_as?}).
 *
 * Every dialog is short: the time as "Now · Change" and the remark (EventFields), plus only
 * what the move needs:
 * - acknowledge / start: "Recording as <name>" (the person this move will assign) or
 *   "Nobody will be assigned" (BR4-04);
 * - back in service: who did the work, always asked, pre-filled from `default_person`; from
 *   raised or acknowledged also when work started (StartedAtFields: a date and an empty
 *   time, sent only when the time is filled, BR4-06);
 * - send back: "Machine down again?" as two choice buttons, then the required remark;
 * - close: symptom, cause and action; not a fault: cause (5.1 No cause found suggested) and
 *   the required remark.
 * Save is labelled for what it does; close and not a fault say the ticket becomes read-only.
 * The API decides every refusal; a refusal is shown beside the field it names.
 */
import { computed, ref, watch } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ensureFailureCauses, ensureMaintenanceActions, failureCauses, maintenanceActions } from "../../stores/masters";
import {
  moveConsequence, moveLabel, moveSaveLabel, restoreTimeLabel, SEND_BACK_HELP, sendBackChoices, sendBackQuestion,
  toLocalDateValue,
} from "../../utils/ticketLabels";
import EventFields from "./EventFields.vue";
import PersonPicker from "./PersonPicker.vue";
import StartedAtFields from "./StartedAtFields.vue";

const props = defineProps({
  ticket: { type: Object, required: true },
  people: { type: Array, default: () => [] },
  modes: { type: Array, default: () => [] },
  ownPersonId: { type: Number, default: null },
});
const emit = defineEmits(["saved", "reload"]);

// The cause a not-a-fault close suggests: "looked, nothing wrong" (§ 1)
const NO_CAUSE_FOUND = "5.1";
const CAUSE_GROUPS = [
  ["design", "Design"], ["fabrication", "Fabrication / installation"], ["operation", "Operation / maintenance"],
  ["management", "Management"], ["misc", "Miscellaneous"],
];
// The fields this dialog shows a refusal beside; any other goes to the top
const SHOWN_FIELDS = ["occurred_at", "remark", "person_id", "started_at", "machine_down", "failure_mode_id", "cause_id",
  "action_id"];

const move = ref({ name: "" });
const loadError = ref("");

const { modal, form, saving, dirty, error, fieldError, openCreate, send } = useFormModal({
  path: null,
  blank: (seed) => ({ occurred_at: null, remark: "", ...seed }),
  afterSave: (result) => emit("saved", result),
});

const name = computed(() => move.value.name);
const remarkRequired = computed(() => name.value === "send-back" || name.value === "not-a-fault");
const asksStart = computed(() => name.value === "restore" && ["raised", "acknowledged"].includes(props.ticket.state));
const activeCauses = computed(() => (failureCauses.value ?? []).filter((c) => c.active));
const activeActions = computed(() => (maintenanceActions.value ?? []).filter((a) => a.active));
const causeGroups = computed(() => CAUSE_GROUPS
  .map(([group, label]) => ({ label, causes: activeCauses.value.filter((c) => c.cause_group === group) }))
  .filter((g) => g.causes.length));
// A stale state (409, no field): the page behind is out of date, so ask the parent to reload it
watch(error, (value) => {
  if (value && !value.field && value.status === 409) emit("reload");
});
const opens = ref(0); // EventFields is keyed on it: every opening starts at "Now" (CR1-03)
const topError = computed(() => (error.value && !SHOWN_FIELDS.includes(error.value.field) ? error.value.message : ""));
const assigneeIds = computed(() => props.ticket.assignees.map((a) => a.id));

async function open(entry) {
  move.value = entry;
  opens.value += 1;
  loadError.value = "";
  const seed = { occurred_at: null, remark: "" };
  if (entry.name === "restore") {
    Object.assign(seed, { person_id: entry.default_person?.id ?? null, started_date: toLocalDateValue(new Date()),
      started_time: "" });
  } else if (entry.name === "send-back") {
    seed.machine_down = null;
  } else if (entry.name === "close" || entry.name === "not-a-fault") {
    seed.cause_id = "";
    if (entry.name === "close") Object.assign(seed, { action_id: "", failure_mode_id: props.ticket.failure_mode?.id ?? "" });
  }
  openCreate(seed);
  if (entry.name === "close" || entry.name === "not-a-fault") {
    try {
      await Promise.all([ensureFailureCauses(), ensureMaintenanceActions()]);
      if (entry.name === "not-a-fault" && form.value.cause_id === "") {
        form.value.cause_id = activeCauses.value.find((c) => c.code === NO_CAUSE_FOUND)?.id ?? "";
      }
    } catch (err) {
      loadError.value = `The cause and action lists could not be loaded: ${err.message}`;
    }
  }
}

/** The simple checks of what the dialog asks for; the API checks everything again. */
function missingField() {
  const f = form.value;
  if (remarkRequired.value && !f.remark.trim()) return ["remark", "Add a remark"];
  if (name.value === "restore" && !f.person_id) return ["person_id", "Who did the work? Pick a name"];
  if (name.value === "send-back" && f.machine_down === null) return ["machine_down", "Choose Yes or No"];
  if (name.value === "close" && !f.failure_mode_id) return ["failure_mode_id", "Choose the symptom"];
  if ((name.value === "close" || name.value === "not-a-fault") && !f.cause_id) return ["cause_id", "Choose the cause"];
  if (name.value === "close" && !f.action_id) return ["action_id", "Choose the action taken"];
  return null;
}

function save() {
  const missing = missingField();
  if (missing) {
    error.value = { field: missing[0], message: missing[1] };
    return;
  }
  const f = form.value;
  const body = {};
  if (f.occurred_at) body.occurred_at = f.occurred_at;
  if (f.remark.trim()) body.remark = f.remark.trim();
  if (name.value === "restore") {
    body.person_id = f.person_id;
    if (asksStart.value && f.started_time && f.started_date) body.started_at = `${f.started_date}T${f.started_time}`;
  } else if (name.value === "send-back") {
    body.machine_down = f.machine_down;
  } else if (name.value === "close") {
    Object.assign(body, { cause_id: Number(f.cause_id), action_id: Number(f.action_id),
      failure_mode_id: Number(f.failure_mode_id) });
  } else if (name.value === "not-a-fault") {
    body.cause_id = Number(f.cause_id);
  }
  return send(() => apiPost(`/api/tickets/${props.ticket.id}/moves/${name.value}`, body));
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    :title="moveLabel(name, ticket.intensity)"
    :saving="saving"
    :dirty="dirty"
    :error="topError || loadError"
    :save-label="moveSaveLabel(name, ticket.intensity)"
    @save="save"
  >
    <template v-if="name === 'acknowledge' || name === 'start'">
      <p v-if="move.recording_as" class="mb-3"><i class="fa-solid fa-user me-2 text-secondary"></i>Recording as <strong>{{ move.recording_as.name }}</strong></p>
      <p v-else class="mb-3 text-secondary">Nobody will be assigned.</p>
    </template>

    <template v-if="name === 'send-back'">
      <fieldset class="mb-3">
        <legend class="form-label fs-6 mb-2">{{ sendBackQuestion(ticket.intensity) }}</legend>
        <div class="d-grid gap-2">
          <button
            v-for="choice in sendBackChoices(ticket.intensity)"
            :key="String(choice.value)"
            type="button"
            class="btn btn-lg text-start"
            :class="form.machine_down === choice.value ? (choice.value ? 'btn-danger' : 'btn-success') : 'btn-outline-secondary'"
            :aria-pressed="form.machine_down === choice.value"
            @click="form.machine_down = choice.value"
          >
            {{ choice.label }}
          </button>
        </div>
        <div v-if="fieldError('machine_down')" class="invalid-feedback d-block">{{ fieldError("machine_down") }}</div>
      </fieldset>
    </template>

    <EventFields
      :key="opens"
      v-model:time="form.occurred_at"
      v-model:remark="form.remark"
      :time-label="name === 'restore' ? restoreTimeLabel(ticket.intensity) : 'When'"
      :remark-required="remarkRequired"
      :remark-label="name === 'not-a-fault' ? 'Why is it not a fault?' : 'Remark'"
      :remark-help="name === 'send-back' ? SEND_BACK_HELP : ''"
      :time-error="fieldError('occurred_at')"
      :remark-error="fieldError('remark')"
      :id-prefix="`move-${name}`"
    />

    <template v-if="name === 'restore'">
      <div class="mb-3">
        <label class="form-label" for="move-restore-person-filter">Who did the work?</label>
        <PersonPicker
          v-model="form.person_id"
          :people="people"
          :own-person-id="ownPersonId"
          :assignee-ids="assigneeIds"
          :invalid="Boolean(fieldError('person_id'))"
          id-prefix="move-restore-person"
        />
        <div v-if="fieldError('person_id')" class="invalid-feedback d-block">{{ fieldError("person_id") }}</div>
      </div>
      <StartedAtFields
        v-if="asksStart"
        :key="opens"
        v-model:date="form.started_date"
        v-model:time="form.started_time"
        :restored-at="form.occurred_at"
        :error="fieldError('started_at')"
        id-prefix="move-restore-started"
      />
    </template>

    <template v-if="name === 'close'">
      <div class="mb-3">
        <label class="form-label" for="move-close-mode">Symptom</label>
        <select id="move-close-mode" v-model="form.failure_mode_id" class="form-select" :class="{ 'is-invalid': fieldError('failure_mode_id') }">
          <option value="">—</option>
          <option v-for="m in modes" :key="m.id" :value="m.id">{{ m.label }}</option>
        </select>
        <div v-if="fieldError('failure_mode_id')" class="invalid-feedback d-block">{{ fieldError("failure_mode_id") }}</div>
      </div>
    </template>

    <template v-if="name === 'close' || name === 'not-a-fault'">
      <div class="mb-3">
        <label class="form-label" for="move-cause">{{ name === 'close' ? 'Cause' : 'Why was it raised?' }}</label>
        <select id="move-cause" v-model="form.cause_id" class="form-select" :class="{ 'is-invalid': fieldError('cause_id') }">
          <option value="">—</option>
          <optgroup v-for="g in causeGroups" :key="g.label" :label="g.label">
            <option v-for="c in g.causes" :key="c.id" :value="c.id">{{ c.code }} {{ c.label }}</option>
          </optgroup>
        </select>
        <div v-if="fieldError('cause_id')" class="invalid-feedback d-block">{{ fieldError("cause_id") }}</div>
      </div>
    </template>

    <template v-if="name === 'close'">
      <div class="mb-3">
        <label class="form-label" for="move-action">Action taken</label>
        <select id="move-action" v-model="form.action_id" class="form-select" :class="{ 'is-invalid': fieldError('action_id') }">
          <option value="">—</option>
          <option v-for="a in activeActions" :key="a.id" :value="a.id">{{ a.code }} {{ a.label }}</option>
        </select>
        <div v-if="fieldError('action_id')" class="invalid-feedback d-block">{{ fieldError("action_id") }}</div>
      </div>
    </template>

    <template #footer-left>
      <span v-if="moveConsequence(name, ticket.serial)" class="small fw-semibold">{{ moveConsequence(name, ticket.serial) }}</span>
    </template>
  </FormModal>
</template>
