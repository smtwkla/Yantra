<script setup>
/**
 * One PM job (docs/steps/S098-pm-job-phone/1-brief.md § 5.10; R03.4; mock-up docs/roadmap/R03-mockups/
 * 03-pm-job.html): the header, then by state
 * - due: the card *Start job* (Performed by, Started) for `can_start`, and the plan's items as they are now;
 * - in progress (`can_work`): Performed by (a change saves at once), Started, "3 of 7 filled", the items to fill
 *   (each saved as it is filled, one PUT per item), and *Mark job done* after them (D13: not a fixed bar);
 * - done, or a reader without pm_job:work: every item as text;
 * and the job's history in every state. The page holds no unsaved state but a typed value or remark, so there is
 * no route-leave guard. A save with no answer (no connection, or 5xx) says "Not saved. <what to do>" on its item;
 * the buttons keep the last saved choice and the input keeps what was typed.
 *
 * S099 § 5.8: a job waiting for verification shows, for a holder of pm_job:verify (`can_verify`), the card
 * *Verify* (*Send back*, *Verify job*, each through PmJobVerifyDialog), else "Waiting for an engineer to verify.";
 * a verified job says who verified it and when; a sent-back job shows the engineer's remark above the items.
 *
 * S101 § 5.7: a due job shows, for a holder of pm_job:verify (`can_reschedule`, `can_skip`), the card *Reschedule or
 * skip* (*Skip job*, *Reschedule job*, each through its dialog); a moved job says where it was moved from under its
 * due line; a skipped job says when, by whom and why; the history names the move's new due point.
 */
import { computed, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiGet, apiPost, apiPut } from "../api";
import { userPersonId } from "../stores/auth";
import { formatDateTime } from "../utils/datetime";
import {
  LIMIT_FLAG_LABELS, OUTCOME_BUTTONS, PM_EVENT_LABELS, REMARK_PROMPTS, RESULT_BADGES, RESULT_LABELS,
  SELF_VERIFIED_TEXT, daysPastText, dueText, filledText, jobBadges, jobSkippedText, limitFlag, movedFromText,
  notSavedText, personLabel, readingUnit, recordedByText, resultBody, resultText, sendBackBlockedText, sentBackText,
  verifiedText,
} from "../utils/pmLabels";
import PmJobDoneDialog from "./pm/PmJobDoneDialog.vue";
import PmJobRescheduleDialog from "./pm/PmJobRescheduleDialog.vue";
import PmJobSkipDialog from "./pm/PmJobSkipDialog.vue";
import PmJobVerifyDialog from "./pm/PmJobVerifyDialog.vue";
import EventFields from "./tickets/EventFields.vue";

const COUNTER_LOWER = "counter_lower"; // meters_core.COUNTER_LOWER: the refusal that offers the Meter reset tick

const route = useRoute();

const job = ref(null);
const people = ref([]); // the site's people, for Performed by (can_start / can_work only)
const loading = ref(true);
const loadError = ref("");
const notFound = ref(false);
const doneDialog = ref(null);
const verifyDialog = ref(null);
const sendBackDialog = ref(null);
const rescheduleDialog = ref(null);
const skipDialog = ref(null);
let loadSeq = 0;

// Start
const start = reactive({ performerId: null, startedAt: null, saving: false, error: null });
// Performed by, while in progress
const performer = reactive({ saving: false, saved: false, error: "" });
// Per item, by result id: {saving, saved, error, code, typed, remarkFor, remark, isReset, note}
const itemStates = reactive({});

const jobId = computed(() => Number(route.params.id));
const due = computed(() => job.value?.state === "due");
const working = computed(() => Boolean(job.value?.can_work));
const cancelled = computed(() => job.value?.state === "cancelled");
const allFilled = computed(() => job.value && job.value.filled_count === job.value.item_count);
const cancelRemark = computed(() => job.value?.events.findLast((e) => e.event === "cancelled")?.remark ?? "");
const dueLine = computed(() => {
  const j = job.value;
  const point = dueText(j.due_on, j.due_meter, j.meter?.meter_type);
  return [j.unit.full_code, point && `due ${point}${daysPastText(j.days_past)}`].filter(Boolean).join(" · ");
});

function stateOf(item) {
  if (!itemStates[item.id]) {
    itemStates[item.id] = { saving: null, saved: false, error: "", code: null, typed: null, remarkFor: null,
      remark: "", isReset: false, note: null };
  }
  return itemStates[item.id];
}

async function loadPeople(nodeId) {
  const answer = await apiGet(`/api/tickets/people?equipment_id=${nodeId}`);
  return answer.items;
}

async function load() {
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  notFound.value = false;
  try {
    const answer = await apiGet(`/api/pm/jobs/${jobId.value}`);
    const list = answer.can_start || answer.can_work ? await loadPeople(answer.equipment.id) : [];
    if (seq !== loadSeq) return;
    job.value = answer;
    people.value = list;
    start.performerId = list.some((p) => p.id === userPersonId.value) ? userPersonId.value : null;
    start.startedAt = null;
    start.error = null;
    for (const key of Object.keys(itemStates)) delete itemStates[key];
  } catch (err) {
    if (seq !== loadSeq) return;
    if (err.status === 404 || err.status === 403) notFound.value = true; // the API hides other units' jobs as 404
    else loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

watch(jobId, load, { immediate: true });

const startError = (field) => (start.error?.field === field ? start.error.message : "");
const startTopError = computed(() =>
  start.error && !["performed_by_id", "started_at"].includes(start.error.field) ? start.error.message : "");

async function startJob() {
  start.saving = true;
  start.error = null;
  try {
    job.value = await apiPost(`/api/pm/jobs/${jobId.value}/start`,
      { performed_by_id: start.performerId, started_at: start.startedAt });
  } catch (err) {
    start.error = { field: err.field, message: err.message };
    if (err.status === 409 && !err.field) await load(); // started by another person meanwhile: show it
  } finally {
    start.saving = false;
  }
}

async function changePerformer(event) {
  const id = Number(event.target.value);
  performer.saving = true;
  performer.saved = false;
  performer.error = "";
  try {
    job.value = await apiPut(`/api/pm/jobs/${jobId.value}`, { performed_by_id: id });
    performer.saved = true;
  } catch (err) {
    performer.error = err.status === 0 || err.status >= 500 ? notSavedText(err.message) : err.message;
    event.target.value = String(job.value.performed_by?.id ?? ""); // show the saved person, so a retry fires change
  } finally {
    performer.saving = false;
  }
}

async function saveItem(item, choice, control) {
  const s = stateOf(item);
  s.saving = control;
  s.saved = false;
  s.error = "";
  s.code = null;
  try {
    const answer = await apiPut(`/api/pm/jobs/${jobId.value}/results/${item.id}`, resultBody(item, choice));
    const index = job.value.items.findIndex((i) => i.id === item.id);
    job.value.items[index] = answer.item;
    job.value.filled_count = answer.filled_count;
    Object.assign(s, { saved: true, note: answer.meter_note, typed: null, remarkFor: null, remark: "",
      isReset: false });
  } catch (err) {
    if (err.status === 0 || err.status >= 500) s.error = notSavedText(err.message);
    else {
      s.error = err.message;
      s.code = err.code;
    }
  } finally {
    s.saving = null;
  }
}

/** A tap on an answer button: one that needs a remark opens the field, any other saves at once. */
function tapOutcome(item, outcome) {
  const s = stateOf(item);
  const asksRemark = outcome in REMARK_PROMPTS && (outcome !== "na" || item.item_type === "reading");
  if (asksRemark) {
    s.remarkFor = outcome;
    s.remark = item.outcome === outcome ? item.remark ?? "" : "";
    s.error = "";
    return;
  }
  s.remarkFor = null;
  saveItem(item, { outcome }, outcome);
}

const saveRemark = (item) => saveItem(item, { outcome: stateOf(item).remarkFor, remark: stateOf(item).remark },
  "remark");
const typedValue = (item) => stateOf(item).typed ?? item.value ?? "";
const saveValue = (item) => saveItem(item, { value: typedValue(item), isReset: stateOf(item).isReset }, "value");
// While typing, the flag comes from the item's limits; else the stored limit state
function flagOf(item) {
  const typed = stateOf(item).typed;
  return typed !== null ? limitFlag(typed, item.min_value, item.max_value) : item.limit_state;
}
const isMarked = (item) => ["not_ok", "not_done"].includes(item.outcome) || Boolean(item.limit_state);
const article = (name) => (/^[aeiou]/i.test(name) ? "an" : "a");
const loggedLine = (item) =>
  `Also logged as ${article(item.meter.meter_type.name)} ${item.meter.meter_type.name} reading of ${item.meter.code}.`;

function onDone(answer) {
  job.value = answer;
}

// S099: waiting for verification, and the reason Send back is off (the open job started, the machine scrapped)
const waitingForOther = computed(() => job.value?.awaits_verification && !job.value.can_verify);
const sendBackBlocked = computed(() => (job.value ? sendBackBlockedText(job.value) : ""));
const showSentBack = computed(() => job.value?.state === "in_progress" && job.value.sent_back);

// S101: a reschedule dropped by a schedule edit (D4) shows no line: the due point is the plan's again (BR1-02)
const movedFrom = computed(() => (job.value?.rescheduled && job.value.reschedule
  ? movedFromText(job.value.reschedule, job.value.meter?.meter_type) : ""));
const canMove = computed(() => Boolean(job.value?.can_reschedule || job.value?.can_skip));
/** A rescheduled line's new due point after its label: " to 15-11-2026"; "" for any other line. */
const movedTo = (e) => {
  if (e.event !== "rescheduled") return "";
  const point = dueText(e.due_on, e.due_meter, job.value.meter?.meter_type);
  return point ? ` to ${point}` : "";
};
</script>

<template>
  <div class="py-3 pm-job">
    <div v-if="notFound">
      <p>PM job not found, or not at your units.</p>
      <router-link to="/pm" class="btn btn-outline-secondary tap-target">Back to PM</router-link>
    </div>
    <div v-else-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center gap-2">
      <span>PM job could not be loaded: {{ loadError }}</span>
      <button type="button" class="btn btn-outline-danger" @click="load">Retry</button>
    </div>
    <div v-else-if="loading && !job" class="text-secondary">Loading…</div>
    <template v-else-if="job">
      <!-- Header -->
      <div class="mb-3">
        <div class="mb-1">
          <span v-for="b in jobBadges(job)" :key="b.label" class="badge me-1" :class="b.badge">{{ b.label }}</span>
        </div>
        <h1 class="h4 mb-1">{{ job.serial }}</h1>
        <div>
          <router-link :to="`/equipment/${job.equipment.id}`">{{ job.equipment.code }} — {{ job.equipment.name }}</router-link>
        </div>
        <div class="small text-secondary">
          <router-link :to="`/equipment/pm/${job.plan.id}`">{{ job.plan.title }}</router-link> · {{ dueLine }}
        </div>
        <div v-if="movedFrom" class="small text-secondary" data-testid="pm-moved-from">{{ movedFrom }}</div>
        <p v-if="waitingForOther" class="text-secondary mt-2 mb-0" data-testid="pm-waiting">
          Waiting for an engineer to verify.
        </p>
      </div>

      <!-- S099: sent back by an engineer -->
      <div v-if="showSentBack" class="alert alert-warning" data-testid="pm-sent-back">{{ sentBackText(job.sent_back) }}</div>

      <!-- Due: Start job -->
      <template v-if="due">
        <div v-if="job.can_start" class="card mb-3" data-testid="pm-start">
          <div class="card-header">Start job</div>
          <div class="card-body">
            <div v-if="startTopError" class="alert alert-danger py-2">{{ startTopError }}</div>
            <div class="mb-3">
              <label class="form-label" for="pm-start-performer">Performed by</label>
              <select
                id="pm-start-performer"
                v-model="start.performerId"
                class="form-select"
                :class="{ 'is-invalid': startError('performed_by_id') }"
              >
                <option :value="null" disabled>Choose a person</option>
                <option v-for="p in people" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
              </select>
              <div v-if="startError('performed_by_id')" class="invalid-feedback d-block">{{ startError("performed_by_id") }}</div>
              <div v-else-if="start.performerId === null" class="form-text">Choose who did the work.</div>
            </div>
            <EventFields
              v-model:time="start.startedAt"
              :with-remark="false"
              time-label="Started"
              id-prefix="pm-start"
              :time-error="startError('started_at')"
            />
            <button type="button" class="btn btn-primary w-100 big-button" :disabled="start.saving" @click="startJob">
              {{ start.saving ? "Starting…" : "Start job" }}
            </button>
          </div>
        </div>
        <p v-if="job.equipment.lifecycle === 'scrapped'" class="text-secondary">
          This machine is scrapped. The job cannot be started.
        </p>
        <p v-else-if="job.can_start" class="text-secondary">These are the plan's items now. Start the job to fill them.</p>
        <p v-else class="text-secondary">These are the plan's items now.</p>
      </template>

      <!-- Cancelled; S101: skipped -->
      <p v-if="cancelled && cancelRemark" class="text-secondary">{{ cancelRemark }}</p>
      <p v-if="job.skipped" class="text-secondary" data-testid="pm-skipped">{{ jobSkippedText(job.skipped) }}</p>

      <!-- In progress: who and when -->
      <div v-if="working" class="card mb-3" data-testid="pm-work">
        <div class="card-body">
          <div class="mb-2">
            <label class="form-label" for="pm-performer">Performed by</label>
            <select
              id="pm-performer"
              class="form-select"
              :value="job.performed_by?.id"
              :disabled="performer.saving"
              @change="changePerformer"
            >
              <option v-for="p in people" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
            </select>
            <div v-if="performer.error" class="invalid-feedback d-block">{{ performer.error }}</div>
            <div v-else-if="performer.saved" class="small text-success"><i class="fa-solid fa-check me-1"></i>Saved</div>
          </div>
          <div>Started {{ formatDateTime(job.started_at) }}</div>
        </div>
      </div>
      <div v-else-if="job.started_at" class="card mb-3" data-testid="pm-times">
        <div class="card-body">
          Performed by {{ job.performed_by?.name }} · Started {{ formatDateTime(job.started_at) }}<template
            v-if="job.done_at"> · Done {{ formatDateTime(job.done_at) }}</template>
          <div v-if="job.verification" class="mt-1" data-testid="pm-verified">{{ verifiedText(job.verification) }}</div>
          <div v-if="job.verification?.remark" class="small">{{ job.verification.remark }}</div>
        </div>
      </div>

      <!-- The items -->
      <div v-if="job.started_at" class="mb-2 fw-semibold" data-testid="pm-filled">
        {{ filledText(job.filled_count, job.item_count) }}
      </div>
      <ul v-if="job.items.length" class="list-group mb-3">
        <li
          v-for="item in job.items"
          :key="item.id ?? `template-${item.template_item_id}`"
          class="list-group-item pm-item"
          :class="{ 'list-group-item-danger': item.id && isMarked(item) }"
          :data-item="item.text"
        >
          <div>
            <span class="fw-semibold">{{ item.position }}. {{ item.text }}</span>
            <span v-if="item.limits_text" class="small text-secondary ms-1">{{ item.limits_text }}</span>
            <span
              v-if="item.item_type === 'reading' && flagOf(item)"
              class="badge text-bg-danger ms-1"
              data-testid="limit-flag"
            >{{ LIMIT_FLAG_LABELS[flagOf(item)] }}</span>
          </div>
          <div v-if="item.help_text" class="small text-secondary">{{ item.help_text }}</div>

          <!-- Filling -->
          <template v-if="working">
            <div v-if="item.item_type !== 'reading'" class="btn-group w-100 mt-2" role="group" :aria-label="item.text">
              <button
                v-for="[outcome, colour] in OUTCOME_BUTTONS[item.item_type]"
                :key="outcome"
                type="button"
                class="btn tap-target big-button"
                :class="item.outcome === outcome ? `btn-${colour}` : `btn-outline-${colour}`"
                :aria-pressed="item.outcome === outcome"
                :disabled="Boolean(stateOf(item).saving)"
                @click="tapOutcome(item, outcome)"
              >{{ stateOf(item).saving === outcome ? "Saving…" : RESULT_LABELS[outcome] }}</button>
            </div>
            <template v-else>
              <form class="mt-2" novalidate @submit.prevent="saveValue(item)">
                <div class="input-group">
                  <input
                    :id="`pm-value-${item.id}`"
                    class="form-control"
                    :class="{ 'border-danger': flagOf(item) }"
                    inputmode="decimal"
                    :aria-label="item.text"
                    :value="typedValue(item)"
                    :disabled="Boolean(stateOf(item).saving)"
                    @input="stateOf(item).typed = $event.target.value"
                  />
                  <span v-if="readingUnit(item)" class="input-group-text">{{ readingUnit(item) }}</span>
                  <button type="submit" class="btn btn-primary tap-target" :disabled="Boolean(stateOf(item).saving)">
                    {{ stateOf(item).saving === "value" ? "Saving…" : "Save" }}
                  </button>
                </div>
                <div v-if="stateOf(item).code === COUNTER_LOWER || stateOf(item).isReset" class="form-check mt-1">
                  <input :id="`pm-reset-${item.id}`" v-model="stateOf(item).isReset" class="form-check-input" type="checkbox" />
                  <label class="form-check-label" :for="`pm-reset-${item.id}`">Meter reset</label>
                </div>
              </form>
              <button
                type="button"
                class="btn tap-target big-button w-100 mt-2"
                :class="item.outcome === 'na' ? 'btn-secondary' : 'btn-outline-secondary'"
                :aria-pressed="item.outcome === 'na'"
                :disabled="Boolean(stateOf(item).saving)"
                @click="tapOutcome(item, 'na')"
              >NA</button>
            </template>
            <div v-if="stateOf(item).remarkFor" class="mt-2">
              <label class="form-label" :for="`pm-remark-${item.id}`">{{ REMARK_PROMPTS[stateOf(item).remarkFor] }}</label>
              <div class="input-group">
                <input
                  :id="`pm-remark-${item.id}`"
                  v-model="stateOf(item).remark"
                  class="form-control"
                  maxlength="500"
                  :disabled="Boolean(stateOf(item).saving)"
                />
                <button type="button" class="btn btn-primary tap-target" :disabled="Boolean(stateOf(item).saving)" @click="saveRemark(item)">
                  {{ stateOf(item).saving === "remark" ? "Saving…" : "Save" }}
                </button>
              </div>
            </div>
            <div v-if="item.remark && !stateOf(item).remarkFor" class="small mt-1">{{ item.remark }}</div>
            <div v-if="stateOf(item).error" class="invalid-feedback d-block">{{ stateOf(item).error }}</div>
            <div v-else-if="stateOf(item).saved" class="small text-success mt-1">
              <i class="fa-solid fa-check me-1"></i>Saved
            </div>
          </template>

          <!-- Read-only: a started job's result as text -->
          <template v-else-if="item.id">
            <div class="mt-1">
              <span v-if="item.outcome" class="badge" :class="RESULT_BADGES[item.outcome]">{{ resultText(item) }}</span>
              <span v-else-if="item.value != null">{{ resultText(item) }}</span>
              <span v-else class="text-secondary small">Not filled</span>
            </div>
            <div v-if="item.remark" class="small">{{ item.remark }}</div>
            <div v-if="item.filled_at" class="small text-secondary">
              Filled by {{ item.filled_by_name }}, {{ formatDateTime(item.filled_at) }}
            </div>
          </template>

          <div v-if="item.id && item.meter && (item.logged || stateOf(item).note)" class="small text-secondary mt-1">
            {{ stateOf(item).note ?? loggedLine(item) }}
          </div>
        </li>
      </ul>

      <!-- Mark job done: after the items, not fixed (D13) -->
      <div v-if="working" class="mb-3">
        <button
          type="button"
          class="btn btn-success w-100 big-button"
          :disabled="!allFilled"
          @click="doneDialog.open()"
        >Mark job done</button>
        <div v-if="!allFilled" class="small text-secondary mt-1">
          Fill all {{ job.item_count }} items first. Your entries are saved as you go.
        </div>
      </div>

      <!-- S101: Reschedule or skip, for a holder of pm_job:verify on a due job -->
      <div v-if="canMove" class="card mb-3" data-testid="pm-move">
        <div class="card-header">Reschedule or skip</div>
        <div class="card-body">
          <p>Not the right time for this job? Move it to a new date or meter value, or skip it. Both need a reason.</p>
          <div class="d-flex gap-2">
            <button
              v-if="job.can_skip"
              type="button"
              class="btn btn-outline-danger big-button flex-fill"
              @click="skipDialog.open()"
            >Skip job</button>
            <button
              v-if="job.can_reschedule"
              type="button"
              class="btn btn-outline-primary big-button flex-fill"
              @click="rescheduleDialog.open()"
            >Reschedule job</button>
          </div>
        </div>
      </div>

      <!-- S099: Verify, for a holder of pm_job:verify while the job waits -->
      <div v-if="job.can_verify" class="card mb-3" data-testid="pm-verify">
        <div class="card-header">Verify</div>
        <div class="card-body">
          <p>Check the results above. Verify the job, or send it back with what must be done again.</p>
          <div class="d-flex gap-2">
            <button
              type="button"
              class="btn btn-outline-danger big-button flex-fill"
              :disabled="!job.can_send_back"
              @click="sendBackDialog.open()"
            >Send back</button>
            <button type="button" class="btn btn-success big-button flex-fill" @click="verifyDialog.open()">
              Verify job
            </button>
          </div>
          <div v-if="sendBackBlocked" class="small text-secondary mt-2" data-testid="pm-send-back-blocked">
            {{ sendBackBlocked }}
          </div>
        </div>
      </div>

      <!-- History -->
      <div class="card mb-3" data-testid="pm-history">
        <div class="card-header">History</div>
        <ul class="list-group list-group-flush">
          <li v-for="(e, index) in job.events" :key="index" class="list-group-item">
            <span class="fw-semibold">{{ PM_EVENT_LABELS[e.event] ?? e.event }}{{ movedTo(e) }}</span>
            <span class="small text-secondary ms-2">{{ formatDateTime(e.occurred_at) }}</span>
            <span v-if="e.person" class="small ms-2">{{ e.person.name }}</span>
            <span v-if="e.self_verified" class="small ms-2">· {{ SELF_VERIFIED_TEXT }}</span>
            <span class="small text-secondary ms-2">{{ recordedByText(e) }}</span>
            <div v-if="e.remark" class="small">{{ e.remark }}</div>
          </li>
        </ul>
      </div>

      <PmJobDoneDialog v-if="working" ref="doneDialog" :job="job" @done="onDone" />
      <template v-if="job.can_verify">
        <PmJobVerifyDialog ref="verifyDialog" :job="job" mode="verify" @saved="onDone" @stale="load" />
        <PmJobVerifyDialog ref="sendBackDialog" :job="job" mode="send_back" @saved="onDone" @stale="load" />
      </template>
      <template v-if="canMove">
        <PmJobRescheduleDialog ref="rescheduleDialog" :job="job" @saved="onDone" @stale="load" />
        <PmJobSkipDialog ref="skipDialog" :job="job" @saved="onDone" @stale="load" />
      </template>
    </template>
  </div>
</template>

<style scoped>
.pm-job {
  overflow-wrap: anywhere;
}
.big-button {
  min-height: 48px;
}
</style>
