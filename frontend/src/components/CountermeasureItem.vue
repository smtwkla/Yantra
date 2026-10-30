<script setup>
/**
 * One countermeasure's row (docs/steps/S071-countermeasure-screens/1-brief.md § 5.2), for the
 * improvement page and for *Me › Open work*.
 *
 * Two answer shapes: a detail entry (state, owner, done and cancelled fields, documents) and a
 * `mine` item (none of those). The row reads `state ?? "open"`, shows the owner line only when
 * `owner` is there, the done and cancelled lines only when the state says so, and the photos
 * button only when `documents` is there.
 *
 * The row makes no call. It emits `change`, `ask-cancel`, `keep` (the inline cancel's two
 * taps), `cancel(reason)`, `mark-done` and `photos`; the page makes the calls and holds which
 * row asks and which row shows its photos (`cancelling`, `photosOpen`), so only one of each is
 * open at a time. Every button follows the server's flags (`can_change`, `can_mark_done`,
 * `can_add_photo`, `can_write_lesson`), so none ends in a refusal.
 *
 * A *Lesson* countermeasure shows its lesson (S077 § 5.4; `lesson` is in the detail shape only) as a link to
 * its page, or "Write lesson", which emits `write-lesson`; the page opens the lesson dialog.
 */
import { computed, nextTick, ref, watch } from "vue";
import { formatDateTime } from "../utils/datetime";
import { ACTION_STATE_LABELS, actionKindLabel, CANCEL_REASON_MAX, overdueText } from "../utils/improvementLabels";

const props = defineProps({
  action: { type: Object, required: true },
  // The row's number in the list: names its icon buttons ("Change countermeasure 3")
  number: { type: Number, default: 0 },
  // Me: a line with the improvement, a red row when overdue, no change or cancel buttons
  showImprovement: { type: Boolean, default: false },
  cancelling: { type: Boolean, default: false },
  cancelBusy: { type: Boolean, default: false },
  // {field, message} of the last refused cancel
  cancelError: { type: Object, default: null },
  photosOpen: { type: Boolean, default: false },
});
const emit = defineEmits(["change", "ask-cancel", "keep", "cancel", "mark-done", "photos", "write-lesson"]);

const state = computed(() => props.action.state ?? "open");
const overdue = computed(() => state.value === "open" && props.action.overdue_days > 0);
const documentCount = computed(() => props.action.documents?.length ?? null);
const owner = computed(() => props.action.owner ?? null);
const ownerLeft = computed(() => owner.value && (!owner.value.active || !owner.value.may_own));
const recordedBy = computed(() => {
  const by = props.action.done_by_name;
  return by && by !== owner.value?.name ? by : "";
});

// The photos button (§ 5.2): on a done row "Photos (n)" or, with none and the right, "Add photos";
// on an open or cancelled row "Photos (n)" only to view
const photosLabel = computed(() => {
  if (documentCount.value === null) return "";
  if (documentCount.value > 0) return `Photos (${documentCount.value})`;
  return state.value === "done" && props.action.can_add_photo ? "Add photos" : "";
});

const reason = ref("");
const reasonField = ref(null);
const reasonId = computed(() => `cancel-reason-${props.action.id}`);
watch(() => props.cancelling, (asking) => {
  if (!asking) return;
  reason.value = "";
  nextTick(() => reasonField.value?.focus());
});
const reasonError = computed(() => (props.cancelError?.field === "reason" ? props.cancelError.message : ""));
const rowError = computed(() => (props.cancelError && props.cancelError.field !== "reason" ? props.cancelError.message : ""));
</script>

<template>
  <li
    class="list-group-item"
    :class="{ 'list-group-item-danger': showImprovement && overdue, 'text-secondary': state === 'cancelled' }"
    :data-action="action.id"
  >
    <div class="cm-row">
      <div class="cm-badges d-flex flex-wrap align-items-center gap-2">
        <span class="badge text-bg-light border">{{ actionKindLabel(action.kind) }}</span>
        <span v-if="overdue" class="badge text-bg-danger">{{ overdueText(action.overdue_days) }}</span>
        <span
          v-else
          class="badge"
          :class="{ 'text-bg-secondary': state === 'open', 'text-bg-success': state === 'done', 'text-bg-light border': state === 'cancelled' }"
        >{{ ACTION_STATE_LABELS[state] ?? state }}</span>
      </div>
      <div class="cm-due small text-nowrap">due {{ formatDateTime(action.due_date) }}</div>
      <div class="cm-body text-break">
        <div class="cm-text">{{ action.text }}</div>
        <div v-if="owner" class="small">
          Owner: {{ owner.name }}<template v-if="ownerLeft"> (not at this site now)</template>
        </div>
        <template v-if="state === 'done'">
          <div class="small">
            Done {{ formatDateTime(action.done_at) }}<template v-if="recordedBy"> · recorded by {{ recordedBy }}</template>
          </div>
          <div class="cm-text small">{{ action.done_text }}</div>
        </template>
        <div v-if="state === 'cancelled'" class="small cm-text">
          Cancelled {{ formatDateTime(action.cancelled_at) }} by {{ action.cancelled_by_name }}: {{ action.cancel_reason }}
        </div>
        <div v-if="action.lesson" class="small mt-1">
          <router-link :to="`/equipment/lessons/${action.lesson.id}`">
            Lesson {{ action.lesson.serial }} · {{ action.lesson.title }}
          </router-link>
          <template v-if="!action.lesson.active"> (retired)</template>
        </div>
        <div v-if="showImprovement && action.improvement" class="small mt-1">
          <router-link :to="`/tickets/improvements/${action.improvement.id}`">
            {{ action.improvement.serial }} · {{ action.improvement.title }}
          </router-link>
        </div>
      </div>
      <div v-if="!cancelling" class="cm-buttons d-flex flex-wrap align-items-center gap-2">
        <button v-if="action.can_mark_done" type="button" class="btn btn-success cm-done" @click="emit('mark-done')">Mark done</button>
        <button v-if="action.can_write_lesson" type="button" class="btn btn-outline-primary tap-target" @click="emit('write-lesson')">
          Write lesson
        </button>
        <button v-if="photosLabel" type="button" class="btn btn-outline-secondary" :aria-expanded="photosOpen" @click="emit('photos')">
          <i class="fa-solid fa-camera me-1"></i>{{ photosLabel }}
        </button>
        <template v-if="action.can_change && !showImprovement">
          <button type="button" class="btn btn-outline-primary" :aria-label="`Change countermeasure ${number}`" @click="emit('change')">
            <i class="fa-solid fa-pen"></i>
          </button>
          <button type="button" class="btn btn-outline-danger" :aria-label="`Cancel countermeasure ${number}`" @click="emit('ask-cancel')">
            <i class="fa-solid fa-ban"></i>
          </button>
        </template>
      </div>
    </div>

    <div v-if="cancelling" class="mt-2">
      <p class="mb-2">Cancel this countermeasure? It stays on the record with your reason.</p>
      <label class="form-label" :for="reasonId">Why cancel it?</label>
      <textarea
        :id="reasonId"
        ref="reasonField"
        v-model="reason"
        class="form-control"
        :class="{ 'is-invalid': reasonError }"
        rows="2"
        :maxlength="CANCEL_REASON_MAX"
      ></textarea>
      <div v-if="reasonError" class="invalid-feedback d-block">{{ reasonError }}</div>
      <div class="form-text">For example: done by another countermeasure, or added by mistake.</div>
      <div class="d-flex flex-wrap justify-content-end gap-2 mt-2">
        <button type="button" class="btn btn-danger" :disabled="cancelBusy || !reason.trim()" @click="emit('cancel', reason.trim())">
          Cancel countermeasure
        </button>
        <button type="button" class="btn btn-outline-secondary" :disabled="cancelBusy" @click="emit('keep')">Keep it</button>
      </div>
      <div v-if="rowError" class="alert alert-danger py-2 mt-2 mb-0">{{ rowError }}</div>
    </div>

    <!-- The page puts the row's photo cards here while its photos button is open -->
    <slot />
  </li>
</template>

<style scoped>
.cm-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.cm-due {
  margin-left: auto;
}
.cm-body {
  flex: 1 1 100%;
  min-width: 0;
}
.cm-buttons {
  flex: 1 1 100%;
}
.cm-done {
  flex: 1 1 100%;
}
.cm-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
/* A wide screen reads like a table: kind and state | text and owner | due date | buttons.
   992px is Bootstrap's `lg` breakpoint: the order and flex rules need scoped CSS, since a
   utility class (d-lg-flex, order-lg-*) cannot also reset the base rules above. */
@media (min-width: 992px) {
  .cm-row {
    flex-wrap: nowrap;
    align-items: flex-start;
  }
  .cm-badges {
    order: 1;
    flex: 0 0 11rem;
  }
  .cm-body {
    order: 2;
    flex: 1 1 auto;
  }
  .cm-due {
    order: 3;
    margin-left: 0;
    flex: 0 0 auto;
  }
  .cm-buttons {
    order: 4;
    flex: 0 0 auto;
  }
  .cm-done {
    flex: 0 0 auto;
  }
}
</style>
