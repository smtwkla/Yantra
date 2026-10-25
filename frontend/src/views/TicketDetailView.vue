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
 * 2. repeats; then details (half), times and assignees (a quarter each); then the meters as they
 *    stood when it happened (S052, full width, only when the machine or the part has meters);
 *    then parts used (S020,
 *    full width, in columns when long); then the timeline (full width, newest first; the newest 10,
 *    *Show all* expands it in place). Times, assignees, parts and labour show to
 *    ticket:work holders, or when not empty;
 *    Edit and Assign sit with their cards. Stacked on a phone;
 * 3. photos and documents, then labour.
 *
 * Every control follows the detail's `moves`, `permissions` (the keys at the ticket's site)
 * and `regrade_to`, so a user never sees a button that ends in a 403. Each write answers with
 * the ticket's detail, which replaces the page's copy.
 *
 * S019 (deferred work): the state badge reads Deferred, Waiting (a scheduled breakdown) or
 * Overdue, with the plan on a line under the header ("check by" or "for", by reason, S034);
 * Defer / Put on hold and Change plan sit in outline
 * beside Change severity; the times card adds the waiting split and the planned stop; the
 * timeline shows each plan, a change with "(was …)".
 *
 * S020 (parts used): the Parts used panel beside Labour; Not a fault is disabled with "Remove the
 * parts first" while the ticket has part lines (the API refuses it too, 409).
 *
 * S027 (work notes): *Add note* in outline in the action bar, after the next move, for
 * ticket:restore holders while open. A note is a timeline line with its text in the normal size;
 * the raise's *What is wrong?* (the description) shows on the Raised line in the same style, as
 * the first note, so there is no Description card. ticket:edit_notes holders get a pencil on each
 * note; a corrected note shows "Edited by …" and *Show earlier text*.
 */
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiDelete, apiGet } from "../api";
import IntensityBadge from "../components/IntensityBadge.vue";
import DocumentsCards from "../components/documents/DocumentsCards.vue";
import { useShowMore } from "../composables/useShowMore";
import { userPersonId } from "../stores/auth";
import { formatDateTime } from "../utils/datetime";
import {
  ageText, EVENT_LABELS, intensityChanges, minutesText, moveLabel, PLAN_MOVES, planChanges, planLine, SIGNIFICANT_MOVES,
  stateLabel, ticketTint, waitingSplit,
} from "../utils/ticketLabels";
import AssignDialog from "./tickets/AssignDialog.vue";
import EditTicketDialog from "./tickets/EditTicketDialog.vue";
import LabourPanel from "./tickets/LabourPanel.vue";
import MoveDialog from "./tickets/MoveDialog.vue";
import NoteDialog from "./tickets/NoteDialog.vue";
import PartsPanel from "./tickets/PartsPanel.vue";
import RegradeDialog from "./tickets/RegradeDialog.vue";
import TicketMetersCard from "./tickets/TicketMetersCard.vue";

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
const noteDialog = ref(null);
const shownEarlier = ref(new Set()); // the notes whose earlier texts are open
const labourPanel = ref(null);
const confirmingUnassignId = ref(null);
const unassigning = ref(false);
const unassignError = ref("");

const can = (key) => (ticket.value?.permissions ?? []).includes(key);
const isOpen = computed(() => ticket.value && ticket.value.state !== "closed");
const canWork = computed(() => isOpen.value && can("ticket:work"));
const canAssign = computed(() => isOpen.value && can("ticket:assign"));
// S027: whoever may confirm the machine is back may write what they see; correcting is narrower
const canAddNote = computed(() => isOpen.value && can("ticket:restore"));
const canEditNotes = computed(() => isOpen.value && can("ticket:edit_notes"));
const chainMoves = computed(() => (ticket.value?.moves ?? [])
  .filter((m) => !SIGNIFICANT_MOVES.includes(m.name) && !PLAN_MOVES.includes(m.name)));
const planMoves = computed(() => (ticket.value?.moves ?? []).filter((m) => PLAN_MOVES.includes(m.name)));
const significantMoves = computed(() => (ticket.value?.moves ?? []).filter((m) => SIGNIFICANT_MOVES.includes(m.name)));
const closeNeedsLabour = (m) => m.name === "close" && ticket.value.labour.length === 0;
// A ticket with parts was a fault (S020 § 1.5): Not a fault waits until they are removed
const notAFaultHasParts = (m) => m.name === "not-a-fault" && ticket.value.parts.length > 0;
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
const showParts = computed(() => can("ticket:work") || ticket.value?.parts.length > 0);
const intensityTexts = computed(() => intensityChanges(ticket.value?.events ?? []));
const planTexts = computed(() => planChanges(ticket.value?.events ?? []));
// The API sends the events oldest first, as the intensity and plan texts read each against the
// one before; the timeline shows them newest first, each keeping its index into those texts
const timelineRows = computed(() => (ticket.value?.events ?? []).map((e, i) => ({ e, i })).reverse());
const timelineMore = useShowMore(() => timelineRows.value);
const waiting = computed(() => waitingSplit(times.value.waiting_by_reason));

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

function toggleEarlier(note) {
  const shown = new Set(shownEarlier.value);
  if (shown.has(note.id)) shown.delete(note.id);
  else shown.add(note.id);
  shownEarlier.value = shown;
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
      <div
        data-testid="ticket-title"
        class="d-flex flex-wrap align-items-center gap-2 mb-3"
        :class="ticketTint(ticket) && `bg-${ticketTint(ticket)}-subtle border border-${ticketTint(ticket)}-subtle rounded px-2 py-1`"
      >
        <h4 class="mb-0 me-2">{{ ticket.serial }}</h4>
        <IntensityBadge :intensity="ticket.intensity" />
        <span class="badge state-badge" :class="ticket.overdue ? 'text-bg-danger' : 'text-bg-light border'">{{ stateLabel(ticket) }}</span>
        <span v-if="ticket.not_a_fault" class="badge text-bg-info">Not a fault</span>
      </div>
      <p v-if="planLine(ticket)" class="plan-line mb-3" :class="ticket.overdue ? 'text-danger fw-semibold' : 'text-secondary'">
        <i class="fa-regular fa-calendar me-1"></i>{{ planLine(ticket) }}
      </p>

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
        <button v-if="canAddNote" type="button" class="btn btn-outline-primary btn-lg" @click="noteDialog.openAdd()">
          <i class="fa-regular fa-comment me-2"></i>Add note
        </button>
        <button v-if="showChangeSeverity" type="button" class="btn btn-outline-primary btn-lg" @click="regradeDialog.open('change')">
          Change severity
        </button>
        <button
          v-for="m in planMoves"
          :key="m.name"
          type="button"
          class="btn btn-outline-primary btn-lg"
          @click="moveDialog.open(m)"
        >
          <i class="fa-regular fa-calendar me-2"></i>{{ moveLabel(m.name, ticket.intensity) }}
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
            <div v-else-if="notAFaultHasParts(m)" class="d-grid gap-1">
              <button type="button" class="btn btn-outline-secondary btn-lg" disabled>
                {{ moveLabel(m.name, ticket.intensity) }}
              </button>
              <span class="small text-secondary">Remove the parts first</span>
            </div>
            <button v-else type="button" class="btn btn-outline-dark btn-lg" @click="moveDialog.open(m)">
              {{ moveLabel(m.name, ticket.intensity) }}
            </button>
          </template>
        </div>
      </div>
      <div v-if="pickersError" class="alert alert-warning py-2">{{ pickersError }}</div>

      <!-- 2. Repeats; details, times and assignees; parts used; the timeline (labour comes after the documents) -->
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

      <div class="row g-3 mb-3">
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
        <div v-if="showTimes" class="col-md-6 col-lg-3">
          <div class="card h-100">
            <div class="card-header">Times</div>
            <div class="card-body">
              <dl class="row mb-0">
                <dt class="col-7 fw-normal">Response</dt><dd class="col-5 mb-1">{{ minutesText(times.response_minutes) }}</dd>
                <dt class="col-7 fw-normal">Repair (hands on)</dt><dd class="col-5 mb-1">{{ minutesText(times.repair_minutes) }}</dd>
                <dt class="col-7 fw-normal">Downtime</dt><dd class="col-5 mb-0">{{ minutesText(times.downtime_minutes) }}</dd>
                <!-- S019: the waiting inside the downtime, per reason, then EN 13306's two delays -->
                <template v-if="times.waiting_minutes !== null && times.waiting_minutes !== undefined">
                  <dt class="col-7 fw-normal ps-4">of which waiting</dt><dd class="col-5 mb-0">{{ minutesText(times.waiting_minutes) }}</dd>
                  <template v-for="r in waiting.reasons" :key="r.reason">
                    <dt class="col-7 fw-normal ps-5 small text-secondary">{{ r.label }}</dt>
                    <dd class="col-5 mb-0 small text-secondary">{{ minutesText(r.minutes) }}</dd>
                  </template>
                  <template v-if="waiting.logistic !== null">
                    <dt class="col-7 fw-normal ps-5 small text-secondary">Logistic delay</dt>
                    <dd class="col-5 mb-0 small text-secondary">{{ minutesText(waiting.logistic) }}</dd>
                  </template>
                  <template v-if="waiting.administrative !== null">
                    <dt class="col-7 fw-normal ps-5 small text-secondary">Administrative delay</dt>
                    <dd class="col-5 mb-0 small text-secondary">{{ minutesText(waiting.administrative) }}</dd>
                  </template>
                </template>
                <template v-if="times.planned_downtime_minutes !== null && times.planned_downtime_minutes !== undefined">
                  <dt class="col-7 fw-normal mt-1">Planned stop</dt><dd class="col-5 mb-0 mt-1">{{ minutesText(times.planned_downtime_minutes) }}</dd>
                </template>
              </dl>
            </div>
          </div>
        </div>
        <div v-if="showAssignees" class="col-md-6 col-lg-3">
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
      </div>

      <!-- S052: the meters as they stood when it happened; draws nothing while loading or without meters -->
      <TicketMetersCard :ticket="ticket" />

      <!-- Full width: an overhaul can use 100 parts or more, in columns (PartsPanel) -->
      <div v-if="showParts" class="mb-3">
        <PartsPanel :ticket="ticket" :can-edit="canWork" @saved="onSaved" />
      </div>

      <div class="row g-3">
        <div class="col-12">
          <div class="card">
            <div class="card-header">Timeline</div>
            <ul class="list-group list-group-flush">
              <li v-for="{ e, i } in timelineMore.shown.value" :key="i" class="list-group-item">
                <div class="d-flex flex-wrap align-items-center gap-2">
                  <!-- S027: a note names its writer in the title, so it has no separate user line -->
                  <span class="fw-semibold">
                    {{ EVENT_LABELS[e.event] ?? e.event }}<template v-if="e.event === 'note'"> by {{ e.created_by }}</template>
                  </span>
                  <span v-if="intensityTexts[i]" class="text-secondary">· {{ intensityTexts[i] }}</span>
                  <span class="ms-auto small">{{ formatDateTime(e.occurred_at) }}</span>
                  <button
                    v-if="e.event === 'note' && canEditNotes"
                    type="button"
                    class="btn btn-sm btn-outline-secondary py-0"
                    title="Edit note"
                    aria-label="Edit note"
                    @click="noteDialog.openEdit(e)"
                  >
                    <i class="fa-solid fa-pen fa-xs"></i>
                  </button>
                </div>
                <div v-if="planTexts[i]" class="small text-break">{{ planTexts[i] }}</div>
                <div v-if="e.machine_stopped !== null && e.machine_stopped !== undefined" class="small">
                  {{ e.machine_stopped ? "Machine stopped for this work" : "Machine kept running" }}
                </div>
                <div v-if="e.event !== 'note'" class="small text-secondary">
                  {{ e.created_by }}<template v-if="e.person"> · {{ e.person.name }}</template>
                </div>
                <!-- S027: a note's text is the content of its line, so the normal size; the
                     raise's *What is wrong?* is the first note -->
                <div v-if="e.event === 'raised' && ticket.description" class="note-text">{{ ticket.description }}</div>
                <template v-if="e.event === 'note'">
                  <div class="note-text">{{ e.remark }}</div>
                  <div v-if="e.updated_by" class="small text-secondary">
                    Edited by {{ e.updated_by }}, {{ formatDateTime(e.updated_at) }}
                  </div>
                  <template v-if="e.earlier?.length">
                    <button type="button" class="btn btn-link px-0" @click="toggleEarlier(e)">
                      {{ shownEarlier.has(e.id) ? "Hide earlier text" : "Show earlier text" }}
                    </button>
                    <!-- divs, not a nested list: the timeline's entries are its li elements -->
                    <div v-if="shownEarlier.has(e.id)" class="earlier border-start ps-2 mt-1">
                      <div v-for="(old, j) in e.earlier" :key="j" class="mb-1">
                        <div class="small note-text">{{ old.remark }}</div>
                        <div class="small text-secondary">Replaced by {{ old.replaced_by }}, {{ formatDateTime(old.replaced_at) }}</div>
                      </div>
                    </div>
                  </template>
                </template>
                <div v-else-if="e.remark" class="small text-break remark">{{ e.remark }}</div>
              </li>
            </ul>
            <div v-if="timelineMore.canExpand.value" class="card-footer">
              <button type="button" class="btn btn-link px-0" @click="timelineMore.toggle">
                {{ timelineMore.toggleLabel.value }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <DocumentsCards
        :base-path="`/api/tickets/${ticket.id}/documents`"
        :can-edit="ticket.can_add_photos"
        :can-edit-documents="ticket.can_add_documents"
        large-add
      />

      <div v-if="showLabour" class="mt-3">
        <LabourPanel
          ref="labourPanel"
          :ticket="ticket"
          :people="people"
          :own-person-id="userPersonId"
          :can-edit="canWork"
          @saved="onSaved"
        />
      </div>

      <MoveDialog ref="moveDialog" :ticket="ticket" :people="people" :modes="modes" :own-person-id="userPersonId" @saved="onSaved" @reload="load" />
      <RegradeDialog ref="regradeDialog" :ticket="ticket" @saved="onSaved" @reload="load" />
      <AssignDialog ref="assignDialog" :ticket="ticket" :people="people" :own-person-id="userPersonId" @saved="onSaved" />
      <EditTicketDialog ref="editDialog" :ticket="ticket" :modes="modes" @saved="onSaved" />
      <NoteDialog ref="noteDialog" :ticket="ticket" @saved="onSaved" @reload="load" />
    </template>
  </div>
</template>

<style scoped>
/* pre-wrap: shown as entered, line breaks kept */
.note-text,
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
