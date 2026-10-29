<script setup>
/**
 * Improvement page (docs/steps/S068-improvement-screens/1-brief.md § 5.4; mock-up
 * docs/roadmap/R05-mockups/02-analysis.html, left half). One column on a phone: the header, the
 * card *The problem*, the card *Tickets*, then S069's cards *Why-why* and *Root cause* with the
 * note on the two causes. On a wide screen the problem and the tickets take the left half, the
 * analysis the right half.
 *
 * S071's card *Countermeasures* (docs/steps/S071-countermeasure-screens/1-brief.md § 5.1; mock-up
 * 03-countermeasures.html) runs across the full width under both columns.
 *
 * Every control follows the detail's `permissions`, `is_open` and each ticket's `removable`, so
 * no button ends in a refusal. Each write answers with the whole detail, which replaces the page's
 * copy, so the header, the loss line and the rows always agree.
 */
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiDelete, apiGet, apiPost } from "../api";
import CountermeasureItem from "../components/CountermeasureItem.vue";
import DocumentsCards from "../components/documents/DocumentsCards.vue";
import IntensityBadge from "../components/IntensityBadge.vue";
import TicketsTabs from "../components/TicketsTabs.vue";
import { formatDateTime } from "../utils/datetime";
import { causeGroupLabel } from "../stores/masters";
import { ACTION_KINDS, actionCountsText, causeText, improvementStateLabel, lossText, ticketCauses } from "../utils/improvementLabels";
import { minutesText } from "../utils/ticketLabels";
import ActionDialog from "./improvements/ActionDialog.vue";
import AddTicketDialog from "./improvements/AddTicketDialog.vue";
import ImprovementDialog from "./improvements/ImprovementDialog.vue";
import MarkDoneDialog from "./improvements/MarkDoneDialog.vue";
import RootCauseDialog from "./improvements/RootCauseDialog.vue";
import WhyDialog from "./improvements/WhyDialog.vue";

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
const whyDialog = ref(null);
const rootCauseDialog = ref(null);
const confirmingRemoveWhyId = ref(null);
const removeWhyError = ref("");
const actionDialog = ref(null);
const markDoneDialog = ref(null);
const cancellingId = ref(null); // the countermeasure that asks for a reason: one at a time
const cancelBusy = ref(false);
const cancelError = ref(null); // {field, message} of the last refused cancel
const photosOpenId = ref(null); // the countermeasure whose photo cards show under its row: one at a time

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
  confirmingRemoveWhyId.value = null;
  removeWhyError.value = "";
  cancellingId.value = null;
  cancelError.value = null;
}

function askRemove(t) {
  confirmingRemoveId.value = t.id;
  removeError.value = "";
  confirmingRemoveWhyId.value = null;
  removeWhyError.value = "";
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

function askRemoveWhy(why) {
  confirmingRemoveWhyId.value = why.id;
  removeWhyError.value = "";
  confirmingRemoveId.value = null;
  removeError.value = "";
}

async function removeWhy(why) {
  removing.value = true;
  removeWhyError.value = "";
  try {
    onSaved(await apiDelete(`/api/improvements/${improvement.value.id}/whys/${why.id}`));
  } catch (err) {
    removeWhyError.value = err.message;
  } finally {
    removing.value = false;
  }
}

function askCancel(action) {
  cancellingId.value = action.id;
  cancelError.value = null;
}

async function cancelAction(action, reason) {
  cancelBusy.value = true;
  cancelError.value = null;
  try {
    onSaved(await apiPost(`/api/improvements/${improvement.value.id}/actions/${action.id}/cancel`, { reason }));
  } catch (err) {
    cancelError.value = { field: err.field, message: err.message };
    // A stale row (409, no field): the owner marked it done meanwhile, so show what is true now
    // and close its cancel ask when the reloaded row can no longer be cancelled (S071 CR2-01)
    if (!err.field && err.status === 409) load().then(() => closeStaleCancel(action.id));
  } finally {
    cancelBusy.value = false;
  }
}

// load() catches its own errors, so this runs after every reload; a row still open keeps its ask
function closeStaleCancel(actionId) {
  if (cancellingId.value !== actionId) return;
  const row = improvement.value?.actions.find((a) => a.id === actionId);
  if (!row?.can_change) cancellingId.value = null;
}

function togglePhotos(action) {
  photosOpenId.value = photosOpenId.value === action.id ? null : action.id;
}

// "Priya (engineer), 29-10-2026 11:52", and who changed it when that is someone else
function whyByline(why) {
  const line = `${why.created_by_name}, ${formatDateTime(why.created_at)}`;
  return why.updated_by_name && why.updated_by_name !== why.created_by_name ? `${line} · changed by ${why.updated_by_name}` : line;
}

// The linked tickets' own causes beside the root cause (Q2.3 a); the tickets are never written
const ticketCauseText = computed(() => ticketCauses(improvement.value?.tickets ?? []).map(causeText).join(", "));

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

        <div class="col-lg-6">
          <div class="card mb-3" data-testid="why-why">
            <div class="card-header d-flex justify-content-between align-items-center">
              <span>Why-why</span>
              <button v-if="canEdit" type="button" class="btn btn-outline-primary" @click="whyDialog.openAdd()">
                <i class="fa-solid fa-plus me-1"></i>Add why
              </button>
            </div>
            <div class="card-body pb-2">
              <p class="small text-secondary mb-0">Ask why until the answer is something the plant can change.</p>
            </div>
            <ul v-if="improvement.whys.length" class="list-group list-group-flush">
              <li v-for="w in improvement.whys" :key="w.id" class="list-group-item" :data-why="w.position">
                <div class="d-flex align-items-start gap-2">
                  <div class="flex-grow-1 text-break">
                    <div class="fw-semibold">{{ w.position }}. {{ w.question }}</div>
                    <div class="analysis-text">{{ w.answer }}</div>
                    <div v-if="w.evidence" class="text-secondary analysis-text">Evidence: {{ w.evidence }}</div>
                    <div class="small text-secondary">{{ whyByline(w) }}</div>
                  </div>
                  <template v-if="canEdit && confirmingRemoveWhyId !== w.id">
                    <button type="button" class="btn btn-outline-primary" :aria-label="`Edit why ${w.position}`" @click="whyDialog.openChange(w)">
                      <i class="fa-solid fa-pen"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger" :aria-label="`Remove why ${w.position}`" @click="askRemoveWhy(w)">
                      <i class="fa-solid fa-trash"></i>
                    </button>
                  </template>
                </div>
                <template v-if="confirmingRemoveWhyId === w.id">
                  <div class="d-flex flex-wrap align-items-center justify-content-end gap-3 mt-2">
                    <span>Remove why {{ w.position }}? You cannot undo this.</span>
                    <button type="button" class="btn btn-danger" :disabled="removing" @click="removeWhy(w)">Remove why</button>
                    <button type="button" class="btn btn-outline-secondary" @click="confirmingRemoveWhyId = null">Cancel</button>
                  </div>
                  <div v-if="removeWhyError" class="alert alert-danger py-2 mt-2 mb-0">{{ removeWhyError }}</div>
                </template>
              </li>
            </ul>
            <div v-else class="card-body pt-0">
              <p class="mb-0">No whys yet.</p>
              <p v-if="canEdit" class="mb-0 text-secondary">Start with why the problem happened.</p>
            </div>
          </div>

          <div class="card" data-testid="root-cause">
            <div class="card-header d-flex justify-content-between align-items-center">
              <span><i class="fa-solid fa-crosshairs me-1"></i>Root cause</span>
              <button v-if="canEdit" type="button" class="btn btn-outline-primary" @click="rootCauseDialog.open()">
                {{ improvement.root_cause ? "Edit root cause" : "Set root cause" }}
              </button>
            </div>
            <div class="card-body">
              <template v-if="improvement.root_cause">
                <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
                  <span class="badge text-bg-primary text-wrap">
                    {{ causeText(improvement.root_cause.cause) }}<template v-if="!improvement.root_cause.cause.active"> (inactive)</template>
                  </span>
                  <span class="small text-secondary">Group: {{ causeGroupLabel(improvement.root_cause.cause.cause_group) }}</span>
                </div>
                <p class="mb-0 analysis-text">{{ improvement.root_cause.text }}</p>
                <p v-if="improvement.contributing_causes" class="mt-2 mb-0 analysis-text">
                  Other causes: {{ improvement.contributing_causes }}
                </p>
              </template>
              <p v-else class="mb-0 text-secondary">No root cause yet. Find it with the why-why first.</p>
            </div>
          </div>
          <div v-if="ticketCauseText" class="small mt-2" data-testid="ticket-causes">
            <div>Cause on the tickets: {{ ticketCauseText }}</div>
            <div class="text-secondary">The ticket's cause says why the part failed. The root cause says why the plant let it happen.</div>
          </div>
        </div>
      </div>

      <div class="card mt-3" data-testid="countermeasures">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>
            Countermeasures<template v-if="actionCountsText(improvement.action_counts)"> ({{ actionCountsText(improvement.action_counts) }})</template>
          </span>
          <button v-if="canEdit" type="button" class="btn btn-outline-primary" @click="actionDialog.openAdd()">
            <i class="fa-solid fa-plus me-1"></i>Add countermeasure
          </button>
        </div>
        <ul v-if="improvement.actions.length" class="list-group list-group-flush">
          <CountermeasureItem
            v-for="(a, i) in improvement.actions"
            :key="a.id"
            :action="a"
            :number="i + 1"
            :cancelling="cancellingId === a.id"
            :cancel-busy="cancelBusy"
            :cancel-error="cancellingId === a.id ? cancelError : null"
            :photos-open="photosOpenId === a.id"
            @change="actionDialog.openChange(a)"
            @ask-cancel="askCancel(a)"
            @keep="cancellingId = null"
            @cancel="(reason) => cancelAction(a, reason)"
            @mark-done="markDoneDialog.open({ improvementId: improvement.id, action: a })"
            @photos="togglePhotos(a)"
          >
            <DocumentsCards
              v-if="photosOpenId === a.id"
              :base-path="`/api/improvements/actions/${a.id}/documents`"
              :can-edit="a.can_add_photo"
              large-add
              @changed="load"
            />
          </CountermeasureItem>
        </ul>
        <div v-else class="card-body">
          <p class="mb-0">No countermeasures yet.</p>
          <p v-if="canEdit" class="mb-0 text-secondary">Add what the team will do about the root cause.</p>
        </div>
        <div class="card-footer small text-secondary" data-testid="kind-help">
          <div v-for="k in ACTION_KINDS" :key="k.key"><em>{{ k.label }}</em>: {{ k.sentence }}</div>
        </div>
      </div>

      <ImprovementDialog ref="editDialog" @saved="onSaved" />
      <AddTicketDialog ref="addDialog" :improvement="improvement" @saved="onSaved" />
      <WhyDialog ref="whyDialog" :improvement="improvement" @saved="onSaved" />
      <RootCauseDialog ref="rootCauseDialog" :improvement="improvement" @saved="onSaved" />
      <ActionDialog ref="actionDialog" :improvement="improvement" @saved="onSaved" />
      <MarkDoneDialog ref="markDoneDialog" @saved="onSaved" @reload="load" />
    </template>
  </div>
</template>

<style scoped>
.problem-text,
.analysis-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.details dd {
  overflow-wrap: anywhere;
}
</style>
