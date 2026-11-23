<script setup>
/**
 * The ticket page's *Tasks* card (docs/steps/S107-ticket-task-screens/1-brief.md § 5.1): the
 * ticket's "who does what by when" (TPM's abnormality tag: who acts and by when, visible at a
 * glance). "Tasks (1 of 3 done)", one TaskItem per task in the order added, "Add task" for the
 * holders of ticket:assign while the ticket is open (`can_add_task`). Shown when the ticket has a
 * task or the user may add one.
 *
 * The card makes the cancel call and holds which row asks (`cancellingId`; one row at a time, as
 * S071 § 5.2); the add / change and *Mark done* dialogs live in it. It emits `saved(detail)` with
 * each answer (the page replaces its copy) and `reload` when the page behind is stale (a 409 with
 * no field) or a photo went up (the page reloads the detail and its photos card).
 *
 * A stale cancel ask closes itself: when the asking task is gone or can no longer be changed in a
 * new copy of the ticket (a reload after a 409, a save from another control), the ask closes (the
 * work of S071 CR2-01's closeStaleCancel, which the card cannot call: the page reloads, not the card).
 */
import { computed, ref, watch } from "vue";
import { apiPost } from "../../api";
import TaskItem from "../../components/TaskItem.vue";
import { actionCountsText } from "../../utils/improvementLabels";
import { taskDoneTarget } from "../../utils/ticketLabels";
import MarkDoneDialog from "../improvements/MarkDoneDialog.vue";
import TaskDialog from "./TaskDialog.vue";

const props = defineProps({
  ticket: { type: Object, required: true },
  people: { type: Array, default: () => [] },
  ownPersonId: { type: Number, default: null },
});
const emit = defineEmits(["saved", "reload"]);

const taskDialog = ref(null);
const markDoneDialog = ref(null);
const cancellingId = ref(null);
const cancelBusy = ref(false);
const cancelError = ref(null); // {field, message} of the last refused cancel

const tasks = computed(() => props.ticket.tasks ?? []);
const shown = computed(() => tasks.value.length > 0 || props.ticket.can_add_task);
// task_counts has the shape of an improvement's action_counts: cancelled ones in neither number
const countsText = computed(() => (props.ticket.task_counts ? actionCountsText(props.ticket.task_counts) : ""));

watch(() => props.ticket, (ticket) => {
  if (cancellingId.value === null) return;
  const asking = (ticket.tasks ?? []).find((t) => t.id === cancellingId.value);
  if (!asking?.can_change) {
    cancellingId.value = null;
    cancelError.value = null;
  }
});

function askCancel(task) {
  cancellingId.value = task.id;
  cancelError.value = null;
}

function keep() {
  cancellingId.value = null;
  cancelError.value = null;
}

async function cancelTask(task, reason) {
  cancelBusy.value = true;
  cancelError.value = null;
  try {
    const detail = await apiPost(`/api/tickets/${props.ticket.id}/tasks/${task.id}/cancel`, { reason });
    cancellingId.value = null;
    emit("saved", detail);
  } catch (err) {
    cancelError.value = { field: err.field, message: err.message };
    // A stale page: reload it; the ask closes when the reloaded task can no longer be changed
    if (!err.field && err.status === 409) emit("reload");
  } finally {
    cancelBusy.value = false;
  }
}
</script>

<template>
  <div>
    <div v-if="shown" class="card mb-3" data-testid="tasks">
      <div class="card-header d-flex justify-content-between align-items-center gap-2">
        <span data-testid="tasks-title">Tasks<template v-if="countsText"> ({{ countsText }})</template></span>
        <button v-if="ticket.can_add_task" type="button" class="btn btn-outline-primary" @click="taskDialog.openAdd()">
          <i class="fa-solid fa-plus me-1"></i>Add task
        </button>
      </div>
      <div v-if="!tasks.length" class="card-body text-secondary">
        <div>No tasks yet.</div>
        <div v-if="ticket.can_add_task" class="small">Give each check or follow-up job to one person, with a date.</div>
      </div>
      <ul v-else class="list-group list-group-flush">
        <TaskItem
          v-for="(t, i) in tasks"
          :key="t.id"
          :task="t"
          :number="i + 1"
          :cancelling="cancellingId === t.id"
          :cancel-busy="cancelBusy"
          :cancel-error="cancellingId === t.id ? cancelError : null"
          @change="taskDialog.openChange(t)"
          @ask-cancel="askCancel(t)"
          @keep="keep"
          @cancel="(reason) => cancelTask(t, reason)"
          @mark-done="markDoneDialog.open(taskDoneTarget(ticket.id, t))"
        />
      </ul>
    </div>
    <!-- Outside the card's v-if: a reload that hides the card must not tear down an open dialog -->
    <TaskDialog
      ref="taskDialog"
      :ticket="ticket"
      :people="people"
      :own-person-id="ownPersonId"
      @saved="emit('saved', $event)"
      @reload="emit('reload')"
    />
    <MarkDoneDialog ref="markDoneDialog" @saved="emit('saved', $event)" @reload="emit('reload')" />
  </div>
</template>
