<script setup>
/**
 * Improvement page (docs/steps/S068-improvement-screens/1-brief.md § 5.4; mock-up
 * docs/roadmap/R05-mockups/02-analysis.html, left half). One column on a phone: the header, the
 * card *The problem*, the card *Tickets*. On a wide screen the two cards take the left half; the
 * right half is left for R05.2's why-why.
 *
 * Every control follows the detail's `permissions`, `is_open` and each ticket's `removable`, so
 * no button ends in a refusal. Each write answers with the whole detail, which replaces the page's
 * copy, so the header, the loss line and the rows always agree.
 */
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiDelete, apiGet } from "../api";
import IntensityBadge from "../components/IntensityBadge.vue";
import TicketsTabs from "../components/TicketsTabs.vue";
import { formatDateTime } from "../utils/datetime";
import { improvementStateLabel, lossText } from "../utils/improvementLabels";
import { minutesText } from "../utils/ticketLabels";
import AddTicketDialog from "./improvements/AddTicketDialog.vue";
import ImprovementDialog from "./improvements/ImprovementDialog.vue";

const route = useRoute();

const improvement = ref(null);
const loading = ref(true);
const notFound = ref(false);
const forbidden = ref(false);
const loadError = ref("");
let loadSeq = 0;

const editDialog = ref(null);
const addDialog = ref(null);
const confirmingRemoveId = ref(null);
const removing = ref(false);
const removeError = ref("");

const canEdit = computed(() => Boolean(improvement.value?.is_open) && (improvement.value?.permissions ?? []).includes("improvement:edit"));

async function load() {
  const id = route.params.id;
  if (id === undefined) return; // the route is changing to another page
  const seq = ++loadSeq;
  if (improvement.value && String(improvement.value.id) !== String(id)) improvement.value = null;
  loading.value = true;
  notFound.value = false;
  forbidden.value = false;
  loadError.value = "";
  try {
    const loaded = await apiGet(`/api/improvements/${id}`);
    if (seq !== loadSeq) return;
    improvement.value = loaded;
  } catch (err) {
    if (seq !== loadSeq) return;
    if (err.status === 404) { improvement.value = null; notFound.value = true; }
    else if (err.status === 403) { improvement.value = null; forbidden.value = true; }
    else {
      if (String(improvement.value?.id) !== String(id)) improvement.value = null;
      loadError.value = err.message;
    }
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

function onSaved(result) {
  improvement.value = result;
  confirmingRemoveId.value = null;
  removeError.value = "";
}

function askRemove(t) {
  confirmingRemoveId.value = t.id;
  removeError.value = "";
}

async function removeTicket(t) {
  removing.value = true;
  removeError.value = "";
  try {
    onSaved(await apiDelete(`/api/improvements/${improvement.value.id}/tickets/${t.id}`));
  } catch (err) {
    removeError.value = err.message;
  } finally {
    removing.value = false;
  }
}

// A ticket row's second line: the machine's code when it is not the improvement's machine (so the
// user sees why that machine's last ticket cannot be removed), the symptom, the cause, the downtime
function detailText(t) {
  const parts = [];
  if (t.machine.id !== improvement.value.machine.id) parts.push(t.machine.code);
  parts.push(t.failure_mode ? t.failure_mode.label : "No symptom");
  if (t.cause) parts.push(t.cause.label);
  if (t.downtime_minutes > 0) parts.push(`down ${minutesText(t.downtime_minutes)}`);
  return parts.join(" · ");
}

watch(() => route.params.id, load, { immediate: true });
</script>

<template>
  <div class="py-3">
    <TicketsTabs />
    <div v-if="loading && !improvement" class="text-secondary">Loading…</div>
    <div v-else-if="notFound" class="alert alert-warning">
      Improvement not found, or not at your units.
      <router-link to="/tickets/improvements" class="alert-link ms-1">Back to the list</router-link>
    </div>
    <div v-else-if="forbidden" class="alert alert-warning">You can't see this improvement.</div>
    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger" @click="load">Retry</button>
    </div>

    <template v-if="improvement && !notFound && !forbidden">
      <div class="mb-3">
        <div class="d-flex flex-wrap align-items-center gap-2">
          <h4 class="mb-0 me-2">{{ improvement.serial }}</h4>
          <span class="badge text-bg-light border state-badge">{{ improvementStateLabel(improvement.state) }}</span>
        </div>
        <p class="fw-semibold mt-2 mb-1 text-break" data-testid="improvement-title">{{ improvement.title }}</p>
        <p class="small text-secondary mb-0">
          Started {{ formatDateTime(improvement.created_at) }} by {{ improvement.created_by_name }} · lead {{ improvement.lead.name }}
        </p>
      </div>

      <div class="row g-3">
        <div class="col-lg-6">
          <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
              <span>The problem</span>
              <button v-if="canEdit" type="button" class="btn btn-outline-primary" @click="editDialog.openChange(improvement)">
                <i class="fa-solid fa-pen me-1"></i>Edit
              </button>
            </div>
            <div class="card-body">
              <dl class="row mb-0 details">
                <dt class="col-5">Where</dt>
                <dd class="col-7">
                  <router-link :to="`/equipment/${improvement.machine.id}`">{{ improvement.machine.code }}</router-link>
                  — {{ improvement.machine.name }}
                  <div class="small text-secondary">{{ improvement.unit.site_code }}.{{ improvement.unit.code }}</div>
                </dd>
                <dt class="col-5">What happened</dt>
                <dd class="col-7 problem-text">{{ improvement.problem }}</dd>
                <dt class="col-5">Loss</dt>
                <dd class="col-7 mb-0" data-testid="improvement-loss">{{ lossText(improvement.loss) }}</dd>
              </dl>
            </div>
          </div>

          <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
              <span>Tickets ({{ improvement.tickets.length }})</span>
              <button v-if="canEdit" type="button" class="btn btn-outline-primary" @click="addDialog.open()">
                <i class="fa-solid fa-plus me-1"></i>Add ticket
              </button>
            </div>
            <ul class="list-group list-group-flush">
              <li v-for="t in improvement.tickets" :key="t.id" class="list-group-item" :data-ticket="t.serial">
                <div class="d-flex align-items-start gap-2">
                  <div class="flex-grow-1 text-break">
                    <div class="d-flex flex-wrap align-items-center gap-2">
                      <router-link :to="`/tickets/${t.id}`" class="fw-semibold">{{ t.serial }}</router-link>
                      <IntensityBadge :intensity="t.intensity" />
                      <span class="small text-secondary">{{ formatDateTime(t.occurred_at) }}</span>
                    </div>
                    <div class="small">{{ detailText(t) }}</div>
                  </div>
                  <button
                    v-if="canEdit && t.removable && confirmingRemoveId !== t.id"
                    type="button"
                    class="btn btn-outline-danger"
                    :aria-label="`Remove ${t.serial} from this improvement`"
                    @click="askRemove(t)"
                  >
                    <i class="fa-solid fa-link-slash"></i>
                  </button>
                </div>
                <template v-if="confirmingRemoveId === t.id">
                  <div class="d-flex flex-wrap align-items-center justify-content-end gap-3 mt-2">
                    <span>Remove {{ t.serial }} from {{ improvement.serial }}? The ticket stays as it is.</span>
                    <button type="button" class="btn btn-danger" :disabled="removing" @click="removeTicket(t)">Remove ticket</button>
                    <button type="button" class="btn btn-outline-secondary" @click="confirmingRemoveId = null">Cancel</button>
                  </div>
                  <div v-if="removeError" class="alert alert-danger py-2 mt-2 mb-0">{{ removeError }}</div>
                </template>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <ImprovementDialog ref="editDialog" @saved="onSaved" />
      <AddTicketDialog ref="addDialog" :improvement="improvement" @saved="onSaved" />
    </template>
  </div>
</template>

<style scoped>
.problem-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.details dd {
  overflow-wrap: anywhere;
}
</style>
