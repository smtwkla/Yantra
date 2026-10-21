<script setup>
/**
 * Ticket page (docs/steps/S017-raise-tickets/1-brief.md § 1; worked in
 * docs/steps/S018-work-tickets/1-brief.md § 1 "The ticket page on a phone").
 *
 * Phone first, top to bottom:
 * 1. the action bar, under the header, as full-width stacked buttons: the next move in the
 *    chain (Acknowledge, Start, Back in service / Fixed); Machine stopped (an operator on a
 *    defect) or Change severity (ticket:work holders); Not fixed — raise again; then, after a
 *    gap and in outline, the significant moves Close / Not a fault / Send back. On a wider
 *    screen the same buttons sit in one row, the significant ones on the left. While there is
 *    no labour, Close is disabled with the reason written under it and Add labour beside it;
 * 2. the times, assignees and labour — shown to ticket:work holders, or when not empty;
 *    Edit and Assign sit with these panels;
 * 3. repeats, details, description, photos and documents, timeline.
 *
 * Every control follows the detail's `moves`, `permissions` (the keys at the ticket's site)
 * and `regrade_to`, so a user never sees a button that ends in a 403. Each write answers with
 * the ticket's detail, which replaces the page's copy.
 */
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiDelete, apiGet } from "../api";
import IntensityBadge from "../components/IntensityBadge.vue";
import DocumentsCards from "../components/documents/DocumentsCards.vue";
import { userPersonId } from "../stores/auth";
import { formatDateTime } from "../utils/datetime";
import {
  ageText, EVENT_LABELS, intensityChanges, minutesText, moveLabel, SIGNIFICANT_MOVES, STATE_LABELS,
} from "../utils/ticketLabels";
import AssignDialog from "./tickets/AssignDialog.vue";
import EditTicketDialog from "./tickets/EditTicketDialog.vue";
import LabourPanel from "./tickets/LabourPanel.vue";
import MoveDialog from "./tickets/MoveDialog.vue";
import RegradeDialog from "./tickets/RegradeDialog.vue";

const route = useRoute();

const ticket = ref(null);
const loading = ref(true);
const notFound = ref(false);
const forbidden = ref(false);
const loadError = ref("");
const people = ref([]);
const modes = ref([]);
const pickersError = ref("");
let loadSeq = 0;

const moveDialog = ref(null);
const regradeDialog = ref(null);
const assignDialog = ref(null);
const editDialog = ref(null);
const labourPanel = ref(null);
const confirmingUnassignId = ref(null);
const unassigning = ref(false);
const unassignError = ref("");

const can = (key) => (ticket.value?.permissions ?? []).includes(key);
const isOpen = computed(() => ticket.value && ticket.value.state !== "closed");
const canWork = computed(() => isOpen.value && can("ticket:work"));
const canAssign = computed(() => isOpen.value && can("ticket:assign"));
const chainMoves = computed(() => (ticket.value?.moves ?? []).filter((m) => !SIGNIFICANT_MOVES.includes(m.name)));
const significantMoves = computed(() => (ticket.value?.moves ?? []).filter((m) => SIGNIFICANT_MOVES.includes(m.name)));
const closeNeedsLabour = (m) => m.name === "close" && ticket.value.labour.length === 0;
// ticket:work holders get Change severity only; others Machine stopped, on a defect (BR4-05)
const showChangeSeverity = computed(() => can("ticket:work") && (ticket.value?.regrade_to ?? []).length > 0);
const showMachineStopped = computed(() => !can("ticket:work") && !ticket.value?.is_breakdown
  && (ticket.value?.regrade_to ?? []).includes("critical"));
const repeatLink = computed(() => {
  const t = ticket.value;
  return `/tickets/new?equipment=${t.component?.id ?? t.machine.id}&repeat_of=${t.id}`;
});
const times = computed(() => ticket.value?.times ?? {});
// Downtime is always a number (0 on a defect): "nothing to show" is no response, no repair, no downtime
const timesEmpty = computed(() => times.value.response_minutes === null && times.value.repair_minutes === null
  && times.value.downtime_minutes === 0);
const showTimes = computed(() => !ticket.value?.not_a_fault && (can("ticket:work") || !timesEmpty.value));
const showAssignees = computed(() => can("ticket:work") || ticket.value?.assignees.length > 0);
const showLabour = computed(() => can("ticket:work") || ticket.value?.labour.length > 0);
const intensityTexts = computed(() => intensityChanges(ticket.value?.events ?? []));

async function loadPickers(loaded, seq) {
  // People: back in service, labour and assign; symptoms: close and edit (S018 § 3)
  const moveNames = loaded.moves.map((m) => m.name);
  const work = loaded.permissions.includes("ticket:work");
  const needPeople = work || moveNames.includes("restore") || loaded.permissions.includes("ticket:assign");
  const needModes = work || moveNames.includes("close");
  pickersError.value = "";
  try {
    const [peopleList, modeList] = await Promise.all([
      needPeople ? apiGet(`/api/tickets/people?ticket_id=${loaded.id}`) : { items: [] },
      needModes ? apiGet(`/api/tickets/modes?ticket_id=${loaded.id}`) : { items: [] },
    ]);
    if (seq !== loadSeq) return;
    people.value = peopleList.items;
    modes.value = modeList.items;
  } catch (err) {
    if (seq === loadSeq) pickersError.value = `The people or symptom lists could not be loaded: ${err.message}`;
  }
}

async function load() {
  const id = route.params.id;
  if (id === undefined) return; // the route is changing to another page
  const seq = ++loadSeq;
  // Another ticket's buttons must not be live under this URL while it loads (CR5-02). The same
  // ticket is kept, so a reload after a 409 does not tear down an open dialog.
  if (ticket.value && String(ticket.value.id) !== String(id)) ticket.value = null;
  loading.value = true;
  notFound.value = false;
  forbidden.value = false;
  loadError.value = "";
  try {
    const loaded = await apiGet(`/api/tickets/${id}`);
    if (seq !== loadSeq) return;
    ticket.value = loaded;
    if (loaded.state !== "closed") loadPickers(loaded, seq);
  } catch (err) {
    if (seq !== loadSeq) return;
    // A failed reload (e.g. after a 409) keeps the ticket shown, so the open dialog is not torn
    // down mid-modal (CR4-03); only "gone" or "not allowed" clears it. Another ticket's data is never kept.
    if (err.status === 404) { ticket.value = null; notFound.value = true; }
    else if (err.status === 403) { ticket.value = null; forbidden.value = true; } // no ticket:read: the API's text names a permission key
    else {
      if (String(ticket.value?.id) !== String(id)) ticket.value = null;
      loadError.value = err.message;
    }
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

function onSaved(result) {
  ticket.value = result;
  confirmingUnassignId.value = null;
}

async function unassign(person) {
  unassigning.value = true;
  unassignError.value = "";
  try {
    onSaved(await apiDelete(`/api/tickets/${ticket.value.id}/assignees/${person.id}`));
  } catch (err) {
    unassignError.value = err.message;
  } finally {
    unassigning.value = false;
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
    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger" @click="load">Retry</button>
    </div>

    <template v-if="ticket && !notFound && !forbidden">
      <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
        <h4 class="mb-0 me-2">{{ ticket.serial }}</h4>
        <IntensityBadge :intensity="ticket.intensity" />
        <span class="badge text-bg-light border">{{ STATE_LABELS[ticket.state] ?? ticket.state }}</span>
        <span v-if="ticket.not_a_fault" class="badge text-bg-info">Not a fault</span>
      </div>

      <!-- 1. The action bar: stacked on a phone; one row on a wider screen, the significant moves on the left -->
      <div class="action-bar d-grid gap-2 d-md-flex flex-md-wrap align-items-md-start mb-3">
        <button
          v-for="m in chainMoves"
          :key="m.name"
          type="button"
          class="btn btn-primary btn-lg"
          @click="moveDialog.open(m)"
        >
          {{ moveLabel(m.name, ticket.intensity) }}
        </button>
        <button v-if="showMachineStopped" type="button" class="btn btn-danger btn-lg" @click="regradeDialog.open('stopped')">
          <i class="fa-solid fa-circle-stop me-2"></i>Machine stopped
        </button>
        <button v-if="showChangeSeverity" type="button" class="btn btn-outline-primary btn-lg" @click="regradeDialog.open('change')">
          Change severity
        </button>
        <router-link v-if="ticket.can_raise_repeat" :to="repeatLink" class="btn btn-outline-primary btn-lg">
          Not fixed — raise again
        </router-link>
        <div v-if="significantMoves.length" class="significant d-grid gap-2 d-md-flex align-items-md-start order-md-first me-md-auto">
          <template v-for="m in significantMoves" :key="m.name">
            <div v-if="closeNeedsLabour(m)" class="d-grid gap-1">
              <div class="d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary btn-lg flex-grow-1" disabled>Close</button>
                <button v-if="canWork" type="button" class="btn btn-outline-primary btn-lg" @click="labourPanel.openAdd()">
                  Add labour
                </button>
              </div>
              <span class="small text-secondary">Add the labour first</span>
            </div>
            <button v-else type="button" class="btn btn-outline-dark btn-lg" @click="moveDialog.open(m)">
              {{ moveLabel(m.name, ticket.intensity) }}
            </button>
          </template>
        </div>
      </div>
      <div v-if="pickersError" class="alert alert-warning py-2">{{ pickersError }}</div>

      <!-- 2. Times, assignees, labour -->
      <div class="row g-3 mb-3">
        <div v-if="showTimes" class="col-md-4">
          <div class="card h-100">
            <div class="card-header">Times</div>
            <div class="card-body">
              <dl class="row mb-0">
                <dt class="col-7 fw-normal">Response</dt><dd class="col-5 mb-1">{{ minutesText(times.response_minutes) }}</dd>
                <dt class="col-7 fw-normal">Repair (hands on)</dt><dd class="col-5 mb-1">{{ minutesText(times.repair_minutes) }}</dd>
                <dt class="col-7 fw-normal">Downtime</dt><dd class="col-5 mb-0">{{ minutesText(times.downtime_minutes) }}</dd>
              </dl>
            </div>
          </div>
        </div>
        <div v-if="showAssignees" class="col-md-4">
          <div class="card h-100">
            <div class="card-header d-flex justify-content-between align-items-center">
              <span>Assigned</span>
              <button v-if="canAssign" class="btn btn-outline-primary" @click="assignDialog.open()">
                <i class="fa-solid fa-plus me-1"></i>Assign
              </button>
            </div>
            <div v-if="unassignError" class="alert alert-danger py-2 m-2">{{ unassignError }}</div>
            <div v-if="!ticket.assignees.length" class="card-body text-secondary">Nobody assigned</div>
            <ul v-else class="list-group list-group-flush">
              <li v-for="a in ticket.assignees" :key="a.id" class="list-group-item">
                <div class="d-flex align-items-center gap-2">
                  <span class="flex-grow-1 text-break">{{ a.name }}</span>
                  <button
                    v-if="canAssign && confirmingUnassignId !== a.id"
                    class="btn btn-outline-danger"
                    title="Unassign"
                    @click="confirmingUnassignId = a.id"
                  >
                    <i class="fa-solid fa-user-minus"></i>
                  </button>
                </div>
                <div v-if="canAssign && confirmingUnassignId === a.id" class="d-flex flex-wrap align-items-center justify-content-end gap-3 mt-2">
                  <span>Remove {{ a.name }}?</span>
                  <button class="btn btn-danger" :disabled="unassigning" @click="unassign(a)">Yes</button>
                  <button class="btn btn-outline-secondary" @click="confirmingUnassignId = null">No</button>
                </div>
              </li>
            </ul>
          </div>
        </div>
        <div v-if="showLabour" class="col-md-4">
          <LabourPanel
            ref="labourPanel"
            :ticket="ticket"
            :people="people"
            :own-person-id="userPersonId"
            :can-edit="canWork"
            @saved="onSaved"
          />
        </div>
      </div>

      <!-- 3. Repeats, details, description, photos and documents, timeline -->
      <div v-if="ticket.repeat_of || ticket.repeats.length" class="alert alert-light border">
        <div v-if="ticket.repeat_of">
          Repeat of <router-link :to="`/tickets/${ticket.repeat_of.id}`">{{ ticket.repeat_of.serial }}</router-link>
        </div>
        <div v-if="ticket.repeats.length">
          Came back as
          <template v-for="(r, i) in ticket.repeats" :key="r.id">
            <span v-if="i">, </span><router-link :to="`/tickets/${r.id}`">{{ r.serial }}</router-link>
          </template>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-lg-6">
          <div class="card h-100">
            <div class="card-header d-flex justify-content-between align-items-center">
              <span>Details</span>
              <button v-if="canWork" class="btn btn-outline-primary" @click="editDialog.open()">
                <i class="fa-solid fa-pen me-1"></i>Edit
              </button>
            </div>
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
                <template v-if="ticket.cause">
                  <dt class="col-5">Cause</dt><dd class="col-7">{{ ticket.cause.code }} {{ ticket.cause.label }}</dd>
                </template>
                <template v-if="ticket.action">
                  <dt class="col-5">Action</dt><dd class="col-7">{{ ticket.action.code }} {{ ticket.action.label }}</dd>
                </template>
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
                  <span v-if="intensityTexts[i]" class="text-secondary">· {{ intensityTexts[i] }}</span>
                  <span class="ms-auto small">{{ formatDateTime(e.occurred_at) }}</span>
                </div>
                <div class="small text-secondary">
                  {{ e.created_by }}<template v-if="e.person"> · {{ e.person.name }}</template>
                </div>
                <div v-if="e.remark" class="small text-break remark">{{ e.remark }}</div>
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

      <DocumentsCards
        :base-path="`/api/tickets/${ticket.id}/documents`"
        :can-edit="ticket.can_add_photos"
        :can-edit-documents="ticket.can_add_documents"
        large-add
      />

      <MoveDialog ref="moveDialog" :ticket="ticket" :people="people" :modes="modes" :own-person-id="userPersonId" @saved="onSaved" @reload="load" />
      <RegradeDialog ref="regradeDialog" :ticket="ticket" @saved="onSaved" @reload="load" />
      <AssignDialog ref="assignDialog" :ticket="ticket" :people="people" :own-person-id="userPersonId" @saved="onSaved" />
      <EditTicketDialog ref="editDialog" :ticket="ticket" :modes="modes" @saved="onSaved" />
    </template>
  </div>
</template>

<style scoped>
.description-text,
.remark {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.details dd {
  overflow-wrap: anywhere;
}
/* The significant moves stand apart from the chain buttons: a gap above them when stacked */
@media (max-width: 767.98px) {
  .significant {
    margin-top: 1rem;
  }
}
</style>
