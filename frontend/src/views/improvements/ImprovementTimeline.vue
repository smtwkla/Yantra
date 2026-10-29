<script setup>
/**
 * The card *Timeline* (docs/steps/S073-verified-close-screens/1-brief.md § 5.6): the record of who
 * did what and when (ISO 9001 § 7.5.3), newest first as the server sends it. The newest 10 show,
 * then *Show all*. The computed *Watch ended* line has no id and no person. Rows are keyed by
 * their index. A changed why's or root cause's earlier text shows as "Was: …".
 */
import { ref } from "vue";
import { useShowMore } from "../../composables/useShowMore";
import { formatDateTime } from "../../utils/datetime";
import { actionKindLabel, eventLabel, improvementStateLabel } from "../../utils/improvementLabels";
import ImprovementNoteDialog from "./ImprovementNoteDialog.vue";

const props = defineProps({
  improvement: { type: Object, required: true },
});
const emit = defineEmits(["saved", "reload"]);

const noteDialog = ref(null);
const more = useShowMore(() => props.improvement.timeline);

const SHOWS_TICKET = ["ticket_linked", "ticket_removed"];
const SHOWS_ACTION = ["action_done", "action_cancelled"];
</script>

<template>
  <div class="card mt-3" data-testid="improvement-timeline">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span>Timeline</span>
      <button v-if="improvement.can_add_note" type="button" class="btn btn-outline-primary" @click="noteDialog.open()">
        <i class="fa-regular fa-comment me-1"></i>Add note
      </button>
    </div>
    <ul class="list-group list-group-flush">
      <li v-for="(line, i) in more.shown.value" :key="i" class="list-group-item" :data-event="line.event">
        <div class="small text-secondary">
          {{ formatDateTime(line.occurred_at) }}<template v-if="line.by_name"> · {{ line.by_name }}</template>
        </div>
        <div>
          <span class="fw-semibold">{{ eventLabel(line.event) }}</span>
          <template v-if="line.event === 'state_changed' && line.to_state"> · Now {{ improvementStateLabel(line.to_state) }}</template>
          <template v-if="line.ticket && SHOWS_TICKET.includes(line.event)">
            · <router-link :to="`/tickets/${line.ticket.id}`">{{ line.ticket.serial }}</router-link>
          </template>
          <template v-if="line.action && SHOWS_ACTION.includes(line.event)">
            · {{ actionKindLabel(line.action.kind) }}: {{ line.action.text }}
          </template>
        </div>
        <div v-if="line.remark" class="line-text">{{ line.remark }}</div>
        <div v-if="line.earlier" :class="line.remark ? 'small text-secondary line-text' : 'line-text'">
          <template v-if="line.remark">Was: </template>{{ line.earlier }}
        </div>
      </li>
    </ul>
    <div v-if="more.canExpand.value" class="card-footer text-center">
      <button type="button" class="btn btn-link" @click="more.toggle()">{{ more.toggleLabel.value }}</button>
    </div>
    <ImprovementNoteDialog ref="noteDialog" :improvement="improvement" @saved="(r) => emit('saved', r)" @reload="emit('reload')" />
  </div>
</template>

<style scoped>
.line-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
