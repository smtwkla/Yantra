<script setup>
/**
 * One task's row (docs/steps/S107-ticket-task-screens/1-brief.md § 5.2), for the ticket page's
 * Tasks card and for *Me › Open work*. A task is one piece of a ticket's corrective work, for one
 * person, with a due date (S106).
 *
 * Two answer shapes: a detail entry (state, owner, done and cancelled fields, can_change) and a
 * `mine` item (none of those, plus `ticket`). The row reads `state ?? "open"`, shows the owner line
 * only when `owner` is there, and the ticket line only with `showTicket`.
 *
 * The row makes no call. It emits `change`, `ask-cancel`, `keep` and `cancel(reason)` (the inline
 * cancel, CancelAsk) and `mark-done`; the card makes the calls and holds which row asks
 * (`cancelling`), so one row asks at a time. Every button follows the server's flags (`can_change`,
 * `can_mark_done`), so none ends in a refusal. On Me (`showTicket`) there is no change or cancel:
 * Me is for doing the work (S071 D5).
 *
 * The owner mark (taskOwnerMark) shows only to the people who can change the task (D8): it tells
 * the engineer to record for an owner who cannot, or to pick another.
 */
import { computed } from "vue";
import { formatDateTime } from "../utils/datetime";
import { ACTION_STATE_LABELS, overdueText } from "../utils/improvementLabels";
import { taskOwnerMark } from "../utils/ticketLabels";
import CancelAsk from "./CancelAsk.vue";

const props = defineProps({
  task: { type: Object, required: true },
  // The row's number in the list: names its icon buttons ("Change task 2")
  number: { type: Number, default: 0 },
  // Me: a line with the ticket, a red row when overdue, no change or cancel buttons
  showTicket: { type: Boolean, default: false },
  cancelling: { type: Boolean, default: false },
  cancelBusy: { type: Boolean, default: false },
  // {field, message} of the last refused cancel
  cancelError: { type: Object, default: null },
});
const emit = defineEmits(["change", "ask-cancel", "keep", "cancel", "mark-done"]);

const state = computed(() => props.task.state ?? "open");
const overdue = computed(() => state.value === "open" && props.task.overdue_days > 0);
const owner = computed(() => props.task.owner ?? null);
const ownerLeft = computed(() => owner.value && (!owner.value.active || !owner.value.may_own));
const ownerMark = computed(() => taskOwnerMark(props.task));
const recordedBy = computed(() => {
  const by = props.task.done_by_name;
  return by && by !== owner.value?.name ? by : "";
});
const canChange = computed(() => props.task.can_change && !props.showTicket);
</script>

<template>
  <li
    class="list-group-item"
    :class="{ 'list-group-item-danger': showTicket && overdue, 'text-secondary': state === 'cancelled' }"
    :data-task="task.id"
  >
    <div class="task-row">
      <div class="task-badges d-flex flex-wrap align-items-center gap-2">
        <span v-if="overdue" class="badge text-bg-danger">{{ overdueText(task.overdue_days) }}</span>
        <span
          v-else
          class="badge"
          :class="{ 'text-bg-secondary': state === 'open', 'text-bg-success': state === 'done', 'text-bg-light border': state === 'cancelled' }"
        >{{ ACTION_STATE_LABELS[state] ?? state }}</span>
      </div>
      <div class="task-due small text-nowrap">due {{ formatDateTime(task.due_date) }}</div>
      <div class="task-body text-break">
        <div class="task-text">{{ task.text }}</div>
        <div v-if="owner" class="small">
          Owner: {{ owner.name }}<template v-if="ownerLeft"> (not at this site now)</template>
        </div>
        <div v-if="ownerMark" class="small text-warning-emphasis" data-testid="owner-mark">
          <i class="fa-solid fa-circle-exclamation me-1"></i>{{ ownerMark }}
        </div>
        <template v-if="state === 'done'">
          <div class="small">
            Done {{ formatDateTime(task.done_at) }}<template v-if="recordedBy"> · recorded by {{ recordedBy }}</template>
          </div>
          <div class="task-text small">{{ task.done_text }}</div>
        </template>
        <div v-if="state === 'cancelled'" class="small task-text">
          Cancelled {{ formatDateTime(task.cancelled_at) }} by {{ task.cancelled_by_name }}: {{ task.cancel_reason }}
        </div>
        <div v-if="showTicket && task.ticket" class="small mt-1">
          <router-link :to="`/tickets/${task.ticket.id}`">
            {{ task.ticket.serial }} · {{ task.ticket.machine.code }} — {{ task.ticket.machine.name }}
          </router-link>
        </div>
      </div>
      <div v-if="!cancelling && (task.can_mark_done || canChange)" class="task-buttons d-flex flex-wrap align-items-center gap-2">
        <button v-if="task.can_mark_done" type="button" class="btn btn-success task-done" @click="emit('mark-done')">Mark done</button>
        <template v-if="canChange">
          <button type="button" class="btn btn-outline-primary" :aria-label="`Change task ${number}`" @click="emit('change')">
            <i class="fa-solid fa-pen"></i>
          </button>
          <button type="button" class="btn btn-outline-danger" :aria-label="`Cancel task ${number}`" @click="emit('ask-cancel')">
            <i class="fa-solid fa-ban"></i>
          </button>
        </template>
      </div>
    </div>

    <CancelAsk
      v-if="cancelling"
      question="Cancel this task? It stays on the record with your reason."
      help="For example: moved to the improvement as a countermeasure, or added by mistake."
      confirm-label="Cancel task"
      :busy="cancelBusy"
      :error="cancelError"
      :id-suffix="`task-${task.id}`"
      @cancel="(reason) => emit('cancel', reason)"
      @keep="emit('keep')"
    />
  </li>
</template>

<style scoped>
/* The row's own layout, as CountermeasureItem's (S107 D3): stacked on a phone */
.task-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.task-due {
  margin-left: auto;
}
.task-body {
  flex: 1 1 100%;
  min-width: 0;
}
.task-buttons {
  flex: 1 1 100%;
}
.task-done {
  flex: 1 1 100%;
}
.task-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
/* A wide screen reads like a table: state | text and owner | due date | buttons. 992px is
   Bootstrap's `lg` breakpoint: the order and flex rules need scoped CSS, since a utility class
   (d-lg-flex, order-lg-*) cannot also reset the base rules above. */
@media (min-width: 992px) {
  .task-row {
    flex-wrap: nowrap;
    align-items: flex-start;
  }
  .task-badges {
    order: 1;
    flex: 0 0 8rem;
  }
  .task-body {
    order: 2;
    flex: 1 1 auto;
  }
  .task-due {
    order: 3;
    margin-left: 0;
    flex: 0 0 auto;
  }
  .task-buttons {
    order: 4;
    flex: 0 0 auto;
  }
  .task-done {
    flex: 0 0 auto;
  }
}
</style>
