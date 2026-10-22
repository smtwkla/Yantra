<script setup>
/**
 * Raise a ticket — phone first (docs/steps/S017-raise-tickets/1-brief.md § 1, § 3).
 *
 * Opened from an equipment page (?equipment=<id>, the node a QR label leads to) or from the
 * Tickets list, where the equipment is picked first. The user gives the intensity (three
 * large buttons), a symptom (optional), a description (needed with no symptom or with Other),
 * when it happened and who found it. Before Save the machine's open tickets are listed: it
 * warns, it does not block.
 *
 * The event time is sent only when the user changed it (BR2-05): left alone, the server's
 * clock is the time, so a phone a few minutes fast never gets a refusal for a time nobody
 * typed. After Save, photos are added on the same screen (camera or gallery: no `capture`),
 * each titled with its file name, then Done opens the ticket page.
 *
 * S018: opened as ?equipment=<id>&repeat_of=<ticket id> from *Not fixed — raise again*, the
 * screen pre-fills the earlier ticket's symptom and current intensity once the node has loaded
 * (after resetForm(), which every node change runs), and Save sends repeat_of_id.
 *
 * S018 A1, *Already fixed*: a user holding ticket:restore at the node's site may tick "Already
 * fixed — back in service" and give the back-in-service time ("Now · Change", EventFields
 * without the remark), who did the work (PersonPicker; pre-filled with his own person only when
 * he holds ticket:work there and is in the site's people list, BS2-04) and, optionally, when
 * work started (StartedAtFields). Save then sends them as `restore`; the server raises and
 * applies the back-in-service move in one transaction, and its refusals come back named
 * restore.<field>. Unticking hides the fields (v-show: the time control keeps its state) and
 * keeps what was typed; a node change clears them with the rest (blankForm).
 *
 * The API decides every refusal; this screen only shows them beside the field they name.
 */
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiPost, apiUpload } from "../api";
import IntensityBadge from "../components/IntensityBadge.vue";
import { useDebounced } from "../composables/useDebounced";
import { userPersonId } from "../stores/auth";
import { ACCEPT, IPHONE_PHOTO_HINT, withoutExtension } from "../utils/documentTypes";
import { revealError } from "../utils/revealError";
import { roleLabel } from "../utils/siteRoles";
import {
  ageText, INTENSITY_CHOICES, problemText, moveSaveLabel, raiseSaveLabel, restoreTimeLabel, toLocalDateValue, toLocalInputValue,
} from "../utils/ticketLabels";
import EventFields from "./tickets/EventFields.vue";
import PersonPicker from "./tickets/PersonPicker.vue";
import StartedAtFields from "./tickets/StartedAtFields.vue";

const OTHER_MODE = "OTH";
const DESCRIPTION_MAX = 1000;
const TITLE_MAX = 200;
const MB = 1024 * 1024;
const PICKER_SIZE = 20;
// The picked intensity button, in its badge's colour
const PICKED_CLASS = { critical: "btn-danger", degraded: "btn-warning", initial: "btn-secondary" };

const route = useRoute();
const router = useRouter();

// ---- the equipment ----

const node = ref(null);
const nodeLoading = ref(false);
const nodeError = ref("");
const modes = ref([]);
const people = ref([]);
const openTickets = ref([]);
const repeatOf = ref(null); // the earlier ticket of a repeat (S018 § 5.5): {id, serial}
const repeatError = ref("");
let loadSeq = 0;

const nodeId = computed(() => route.query.equipment ?? null);
const repeatOfId = computed(() => route.query.repeat_of ?? null);
const canRaiseHere = computed(() => (node.value?.permissions ?? []).includes("ticket:raise"));
const canRestoreHere = computed(() => (node.value?.permissions ?? []).includes("ticket:restore"));
const scrapped = computed(() => node.value?.status === "scrapped");

async function loadNode() {
  const seq = ++loadSeq;
  node.value = null;
  nodeError.value = "";
  modes.value = [];
  people.value = [];
  openTickets.value = [];
  repeatOf.value = null;
  repeatError.value = "";
  if (!nodeId.value) return;
  nodeLoading.value = true;
  try {
    const loaded = await apiGet(`/api/equipment/${nodeId.value}`);
    if (seq !== loadSeq) return;
    node.value = loaded;
    if (loaded.status === "scrapped" || !loaded.permissions.includes("ticket:raise")) return;
    // The open-tickets warning is about the machine, also when the label scanned was a part's (BR2-08)
    const machine = loaded.level === "equipment" ? loaded.id : loaded.ancestors[0].id;
    const [modeList, peopleList, open] = await Promise.all([
      apiGet(`/api/tickets/modes?equipment_id=${loaded.id}`),
      apiGet(`/api/tickets/people?equipment_id=${loaded.id}`),
      apiGet(`/api/tickets?equipment_id=${machine}&state=open`),
    ]);
    if (seq !== loadSeq) return;
    modes.value = modeList.items;
    people.value = peopleList.items;
    openTickets.value = open.items;
    form.value.restorePersonId = defaultRestorePerson(loaded.permissions, peopleList.items);
    if (repeatOfId.value) await loadRepeatOf(seq);
  } catch (err) {
    if (seq !== loadSeq) return;
    nodeError.value = err.status === 404 ? "Equipment not found, or not at your units." : err.message;
  } finally {
    if (seq === loadSeq) nodeLoading.value = false;
  }
}

/** The earlier ticket's symptom and current intensity, into the form resetForm() just cleared. */
async function loadRepeatOf(seq) {
  try {
    const earlier = await apiGet(`/api/tickets/${repeatOfId.value}`);
    if (seq !== loadSeq) return;
    repeatOf.value = { id: earlier.id, serial: earlier.serial };
    form.value.intensity = earlier.intensity;
    form.value.failureModeId = earlier.failure_mode?.id ?? "";
  } catch (err) {
    if (seq === loadSeq) repeatError.value = `The earlier ticket could not be read (${err.message}); this is saved as a new ticket.`;
  }
}

/**
 * Who did the work, pre-filled (A1): the user's own person when he holds ticket:work at the
 * site and may be named there (the page-side form of the move's default_person), else nobody.
 */
function defaultRestorePerson(permissions, sitePeople) {
  if (!permissions.includes("ticket:work") || userPersonId.value === null) return null;
  return sitePeople.some((p) => p.id === userPersonId.value) ? userPersonId.value : null;
}

function chooseEquipment(id) {
  router.replace({ query: id ? { equipment: String(id) } : {} });
}

// ---- equipment picker (no ?equipment): search by code or name among the user's units ----

const searchText = ref("");
const results = ref(null);
const searching = ref(false);
const searchError = ref("");
let searchSeq = 0;

async function search() {
  const text = searchText.value.trim();
  const seq = ++searchSeq;
  searchError.value = "";
  if (!text) {
    results.value = null;
    return;
  }
  searching.value = true;
  try {
    const params = new URLSearchParams({ level: "all", q: text, per_page: String(PICKER_SIZE) });
    const page = await apiGet(`/api/equipment?${params}`);
    if (seq === searchSeq) results.value = page;
  } catch (err) {
    if (seq === searchSeq) searchError.value = err.message;
  } finally {
    if (seq === searchSeq) searching.value = false;
  }
}

const { schedule: scheduleSearch } = useDebounced(search);
watch(searchText, scheduleSearch);

// ---- the form ----

const form = ref(blankForm());
const timeTouched = ref(false);
const fieldErrors = ref({});
const formError = ref("");
const saving = ref(false);
const formEl = ref(null); // the <form>: where a refusal is searched for

// A refusal is always in view (S026): on a phone the form is long and Save is at its bottom, so
// scroll to the first message and focus its field. Post flush: is-invalid is in the DOM by then.
// Every refusal assigns a new fieldErrors object, so the watch fires on a repeat too.
watch([fieldErrors, formError], () => {
  if (Object.keys(fieldErrors.value).length || formError.value) revealError(formEl.value);
}, { flush: "post" });

function blankForm() {
  return {
    intensity: "", failureModeId: "", description: "", occurredAt: toLocalInputValue(new Date()), reportedById: "",
    // Already fixed (A1): restoreAt null = now, as every move dialog
    alreadyFixed: false, restoreAt: null, restorePersonId: null, startedDate: toLocalDateValue(new Date()), startedTime: "",
  };
}

function resetForm() {
  form.value = blankForm();
  timeTouched.value = false;
  fieldErrors.value = {};
  formError.value = "";
}

// Below the form's refs: `immediate` runs it during setup, and resetForm() must not reach
// them before their `const` lines have run
watch(nodeId, () => {
  resetForm();
  loadNode();
}, { immediate: true });

const pickedMode = computed(() => modes.value.find((m) => String(m.id) === String(form.value.failureModeId)));
const descriptionNeeded = computed(() => !pickedMode.value || pickedMode.value.code === OTHER_MODE);

async function save() {
  fieldErrors.value = {};
  formError.value = "";
  if (!form.value.intensity) {
    fieldErrors.value = { intensity: "Choose how bad it is" };
    return;
  }
  const description = form.value.description.trim();
  if (descriptionNeeded.value && !description) {
    fieldErrors.value = { description: pickedMode.value ? "Describe the problem" : "Describe the problem, or pick a symptom" };
    return;
  }
  if (form.value.alreadyFixed && !form.value.restorePersonId) {
    fieldErrors.value = { "restore.person_id": "Who did the work? Pick a name" };
    return;
  }
  const body = {
    equipment_id: node.value.id,
    intensity: form.value.intensity,
    failure_mode_id: form.value.failureModeId ? Number(form.value.failureModeId) : null,
    description: description || null,
    reported_by_id: form.value.reportedById ? Number(form.value.reportedById) : null,
    repeat_of_id: repeatOf.value?.id ?? null,
  };
  // A cleared picker means "now", like an untouched one: send nothing
  if (timeTouched.value && form.value.occurredAt) body.occurred_at = form.value.occurredAt;
  if (form.value.alreadyFixed) body.restore = restoreBody();
  saving.value = true;
  try {
    ticket.value = await apiPost("/api/tickets", body);
    loadPhotoLimit();
  } catch (err) {
    if (err.field && err.field !== "equipment_id") fieldErrors.value = { [err.field]: err.message };
    else formError.value = err.message;
  } finally {
    saving.value = false;
  }
}

/** The back-in-service block, as the restore move's dialog sends it (times only when given). */
function restoreBody() {
  const f = form.value;
  const restore = { person_id: f.restorePersonId };
  if (f.restoreAt) restore.occurred_at = f.restoreAt;
  if (f.startedTime && f.startedDate) restore.started_at = `${f.startedDate}T${f.startedTime}`;
  return restore;
}

// ---- after Save: photos ----

const ticket = ref(null);
const photoLimitMb = ref(null);
const uploads = ref([]); // {key, name, state: "uploading" | "done" | "failed", message}
const uploading = computed(() => uploads.value.some((u) => u.state === "uploading"));
let uploadKey = 0;

async function loadPhotoLimit() {
  try {
    photoLimitMb.value = (await apiGet(`/api/tickets/${ticket.value.id}/documents`)).upload_max_mb;
  } catch {
    photoLimitMb.value = null; // the server still checks each upload
  }
}

async function uploadOne(file) {
  const entry = { key: ++uploadKey, name: file.name, state: "uploading", message: "" };
  uploads.value.push(entry);
  const row = uploads.value[uploads.value.length - 1];
  if (photoLimitMb.value && file.size > photoLimitMb.value * MB) {
    Object.assign(row, { state: "failed", message: `Larger than ${photoLimitMb.value} MB` });
    return;
  }
  const body = new FormData();
  body.append("kind", "photo");
  body.append("title", withoutExtension(file.name).slice(0, TITLE_MAX));
  body.append("file", file);
  try {
    await apiUpload(`/api/tickets/${ticket.value.id}/documents`, body);
    row.state = "done";
  } catch (err) {
    Object.assign(row, { state: "failed", message: err.message });
  }
}

async function onPhotosChosen(event) {
  const files = [...event.target.files];
  event.target.value = ""; // the same photo can be picked again after a failure
  for (const file of files) await uploadOne(file); // one at a time: kinder to a slow mobile link
}

function done() {
  router.push(`/tickets/${ticket.value.id}`);
}
</script>

<template>
  <div class="py-3 raise">
    <h4 class="mb-3">Raise ticket</h4>

    <!-- Step 2: saved; add photos -->
    <template v-if="ticket">
      <div class="alert alert-success">
        Ticket <strong>{{ ticket.serial }}</strong> saved<template v-if="ticket.state === 'back_in_service'"> and marked {{ moveSaveLabel("restore", ticket.intensity).toLowerCase() }}</template>.
      </div>
      <p class="mb-2">Add photos of the problem, if you have them.</p>
      <label class="btn btn-outline-primary btn-lg w-100 mb-2" :class="{ disabled: uploading }">
        <i class="fa-solid fa-camera me-2"></i>Add photos
        <input class="visually-hidden" type="file" multiple :accept="ACCEPT.photo" :disabled="uploading" @change="onPhotosChosen" />
      </label>
      <div class="form-text mb-3">
        <template v-if="photoLimitMb">At most {{ photoLimitMb }} MB each. </template>{{ IPHONE_PHOTO_HINT }}
      </div>
      <ul v-if="uploads.length" class="list-group mb-3">
        <li v-for="u in uploads" :key="u.key" class="list-group-item d-flex align-items-center gap-2">
          <i
            class="fa-solid"
            :class="{
              'fa-spinner fa-spin text-secondary': u.state === 'uploading',
              'fa-check text-success': u.state === 'done',
              'fa-xmark text-danger': u.state === 'failed',
            }"
          ></i>
          <span class="text-break">{{ u.name }}</span>
          <span v-if="u.message" class="small text-danger ms-auto">{{ u.message }}</span>
        </li>
      </ul>
      <button class="btn btn-primary btn-lg w-100" :disabled="uploading" @click="done">Done</button>
    </template>

    <!-- Step 1: pick the equipment -->
    <template v-else-if="!nodeId">
      <label class="form-label" for="raise-search">Which equipment?</label>
      <input
        id="raise-search"
        v-model="searchText"
        class="form-control form-control-lg mb-2"
        type="search"
        placeholder="Code or name"
        autocomplete="off"
      />
      <div v-if="searching" class="text-secondary small">Searching…</div>
      <div v-if="searchError" class="alert alert-danger py-2">{{ searchError }}</div>
      <div v-else-if="results && results.items.length === 0" class="text-secondary">No equipment found at your units.</div>
      <div v-else-if="results" class="list-group">
        <button
          v-for="e in results.items"
          :key="e.id"
          type="button"
          class="list-group-item list-group-item-action py-3"
          @click="chooseEquipment(e.id)"
        >
          <span class="fw-semibold">{{ e.code }}</span> — {{ e.name }}
          <div class="small text-secondary">{{ e.full_path }}</div>
        </button>
        <div v-if="results.total > results.items.length" class="list-group-item small text-secondary">
          More found — type more of the code or name.
        </div>
      </div>
    </template>

    <!-- Step 1: the ticket -->
    <template v-else>
      <div v-if="nodeLoading && !node" class="text-secondary">Loading…</div>
      <div v-else-if="nodeError" class="alert alert-warning d-flex flex-wrap justify-content-between align-items-center gap-2">
        <span>{{ nodeError }}</span>
        <button class="btn btn-outline-secondary" @click="chooseEquipment(null)">Pick other equipment</button>
      </div>
      <template v-else-if="node">
        <div class="card mb-3">
          <div class="card-body d-flex flex-wrap align-items-center gap-2">
            <div class="flex-grow-1 text-break">
              <div class="fw-semibold">{{ node.code }} — {{ node.name }}</div>
              <div class="small text-secondary">{{ node.full_path }}</div>
            </div>
            <button class="btn btn-outline-secondary" type="button" @click="chooseEquipment(null)">Change</button>
          </div>
        </div>

        <div v-if="scrapped" class="alert alert-secondary">Scrapped equipment takes no tickets.</div>
        <div v-else-if="!canRaiseHere" class="alert alert-secondary">You can't raise tickets at this site.</div>
        <form v-else ref="formEl" novalidate @submit.prevent="save">
          <div v-if="repeatOf" class="alert alert-info py-2">
            Repeat of <router-link :to="`/tickets/${repeatOf.id}`" target="_blank">{{ repeatOf.serial }}</router-link>:
            the same fault came back after the repair.
          </div>
          <div v-if="repeatError" class="alert alert-warning py-2">{{ repeatError }}</div>
          <div v-if="fieldErrors.repeat_of_id" class="alert alert-danger py-2">{{ fieldErrors.repeat_of_id }}</div>
          <fieldset class="mb-3">
            <legend class="form-label fs-6 mb-2">How bad is it?</legend>
            <div class="d-grid gap-2">
              <button
                v-for="c in INTENSITY_CHOICES"
                :key="c.value"
                type="button"
                class="btn btn-lg text-start"
                :class="form.intensity === c.value ? PICKED_CLASS[c.value] : 'btn-outline-secondary'"
                :aria-pressed="form.intensity === c.value"
                @click="form.intensity = c.value"
              >
                <span class="fw-semibold">{{ c.label }}</span>
                <span class="d-block small">{{ c.hint }}</span>
              </button>
            </div>
            <div v-if="fieldErrors.intensity" class="invalid-feedback d-block">{{ fieldErrors.intensity }}</div>
          </fieldset>

          <div class="mb-3">
            <label class="form-label" for="raise-mode">Symptom <span class="text-secondary">(if you know it)</span></label>
            <select
              id="raise-mode"
              v-model="form.failureModeId"
              class="form-select form-select-lg"
              :class="{ 'is-invalid': fieldErrors.failure_mode_id }"
            >
              <option value="">— Not sure —</option>
              <option v-for="m in modes" :key="m.id" :value="m.id">{{ m.label }}</option>
            </select>
            <div v-if="fieldErrors.failure_mode_id" class="invalid-feedback d-block">{{ fieldErrors.failure_mode_id }}</div>
          </div>

          <div class="mb-3">
            <label class="form-label" for="raise-description">
              What is wrong?<span v-if="!descriptionNeeded" class="text-secondary"> (optional)</span>
            </label>
            <textarea
              id="raise-description"
              v-model="form.description"
              class="form-control"
              :class="{ 'is-invalid': fieldErrors.description }"
              rows="3"
              :maxlength="DESCRIPTION_MAX"
            ></textarea>
            <div v-if="fieldErrors.description" class="invalid-feedback d-block">{{ fieldErrors.description }}</div>
          </div>

          <div class="mb-3">
            <label class="form-label" for="raise-time">When did it happen?</label>
            <input
              id="raise-time"
              v-model="form.occurredAt"
              class="form-control form-control-lg"
              :class="{ 'is-invalid': fieldErrors.occurred_at }"
              type="datetime-local"
              @input="timeTouched = true"
            />
            <div v-if="fieldErrors.occurred_at" class="invalid-feedback d-block">{{ fieldErrors.occurred_at }}</div>
          </div>

          <div class="mb-3">
            <label class="form-label" for="raise-reporter">Found by <span class="text-secondary">(if not you)</span></label>
            <select
              id="raise-reporter"
              v-model="form.reportedById"
              class="form-select form-select-lg"
              :class="{ 'is-invalid': fieldErrors.reported_by_id }"
            >
              <option value="">—</option>
              <option v-for="p in people" :key="p.id" :value="p.id">{{ p.name }} ({{ roleLabel(p.role) }})</option>
            </select>
            <div v-if="fieldErrors.reported_by_id" class="invalid-feedback d-block">{{ fieldErrors.reported_by_id }}</div>
          </div>

          <div v-if="canRestoreHere" class="mb-3">
            <input id="raise-already-fixed" v-model="form.alreadyFixed" class="btn-check" type="checkbox" autocomplete="off" />
            <label
              class="btn btn-lg w-100 text-start"
              :class="form.alreadyFixed ? 'btn-success' : 'btn-outline-success'"
              for="raise-already-fixed"
            >
              <i class="me-2" :class="form.alreadyFixed ? 'fa-solid fa-square-check' : 'fa-regular fa-square'"></i>Already fixed — back in service
            </label>
            <div v-show="form.alreadyFixed" class="border-start border-3 ps-3 mt-2">
              <p class="form-text mb-2">Set <em>When did it happen?</em> above to when the machine stopped.</p>
              <EventFields
                v-model:time="form.restoreAt"
                :with-remark="false"
                :time-label="restoreTimeLabel(form.intensity)"
                :time-error="fieldErrors['restore.occurred_at']"
                id-prefix="raise-restore"
              />
              <div class="mb-3">
                <label class="form-label" for="raise-restore-person-filter">Who did the work?</label>
                <PersonPicker
                  v-model="form.restorePersonId"
                  :people="people"
                  :own-person-id="userPersonId"
                  :invalid="Boolean(fieldErrors['restore.person_id'])"
                  id-prefix="raise-restore-person"
                />
                <div v-if="fieldErrors['restore.person_id']" class="invalid-feedback d-block">{{ fieldErrors["restore.person_id"] }}</div>
              </div>
              <StartedAtFields
                v-model:date="form.startedDate"
                v-model:time="form.startedTime"
                :restored-at="form.restoreAt"
                :error="fieldErrors['restore.started_at']"
                id-prefix="raise-restore-started"
              />
            </div>
          </div>

          <div v-if="openTickets.length" class="alert alert-warning">
            <div class="fw-semibold mb-1">Already reported on this machine:</div>
            <ul class="list-unstyled mb-1">
              <li v-for="t in openTickets" :key="t.id" class="mb-1">
                <IntensityBadge :intensity="t.intensity" class="me-1" />
                <router-link :to="`/tickets/${t.id}`" target="_blank">{{ t.serial }}</router-link>
                <span v-if="t.component" class="text-secondary"> · {{ t.component.code }}</span>
                · {{ problemText(t) }} · {{ ageText(t.occurred_at) }}
              </li>
            </ul>
            <div class="small">If this is a different problem, save it as a new ticket.</div>
          </div>

          <div v-if="formError" class="alert alert-danger py-2">{{ formError }}</div>
          <button type="submit" class="btn btn-primary btn-lg w-100" :disabled="saving">
            {{ saving ? "Saving…" : raiseSaveLabel(form.alreadyFixed, form.intensity) }}
          </button>
        </form>
      </template>
    </template>
  </div>
</template>

<style scoped>
.raise {
  max-width: 40rem;
}
</style>
