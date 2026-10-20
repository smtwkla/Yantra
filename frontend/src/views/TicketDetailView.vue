<script setup>
/**
 * Ticket page (docs/steps/S017-raise-tickets/1-brief.md § 1): serial, intensity, state, the
 * machine (a link to its equipment page) and component, symptom, description, who found it,
 * who raised it, when it happened, the photos and the timeline. S017 writes only the
 * "raised" event; S018 adds the rest.
 *
 * Photos through DocumentsCards, photos only; adding, retitling and removing them follow
 * the API's can_add_photos (ticket:raise at the ticket's site, not closed).
 */
import { ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiGet } from "../api";
import IntensityBadge from "../components/IntensityBadge.vue";
import DocumentsCards from "../components/documents/DocumentsCards.vue";
import { formatDateTime } from "../utils/datetime";
import { ageText, EVENT_LABELS, INTENSITY_LABELS, STATE_LABELS } from "../utils/ticketLabels";

const route = useRoute();

const ticket = ref(null);
const loading = ref(true);
const notFound = ref(false);
const forbidden = ref(false);
const loadError = ref("");
let loadSeq = 0;

async function load() {
  const id = route.params.id;
  if (id === undefined) return; // the route is changing to another page
  const seq = ++loadSeq;
  loading.value = true;
  notFound.value = false;
  forbidden.value = false;
  loadError.value = "";
  try {
    const loaded = await apiGet(`/api/tickets/${id}`);
    if (seq === loadSeq) ticket.value = loaded;
  } catch (err) {
    if (seq !== loadSeq) return;
    ticket.value = null;
    if (err.status === 404) notFound.value = true;
    else if (err.status === 403) forbidden.value = true; // no ticket:read: the API's text names a permission key
    else loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

watch(() => route.params.id, load, { immediate: true });
</script>

<template>
  <div class="py-3">
    <div v-if="loading && !ticket" class="text-secondary">Loading…</div>
    <div v-else-if="notFound" class="alert alert-warning">
      Ticket not found, or not at your units.
      <router-link to="/tickets" class="alert-link ms-1">Back to the list</router-link>
    </div>
    <div v-else-if="forbidden" class="alert alert-warning">You can't see this ticket.</div>
    <div v-else-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger" @click="load">Retry</button>
    </div>

    <template v-else-if="ticket">
      <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
        <h4 class="mb-0 me-2">{{ ticket.serial }}</h4>
        <IntensityBadge :intensity="ticket.intensity" />
        <span class="badge text-bg-light border">{{ STATE_LABELS[ticket.state] ?? ticket.state }}</span>
      </div>

      <div class="row g-3">
        <div class="col-lg-6">
          <div class="card h-100">
            <div class="card-header">Details</div>
            <div class="card-body">
              <dl class="row mb-0 details">
                <dt class="col-5">Machine</dt>
                <dd class="col-7">
                  <router-link :to="`/equipment/${ticket.machine.id}`">{{ ticket.machine.code }}</router-link>
                  — {{ ticket.machine.name }}
                </dd>
                <template v-if="ticket.component">
                  <dt class="col-5">Part</dt>
                  <dd class="col-7">
                    <router-link :to="`/equipment/${ticket.component.id}`">{{ ticket.component.code }}</router-link>
                    — {{ ticket.component.name }}
                  </dd>
                </template>
                <dt class="col-5">Unit</dt><dd class="col-7">{{ ticket.unit.site_code }}.{{ ticket.unit.code }}</dd>
                <dt class="col-5">Symptom</dt>
                <dd class="col-7">{{ ticket.failure_mode ? ticket.failure_mode.label : "—" }}</dd>
                <dt class="col-5">When it happened</dt>
                <dd class="col-7">
                  {{ formatDateTime(ticket.occurred_at) }}
                  <span class="text-secondary">({{ ageText(ticket.occurred_at) }} ago)</span>
                </dd>
                <dt class="col-5">Found by</dt><dd class="col-7">{{ ticket.reported_by?.name ?? "—" }}</dd>
                <dt class="col-5">Raised by</dt>
                <dd class="col-7 mb-0">{{ ticket.created_by }}, {{ formatDateTime(ticket.created_at) }}</dd>
              </dl>
            </div>
          </div>
        </div>
        <div class="col-lg-6">
          <div class="card h-100">
            <div class="card-header">Timeline</div>
            <ul class="list-group list-group-flush">
              <li v-for="(e, i) in ticket.events" :key="i" class="list-group-item">
                <div class="d-flex flex-wrap gap-2">
                  <span class="fw-semibold">{{ EVENT_LABELS[e.event] ?? e.event }}</span>
                  <span v-if="e.intensity" class="text-secondary">· {{ INTENSITY_LABELS[e.intensity] }}</span>
                  <span class="ms-auto small">{{ formatDateTime(e.occurred_at) }}</span>
                </div>
                <div class="small text-secondary">
                  {{ e.created_by }}<template v-if="e.person"> · {{ e.person.name }}</template>
                </div>
                <div v-if="e.remark" class="small text-break">{{ e.remark }}</div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div v-if="ticket.description" class="card mt-3">
        <div class="card-header">Description</div>
        <!-- pre-wrap: shown as entered -->
        <div class="card-body description-text">{{ ticket.description }}</div>
      </div>

      <DocumentsCards :base-path="`/api/tickets/${ticket.id}/documents`" :can-edit="ticket.can_add_photos" photos-only large-add />
    </template>
  </div>
</template>

<style scoped>
.description-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.details dd {
  overflow-wrap: anywhere;
}
</style>
