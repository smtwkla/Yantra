<script setup>
/**
 * One dialog for every move of a ticket (docs/steps/S018-work-tickets/1-brief.md § 1, § 3):
 * acknowledge, start, back in service, send back, close, not a fault. The parent opens it
 * with an entry of the detail's `moves` ({name, default_person?, recording_as?}).
 *
 * Every dialog is short: the time with a Now tick and the remark (EventFields), plus only
 * what the move needs:
 * - acknowledge / start: "Recording as <name>" (the person this move will assign) or
 *   "Nobody will be assigned" (BR4-04);
 * - back in service: who did the work, always asked, pre-filled from `default_person`; from
 *   raised or acknowledged also when work started (StartedAtFields: a date and an empty
 *   time, sent only when the time is filled, BR4-06);
 * - send back: "Machine down again?" as two choice buttons, then the required remark;
 * - close: symptom, cause and action; not a fault: cause (5.1 No cause found suggested) and
 *   the required remark;
 * - S019 schedule / change plan (S034: Defer on a defect, Put on hold on a breakdown): the
 *   reason, then the date (ScheduleFields). Defer / Put on hold opens with the date empty;
 *   Change plan opens with the current plan and the remark open and required ("Why did the plan change?"). The reason Other opens the remark and makes it
 *   required ("What does it wait for?");
 * - S019 start / back in service from scheduled on a defect (`asks_machine_stopped`): "Is / Was
 *   the machine stopped for this work?" as two choice buttons; on back in service only once a
 *   start time is filled, since the server asks for it only then (BR1-10).
 * - S020 close: "No parts recorded …" under the action when it is one of the close entry's
 *   `parts_hint_actions` (Replace, Modify, Overhaul) and the ticket has no part lines — a hint,
 *   not a refusal (§ 1.6). Not a fault with parts is refused by the API (409, no field), shown
 *   at the top, and the page behind reloads, as for the other stale-page refusals.
 * Save is labelled for what it does; close and not a fault say the ticket becomes read-only.
 * The API decides every refusal; a refusal is shown beside the field it names.
 */
import { computed, ref, watch } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ensureFailureCauses, ensureMaintenanceActions, failureCauses, maintenanceActions } from "../../stores/masters";
import {
  MACHINE_STOPPED_CHOICES, machineStoppedQuestion, moveConsequence, moveLabel, moveSaveLabel, OTHER_REASON, PLAN_MOVES,
  restoreTimeLabel, SEND_BACK_HELP, sendBackChoices, sendBackQuestion, toLocalDateValue,
} from "../../utils/ticketLabels";
import EventFields from "./EventFields.vue";
import PersonPicker from "./PersonPicker.vue";
import ScheduleFields from "./ScheduleFields.vue";
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
  "action_id", "planned_date", "waiting_reason", "machine_stopped"];

const move = ref({ name: "" });
const loadError = ref("");

const { modal, form, saving, dirty, error, fieldError, openCreate, send } = useFormModal({
  path: null,
  blank: (seed) => ({ occurred_at: null, remark: "", ...seed }),
  afterSave: (result) => emit("saved", result),
});

const name = computed(() => move.value.name);
const isPlan = computed(() => PLAN_MOVES.includes(name.value));
const remarkRequired = computed(() => ["send-back", "not-a-fault", "reschedule"].includes(name.value)
  || (isPlan.value && form.value.waiting_reason === OTHER_REASON));
const remarkLabel = computed(() => {
  if (name.value === "not-a-fault") return "Why is it not a fault?";
  if (name.value === "reschedule") return "Why did the plan change?";
  if (isPlan.value && form.value.waiting_reason === OTHER_REASON) return "What does it wait for?";
  return "Remark";
});
const asksStart = computed(() => name.value === "restore"
  && ["raised", "acknowledged", "scheduled"].includes(props.ticket.state));
// Back in service asks only once a start time is filled: the server requires the answer only then
const asksStopped = computed(() => Boolean(move.value.asks_machine_stopped)
  && (name.value === "start" || (name.value === "restore" && Boolean(form.value.started_time))));
const activeCauses = computed(() => (failureCauses.value ?? []).filter((c) => c.active));
const activeActions = computed(() => (maintenanceActions.value ?? []).filter((a) => a.active));
// S020 § 1.6: the action usually fits a part, and none is recorded
const showPartsHint = computed(() => name.value === "close" && props.ticket.parts.length === 0
  && (move.value.parts_hint_actions ?? []).includes(Number(form.value.action_id)));
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
  if (entry.asks_machine_stopped) seed.machine_stopped = null;
  if (entry.name === "restore") {
    Object.assign(seed, { person_id: entry.default_person?.id ?? null, started_date: toLocalDateValue(new Date()),
      started_time: "" });
  } else if (entry.name === "schedule") {
    Object.assign(seed, { planned_date: "", waiting_reason: "" });
  } else if (entry.name === "reschedule") {
    // Prefilled with the current plan: change one thing and save (BR1-10)
    Object.assign(seed, { planned_date: props.ticket.planned_date ?? "", waiting_reason: props.ticket.waiting_reason ?? "" });
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
  if (isPlan.value && !f.waiting_reason) return ["waiting_reason", "Choose why it waits"];
  if (isPlan.value && !f.planned_date) return ["planned_date", "Choose a date"];
  if (remarkRequired.value && !f.remark.trim()) return ["remark", "Add a remark"];
  if (name.value === "restore" && !f.person_id) return ["person_id", "Who did the work? Pick a name"];
  if (asksStopped.value && f.machine_stopped === null) return ["machine_stopped", "Choose Yes or No"];
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
  if (asksStopped.value) body.machine_stopped = f.machine_stopped;
  if (isPlan.value) {
    Object.assign(body, { planned_date: f.planned_date, waiting_reason: f.waiting_reason });
  } else if (name.value === "restore") {
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

    <ScheduleFields
      v-if="isPlan"
      v-model:date="form.planned_date"
      v-model:reason="form.waiting_reason"
      :date-error="fieldError('planned_date')"
      :reason-error="fieldError('waiting_reason')"
      :id-prefix="`move-${name}`"
    />

    <EventFields
      :key="opens"
      v-model:time="form.occurred_at"
      v-model:remark="form.remark"
      :time-label="name === 'restore' ? restoreTimeLabel(ticket.intensity) : 'When'"
      :remark-required="remarkRequired"
      :remark-label="remarkLabel"
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

    <fieldset v-if="asksStopped" class="mb-3">
      <legend class="form-label fs-6 mb-2">{{ machineStoppedQuestion(name) }}</legend>
      <div class="d-grid gap-2">
        <button
          v-for="choice in MACHINE_STOPPED_CHOICES"
          :key="String(choice.value)"
          type="button"
          class="btn text-start"
          :class="form.machine_stopped === choice.value ? 'btn-primary' : 'btn-outline-secondary'"
          :aria-pressed="form.machine_stopped === choice.value"
          @click="form.machine_stopped = choice.value"
        >
          {{ choice.label }}
        </button>
      </div>
      <div v-if="fieldError('machine_stopped')" class="invalid-feedback d-block">{{ fieldError("machine_stopped") }}</div>
    </fieldset>

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
      <div v-if="showPartsHint" class="alert alert-warning py-2 mb-3 parts-hint">
        No parts recorded. If any were fitted, cancel and add them on the ticket first.
      </div>
    </template>

    <template #footer-left>
      <span v-if="moveConsequence(name, ticket.serial)" class="small fw-semibold">{{ moveConsequence(name, ticket.serial) }}</span>
    </template>
  </FormModal>
</template>
