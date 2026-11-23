<script setup>
/**
 * Add task / Change task (docs/steps/S107-ticket-task-screens/1-brief.md § 5.3): one dialog on one
 * useFormModal. *What to do*, the *Owner* from the ticket's people picker (any active member of the
 * site may own a task, S106 D3; with or without a login) and the *Due date* with three quick picks
 * (Today, Tomorrow, In 7 days; no default, D5).
 *
 * The dialog checks nothing itself: every rule is the server's, and its refusals come in field
 * order ("Enter what to do", "Choose the owner", "Choose the due date", …, D13). It saves through
 * `send` with its own URLs, as ActionDialog does, since useFormModal's own save builds
 * `${path}/${id}` from one fixed path. A 409 with no field (30 tasks, the ticket closed, the task no
 * longer open) shows at the top and emits `reload`: the page behind is stale.
 */
import { computed, ref, watch } from "vue";
import { apiPost, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { dateInDays, PLANNED_DATE_MAX_DAYS, TASK_DUE_PICKS, TASK_TEXT_MAX } from "../../utils/ticketLabels";
import PersonPicker from "./PersonPicker.vue";

const props = defineProps({
  ticket: { type: Object, required: true },
  people: { type: Array, default: () => [] },
  ownPersonId: { type: Number, default: null },
});
const emit = defineEmits(["saved", "reload"]);

// On Change: the owner the task has now, kept until another is picked; shown when not in `people`
const openedOwner = ref(null);

// useFormModal calls blank() with no argument at set-up (self-check 13)
const { modal, form, editingId, saving, dirty, error, fieldError, modalError, openCreate, openEdit, send } = useFormModal({
  path: null,
  blank: () => ({ text: "", owner_id: null, due_date: "" }),
  fromRecord: (task) => ({ text: task.text, owner_id: task.owner.id, due_date: task.due_date }),
  afterSave: (result) => emit("saved", result),
});

const isEdit = computed(() => editingId.value !== null);
const assigneeIds = computed(() => props.ticket.assignees.map((a) => a.id));
// The floor the server checks (S106 § 5.3): the day the problem happened; the top a year ahead
const minDate = computed(() => (props.ticket.occurred_at ?? "").slice(0, 10));
const maxDate = computed(() => dateInDays(PLANNED_DATE_MAX_DAYS));
const ownerNotListed = computed(() => isEdit.value && openedOwner.value
  && form.value.owner_id === openedOwner.value.id
  && !props.people.some((p) => p.id === openedOwner.value.id));

// A stale page (409, no field): ask the parent to reload what is behind the dialog
watch(error, (value) => {
  if (value && !value.field && value.status === 409) emit("reload");
});

function openAdd() {
  openedOwner.value = null;
  openCreate();
}

function openChange(task) {
  openedOwner.value = { id: task.owner.id, name: task.owner.name };
  openEdit(task);
}

function pickDue(days) {
  form.value.due_date = dateInDays(days);
}

function save() {
  const f = form.value;
  const base = `/api/tickets/${props.ticket.id}/tasks`;
  // All three on a change too: the server writes only what differs (S106 § 5.2)
  const body = { text: f.text, owner_id: f.owner_id, due_date: f.due_date };
  if (isEdit.value) return send(() => apiPut(`${base}/${editingId.value}`, body));
  return send(() => apiPost(base, body));
}

defineExpose({ openAdd, openChange });
</script>

<template>
  <FormModal
    ref="modal"
    :title="isEdit ? 'Change task' : 'Add task'"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :save-label="isEdit ? 'Save task' : 'Add task'"
    @save="save"
  >
    <div class="mb-3">
      <label class="form-label" for="task-text">What to do</label>
      <textarea
        id="task-text"
        v-model="form.text"
        class="form-control"
        :class="{ 'is-invalid': fieldError('text') }"
        rows="2"
        :maxlength="TASK_TEXT_MAX"
        placeholder="Check the space heater fuse in the panel."
        autofocus
      ></textarea>
      <div v-if="fieldError('text')" class="invalid-feedback d-block">{{ fieldError("text") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="task-owner-filter">Owner</label>
      <p v-if="ownerNotListed" class="small text-secondary mb-2" data-testid="owner-now">
        Owner now: {{ openedOwner.name }} (not at this site now). Choose another person, or keep them.
      </p>
      <PersonPicker
        v-model="form.owner_id"
        :people="people"
        :own-person-id="ownPersonId"
        :assignee-ids="assigneeIds"
        :invalid="Boolean(fieldError('owner_id'))"
        id-prefix="task-owner"
      />
      <div v-if="fieldError('owner_id')" class="invalid-feedback d-block">{{ fieldError("owner_id") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="task-due">Due date</label>
      <input
        id="task-due"
        v-model="form.due_date"
        class="form-control"
        :class="{ 'is-invalid': fieldError('due_date') }"
        type="date"
        :min="minDate || undefined"
        :max="maxDate"
      />
      <div class="d-flex flex-wrap gap-2 mt-2">
        <button
          v-for="[days, label] in TASK_DUE_PICKS"
          :key="days"
          type="button"
          class="btn btn-outline-secondary"
          @click="pickDue(days)"
        >{{ label }}</button>
      </div>
      <div v-if="fieldError('due_date')" class="invalid-feedback d-block">{{ fieldError("due_date") }}</div>
      <div class="form-text">By when it should be done</div>
    </div>
  </FormModal>
</template>
