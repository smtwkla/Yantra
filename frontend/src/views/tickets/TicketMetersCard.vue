<script setup>
/**
 * The Meters card on the ticket page (docs/steps/S052-ticket-meters/1-brief.md § 1): each meter in
 * force on the ticket's machine and the nodes down to its part, with the reading as it stood at
 * the ticket's time (*When it happened*) and how long before it was taken, its High / Low / Not OK
 * / Reset marks, and a warning when the meter was marked in the days before. *Open register* per
 * node opens S050's register.
 *
 * Its own API call (§ 7 decision 2), so a failure leaves the ticket page working. Nothing is drawn
 * while loading, and nothing when no node has a meter (§ 1.6, § 1.7): a ticket on a machine
 * without meters never shows a card that then vanishes. Reloads when the ticket's part changes
 * (*Edit*); the ticket's time cannot be edited.
 */
import { ref, watch } from "vue";
import { apiGet } from "../../api";
import { formatDateTime } from "../../utils/datetime";
import {
  beforeText, formatReading, markWarningText, readingBadgeClass, readingBadges, registerQuery,
} from "../../utils/meterLabels";

const props = defineProps({
  // The ticket's detail: id, occurred_at and component are used
  ticket: { type: Object, required: true },
});

const LOAD_FAILED = "Meter readings could not be loaded. Try again in a minute.";

const answer = ref(null); // null until the first answer
const loadError = ref(false);
const loading = ref(false);
let loadSeq = 0;

async function load() {
  const seq = ++loadSeq;
  loading.value = true;
  try {
    const result = await apiGet(`/api/tickets/${props.ticket.id}/meters`);
    if (seq === loadSeq) {
      answer.value = result;
      loadError.value = false; // cleared only by an answer, so the card stays put during Try again (§ 7 decision 10)
    }
  } catch {
    // Every failure, 503 included, reads the same: the card says so and offers Try again (§ 1.7)
    if (seq === loadSeq) loadError.value = true;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

// A multi-source watch compares the values, so the page's reload after a move (a new ticket
// object, the same part) does not load again. Until a changed part's answer arrives, the card
// keeps the previous one rather than vanishing and coming back.
watch([() => props.ticket.id, () => props.ticket.component?.id], ([id], [oldId] = []) => {
  if (id !== oldId) { answer.value = null; loadError.value = false; }
  load();
}, { immediate: true });

const warning = (line) => markWarningText(line.meter_type.kind, line.marked_count, answer.value.mark_window_days);
</script>

<template>
  <div v-if="loadError || answer?.nodes.length" class="card mb-3" data-testid="ticket-meters">
    <div class="card-header">Meters</div>
    <div v-if="loadError" class="card-body d-flex flex-wrap justify-content-between align-items-center gap-2">
      <span class="text-danger">{{ LOAD_FAILED }}</span>
      <button type="button" class="btn btn-outline-danger" :disabled="loading" @click="load">Try again</button>
    </div>
    <template v-else>
      <div class="card-body pb-0 small text-secondary">Readings up to {{ formatDateTime(answer.at) }}, when it happened</div>
      <div v-for="entry in answer.nodes" :key="entry.node.id" data-testid="ticket-meters-node">
        <div class="px-3 pt-3 pb-2 d-flex flex-wrap align-items-center justify-content-between gap-2">
          <span class="fw-semibold text-break">{{ entry.node.code }} — {{ entry.node.name }}</span>
          <router-link class="btn btn-outline-secondary touch-target" :to="{ path: '/readings', query: registerQuery(entry.node.id) }">
            <i class="fa-solid fa-table me-1"></i>Open register
          </router-link>
        </div>
        <ul class="list-group list-group-flush">
          <li v-for="line in entry.meters" :key="line.meter_type.id" class="list-group-item" data-testid="ticket-meter">
            <div class="d-flex flex-wrap align-items-center gap-2">
              <span class="fw-semibold">{{ line.meter_type.name }}</span>
              <template v-if="line.at_ticket">
                <span>{{ formatReading(line.at_ticket.value, line.meter_type) }}</span>
                <span v-for="badge in readingBadges(line.at_ticket)" :key="badge" class="badge" :class="readingBadgeClass(badge)">{{ badge }}</span>
              </template>
            </div>
            <div v-if="line.at_ticket" class="small text-secondary">
              {{ formatDateTime(line.at_ticket.taken_at) }} · {{ beforeText(line.at_ticket.taken_at, answer.at) }}
            </div>
            <div v-else class="small text-secondary">No reading before this time</div>
            <div v-if="warning(line)" class="small text-warning-emphasis mt-1" data-testid="ticket-meter-warning">
              <i class="fa-solid fa-triangle-exclamation me-1" aria-hidden="true"></i>{{ warning(line) }}
            </div>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* A glove on a floor screen (U3): at least 44 px high */
.touch-target {
  min-height: 44px;
}
</style>
