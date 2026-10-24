<script setup>
/**
 * The end-of-day readings sheet (docs/steps/S040-readings-sheet/1-brief.md): every meter in force
 * at one site, grouped by unit, entered on one screen.
 * - The site: no picker for a user who logs at one site; otherwise a picker, the last choice
 *   remembered in this browser (yantra.readings.site_id, in try/catch).
 * - One card per machine; a part with meters is a titled block inside its machine's card.
 *   Out-of-use machines sit behind "Show out of use" at the end of each unit.
 * - Save readings posts each filled row in turn with S039's POST (one transaction per row). A
 *   refusal shows on its row and the loop goes on; a server or network failure stops the loop
 *   and the rest read "Not saved" with their values kept. A saved row is read-only; Undo (S039's
 *   remove route) shows only for equipment:edit holders at the row's unit.
 * - After a full save the round is read-only and "Enter more readings" starts a new one (A1).
 * - The rules are the server's (S039): this screen only collects, posts and shows.
 *
 * Time taken is one field for the sheet ("Now" sends no taken_at, so the server's clock decides).
 */
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { apiDelete, apiGet, apiPost } from "../api";
import { ensureMyUnits, myUnits, noUnits, readingSites } from "../stores/equipment";
import { ensureSites, ensureUnits, sites, units } from "../stores/masters";
import { LIFECYCLE_LABELS } from "../utils/equipmentLabels";
import { isToday, isUnavailable, NOT_SAVED, notSavedOr, savedMessage } from "../utils/meterLabels";
import EventFields from "./tickets/EventFields.vue";
import ReadingSheetRow from "./readings/ReadingSheetRow.vue";

const SITE_KEY = "yantra.readings.site_id";
const LOAD_FAILED = "Readings could not be loaded. Try again in a minute.";
const SITE_GONE = "This site is no longer available. Pick another site.";
// A refused Time taken is the sheet's, so every row would get the same answer: the loop stops
const TIME_NOT_SAVED = "Not saved. Change Time taken, then save again.";
const UNDO_FAILED = "The reading was not removed. Try again in a minute.";
const OUT_OF_USE = "out_of_use";

const ready = ref(false); // the masters' lists and my-units are loaded
const siteId = ref(null);
const goneSites = ref(new Set()); // sites the server answered 404 for
const siteGone = ref(false);
const sheet = ref(null); // the API's {site, units}
const loading = ref(false);
const loadError = ref("");
const now = ref(new Date());
const takenAt = ref(null); // null = now: the server's clock
const timeError = ref("");
const saving = ref(false);
const wantedSite = ref(null); // a site picked while typed readings exist, waiting for the answer
const pickerKey = ref(0); // bumped to put the <select> back on the current site
const root = ref(null);
const states = reactive({}); // row key -> the row's state
const unfolded = ref(new Set()); // units whose out-of-use machines are shown
let loadSeq = 0;

const siteChoices = computed(() => {
  if (!ready.value) return [];
  return readingSites(units.value, sites.value, myUnits.value).filter((s) => !goneSites.value.has(s.id));
});
const showPicker = computed(() => siteChoices.value.length > 1 || (siteGone.value && siteChoices.value.length > 0));
// No site left, also after a 404 (BR2-07): the same message as a user with no unit
const nothingToShow = computed(() => ready.value && (noUnits.value || siteChoices.value.length === 0));

// ---- the rows ---------------------------------------------------------------------------------

const rowKey = (nodeId, meter) => `${nodeId}-${meter.meter_type.id}`;
const blankState = () => ({
  value: "", is_reset: false, showReset: false, phase: "idle", message: "", notOk: false, reading: null, error: "",
  undoing: false,
});

/** Every meter row of the sheet in screen order: {key, nodeId, unitId, meter}. */
const rows = computed(() => {
  const out = [];
  for (const unit of sheet.value?.units ?? []) {
    for (const machine of unit.machines) {
      for (const node of [machine, ...machine.parts]) {
        for (const meter of node.meters) out.push({ key: rowKey(node.id, meter), nodeId: node.id, unitId: unit.id, meter });
      }
    }
  }
  return out;
});
const stateOf = (key) => states[key];

function resetStates() {
  for (const key of Object.keys(states)) delete states[key];
  for (const row of rows.value) states[row.key] = blankState();
  unfolded.value = new Set();
}

const isFilled = (state) => String(state.value ?? "").trim() !== "";
const filled = computed(() => rows.value.filter((r) => isFilled(states[r.key])).length);
const pending = computed(() => rows.value.filter((r) => isFilled(states[r.key]) && states[r.key].phase !== "saved").length);
// A saved round with no row left to retry is read-only; Enter more readings starts the next (A1).
// Undo of a saved row makes it a pending row again, which opens the round.
const roundDone = computed(() => !saving.value && pending.value === 0 && rows.value.some((r) => states[r.key].phase === "saved"));
// A row saved this session counts too, by the time it was taken
const readToday = computed(() => rows.value.filter((r) => {
  const state = states[r.key];
  return isToday(state.phase === "saved" ? state.reading.taken_at : r.meter.last?.taken_at, now.value);
}).length);

// Undo is for equipment:edit holders at the unit (my-units' edit_unit_ids; null = every unit)
const canUndoAt = (unitId) => myUnits.value?.edit_unit_ids === null || !!myUnits.value?.edit_unit_ids.includes(unitId);
// One line for the whole sheet, once a row without Undo has been saved (BR2-03)
const askEngineer = computed(() => rows.value.some((r) => states[r.key].phase === "saved" && !canUndoAt(r.unitId)));

const visibleMachines = (unit) => unit.machines.filter((m) => m.lifecycle !== OUT_OF_USE);
const idleMachines = (unit) => unit.machines.filter((m) => m.lifecycle === OUT_OF_USE);
function toggleUnfolded(unitId) {
  const next = new Set(unfolded.value);
  if (!next.delete(unitId)) next.add(unitId);
  unfolded.value = next;
}

// ---- the site ---------------------------------------------------------------------------------

function remembered() {
  try {
    return Number(localStorage.getItem(SITE_KEY)) || null;
  } catch {
    return null; // a private window: no memory
  }
}

function remember(id) {
  try {
    if (id === null) localStorage.removeItem(SITE_KEY);
    else localStorage.setItem(SITE_KEY, String(id));
  } catch {
    // no storage: the first site is chosen next time
  }
}

async function loadSheet(id) {
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const result = await apiGet(`/api/readings/sheet?site_id=${id}`);
    if (seq !== loadSeq) return;
    sheet.value = result;
    now.value = new Date();
    resetStates();
    siteGone.value = false;
    remember(id);
  } catch (err) {
    if (seq !== loadSeq) return;
    sheet.value = null;
    if (err.status === 404) {
      // Access changed, or the site was deactivated after the lists were cached (BR2-07)
      remember(null);
      goneSites.value = new Set([...goneSites.value, id]);
      siteGone.value = true;
      siteId.value = null;
    } else {
      loadError.value = LOAD_FAILED;
    }
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

watch(siteId, (id) => {
  if (id !== null) loadSheet(id);
});

// The picker: a site picked while readings are typed and not saved asks first (no lost input, S007)
const pickedSite = computed({
  get: () => siteId.value,
  set(id) {
    if (id === siteId.value) return;
    if (pending.value > 0) {
      wantedSite.value = id;
      pickerKey.value += 1; // the <select> shows the current site until the user answers
    } else {
      siteId.value = id;
    }
  },
});

// The user cleared the typed rows while the question waits: nothing is left to discard (CR2-02)
watch(pending, (count) => {
  if (count === 0) wantedSite.value = null;
});

function discardAndSwitch() {
  const id = wantedSite.value;
  wantedSite.value = null;
  siteId.value = id;
}

function retry() {
  if (siteId.value !== null) loadSheet(siteId.value);
  else init();
}

async function init() {
  loadError.value = "";
  try {
    await Promise.all([ensureSites(), ensureUnits(), ensureMyUnits()]);
  } catch {
    loadError.value = LOAD_FAILED;
    return;
  }
  ready.value = true;
  const choices = siteChoices.value;
  // A remembered site no longer offered falls back to the first (BR1-14)
  siteId.value = (choices.find((s) => s.id === remembered()) ?? choices[0])?.id ?? null;
}

onMounted(init);

// ---- saving -----------------------------------------------------------------------------------

function requestBody(row, state) {
  const body = { meter_type_id: row.meter.meter_type.id, value: String(state.value).trim() };
  if (row.meter.meter_type.kind === "counter") body.is_reset = state.is_reset;
  if (takenAt.value) body.taken_at = takenAt.value;
  return body;
}

function markSaved(row, state, reading) {
  state.phase = "saved";
  state.reading = reading;
  state.error = "";
  const warning = savedMessage(row.meter, reading);
  state.message = warning ?? "Saved";
  state.notOk = warning !== null;
}

function markRefused(state, err) {
  state.error = err.message;
  // Only this refusal offers the reset tick; its text already tells the user to tick it (BR1-02)
  if (err.code === "counter_lower") state.showReset = true;
}

async function saveAll() {
  saving.value = true;
  wantedSite.value = null;
  timeError.value = "";
  now.value = new Date(); // a sheet left open past midnight counts today's readings (CR1-08)
  let stopped = false;
  let notSaved = NOT_SAVED; // what the rows after a stop read
  try {
    // The value posted is the one at the row's turn (BR1-10)
    for (const row of rows.value) {
      const state = states[row.key];
      if (state.phase === "saved" || !isFilled(state)) continue;
      if (stopped) {
        state.error = notSaved;
        continue;
      }
      state.error = "";
      try {
        markSaved(row, state, await apiPost(`/api/equipment/${row.nodeId}/readings`, requestBody(row, state)));
      } catch (err) {
        if (isUnavailable(err)) {
          // The server or the network is down: stop, so no row after it is tried (BS1-02)
          stopped = true;
          state.error = notSavedOr(err).message;
        } else if (err.status === 400 && err.field === "taken_at") {
          // Shown once, on the shared field, not on every row
          stopped = true;
          notSaved = TIME_NOT_SAVED;
          timeError.value = err.message;
          state.error = TIME_NOT_SAVED;
        } else {
          markRefused(state, err);
        }
      }
    }
  } finally {
    saving.value = false;
  }
  // A refusal is always in view (S026): the first one may be rows above the Save button
  await nextTick();
  const target = timeError.value ? root.value?.querySelector(".invalid-feedback") : root.value?.querySelector('[role="alert"]');
  target?.scrollIntoView({ block: "center" });
}

/** A new round: every row empty, Time taken back to now, the last readings reloaded (A1). */
function enterMore() {
  takenAt.value = null;
  timeError.value = "";
  loadSheet(siteId.value);
}

async function undo(row) {
  const state = states[row.key];
  state.undoing = true;
  state.error = "";
  try {
    await apiDelete(`/api/equipment/${row.nodeId}/readings/${state.reading.id}`);
    // Editable again, the value kept (§ 1.6)
    state.phase = "idle";
    state.reading = null;
    state.message = "";
    state.notOk = false;
  } catch (err) {
    state.error = isUnavailable(err) ? UNDO_FAILED : err.message;
  } finally {
    state.undoing = false;
  }
}
</script>

<template>
  <div ref="root" class="py-3 readings-sheet">
    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger" @click="retry">Try again</button>
    </div>

    <div v-else-if="!ready" class="text-secondary">Loading…</div>
    <div v-else-if="nothingToShow" class="text-secondary">You have no units assigned — ask IT admin for unit access.</div>

    <template v-else>
      <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
        <select v-if="showPicker" :key="pickerKey" v-model="pickedSite" class="form-select w-auto" aria-label="Site" :disabled="saving">
          <option :value="null" disabled>Pick a site</option>
          <option v-for="s in siteChoices" :key="s.id" :value="s.id">{{ s.code }}</option>
        </select>
        <h2 v-if="sheet" class="h5 mb-0" data-testid="sheet-heading">{{ sheet.site.code }} — {{ sheet.site.name }}</h2>
      </div>
      <div v-if="wantedSite !== null && pending > 0" class="alert alert-warning d-flex flex-wrap align-items-center gap-2" role="alert" data-testid="discard-confirm">
        <span class="flex-grow-1">Discard {{ pending }} typed {{ pending === 1 ? "reading" : "readings" }}? Switching site removes them. You cannot undo this.</span>
        <button type="button" class="btn btn-primary" @click="wantedSite = null">Keep editing</button>
        <button type="button" class="btn btn-outline-danger" @click="discardAndSwitch">Discard</button>
      </div>
      <div v-if="siteGone" class="alert alert-warning" role="alert">{{ SITE_GONE }}</div>
      <div v-if="loading && !sheet" class="text-secondary">Loading…</div>

      <template v-if="sheet && sheet.units.length === 0">
        <p class="text-secondary">
          No machine at this site has meters. Engineers add meters in Masters › Models or on a machine's page.
        </p>
      </template>

      <template v-else-if="sheet">
        <div class="card mb-3">
          <div class="card-body pb-1">
            <EventFields v-model:time="takenAt" :with-remark="false" time-label="Time taken" :time-error="timeError" :locked="roundDone" id-prefix="sheet" />
          </div>
        </div>
        <div class="small text-secondary mb-2" data-testid="read-today-count">{{ readToday }} of {{ rows.length }} read today</div>

        <section v-for="unit in sheet.units" :key="unit.id" class="mb-3" data-testid="sheet-unit">
          <h3 class="unit-heading h6 mb-2 py-2">{{ unit.code }} · {{ unit.name }}</h3>
          <template v-for="machine in [...visibleMachines(unit), ...(unfolded.has(unit.id) ? idleMachines(unit) : [])]" :key="machine.id">
            <div class="card mb-2" data-testid="sheet-machine">
              <div class="card-header d-flex flex-wrap align-items-baseline gap-2">
                <span class="fw-semibold">{{ machine.code }} — {{ machine.name }}</span>
                <span v-if="machine.lifecycle !== 'in_service'" class="badge text-bg-light border">{{ LIFECYCLE_LABELS[machine.lifecycle] }}</span>
              </div>
              <ul v-if="machine.meters.length" class="list-group list-group-flush">
                <ReadingSheetRow
                  v-for="meter in machine.meters"
                  :key="meter.meter_type.id"
                  :meter="meter"
                  :state="stateOf(rowKey(machine.id, meter))"
                  :can-undo="canUndoAt(unit.id)"
                  :busy="saving"
                  :locked="roundDone"
                  :now="now"
                  :id-prefix="`sheet-${rowKey(machine.id, meter)}`"
                  @undo="undo({ key: rowKey(machine.id, meter), nodeId: machine.id })"
                />
              </ul>
              <template v-for="part in machine.parts" :key="part.id">
                <h4 class="part-title h6 mb-0 px-3 py-2 border-top bg-body-tertiary">{{ part.name }}</h4>
                <ul class="list-group list-group-flush">
                  <ReadingSheetRow
                    v-for="meter in part.meters"
                    :key="meter.meter_type.id"
                    :meter="meter"
                    :state="stateOf(rowKey(part.id, meter))"
                    :can-undo="canUndoAt(unit.id)"
                    :busy="saving"
                    :locked="roundDone"
                    :now="now"
                    :id-prefix="`sheet-${rowKey(part.id, meter)}`"
                    @undo="undo({ key: rowKey(part.id, meter), nodeId: part.id })"
                  />
                </ul>
              </template>
            </div>
          </template>
          <button v-if="idleMachines(unit).length" type="button" class="btn btn-link show-idle" @click="toggleUnfolded(unit.id)">
            {{ unfolded.has(unit.id) ? "Hide out of use" : `Show out of use (${idleMachines(unit).length})` }}
          </button>
        </section>

        <div class="save-bar" data-testid="save-bar">
          <div class="d-flex align-items-center gap-3">
            <span class="small text-secondary flex-grow-1" data-testid="filled-count">{{ filled }} of {{ rows.length }} filled</span>
            <button v-if="roundDone" type="button" class="btn btn-primary" disabled>Saved</button>
            <button v-else type="button" class="btn btn-primary" :disabled="saving || pending === 0" @click="saveAll">Save readings</button>
            <button v-if="roundDone" type="button" class="btn btn-primary enter-more" :disabled="loading" @click="enterMore">Enter more readings</button>
          </div>
          <div v-if="askEngineer" class="small text-secondary mt-1">A wrong reading is removed by an engineer. Ask one.</div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
/* The unit's heading stays in view while its rows scroll (BR2-09) */
.unit-heading {
  position: sticky;
  top: 0;
  z-index: 2;
  background-color: var(--bs-body-bg);
  border-bottom: 1px solid var(--bs-border-color);
}

/* A tap target of at least 44 px on a floor screen (CR1-09) */
.show-idle {
  min-height: 44px;
}

/* A tap target of at least 44 px (A1) */
.enter-more {
  min-height: 44px;
}

/* On a phone the bar sits at the bottom of the scrolling main, above the fixed bottom nav (BR1-04) */
.save-bar {
  padding: 0.5rem 0;
}

@media (max-width: 576px) {
  .save-bar {
    position: sticky;
    bottom: 0;
    z-index: 3;
    background-color: var(--bs-body-bg);
    border-top: 1px solid var(--bs-border-color);
    padding: 0.5rem 1.5rem;
    margin: 0 -1.5rem;
  }
}
</style>
