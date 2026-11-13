<script setup>
/**
 * A PM template's page (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.10, mock-up 09): a new template
 * (`/masters/pm-templates/new`) or an existing one (`/masters/pm-templates/<id>`). The work of a PM plan, written
 * once (TPM: the planned-maintenance standard): *Name*, *Done by*, *An engineer verifies each job*, *When is it
 * due?* (a calendar interval, a meter type, or whichever comes first) and the items. Built from S096's plan editor
 * without the equipment, the assignee and *Last done* (each machine's own, on its plan page).
 *
 * A page, not a dialog (S096 D1): each item opens its own dialog (PmItemDialog). *Save template* sends the template
 * with its whole item list in one request; the server then moves the jobs of every machine it is on (§ 5.6). A
 * schedule change on more than one machine asks first (BR1-08). A refusal shows beside its field; an items refusal
 * ("Item 3: …") above the list, with row 3 outlined.
 *
 * Read-only for a reader without pm_plan:edit (`can_edit`). Not a nav item: a technician reaches it from the plan
 * page's *Open template*, and the API is the gate (BR1-15). The page provides FORM_DIRTY, so Deactivate waits for
 * unsaved changes; Cancel asks first then.
 */
import { computed, nextTick, provide, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiPost, apiPut } from "../api";
import { ensureMeterTypes, meterTypes } from "../stores/masters";
import { formatDate } from "../utils/datetime";
import { FORM_DIRTY } from "../utils/formDirty";
import { formSnapshot } from "../utils/formSnapshot";
import {
  CALENDAR_UNITS, ITEM_TYPES, PERFORMERS, deactivateQuestion, itemType, moveItem, newTemplateForm,
  performerLabel, photoLabel, refusedItemNumber, savedNoteText, scheduleChangeQuestion, scheduleChanged,
  templateBody, templateForm, usedOnText,
} from "../utils/pmLabels";
import { revealError } from "../utils/revealError";
import PmItemDialog from "./pm/PmItemDialog.vue";

const MASTERS_PATH = "/masters?section=pm_templates";
const CHANGE_NOTE = "A change here reaches every machine at its next job. A job already started keeps the items it started with.";
// S104 A1.6.7: no parent tick; a part uses a node above's meter through a link on its Meters card
const METER_NOTE = "The template names the meter type. Each machine uses its own meter of that type, or the meter of a node above that its Meters card links. A machine without one: the template does not apply there.";

const route = useRoute();
const router = useRouter();

const template = ref(null); // the detail (§ 6); null for a new template
const canEdit = ref(false);
const form = ref(newTemplateForm());
const items = ref([]); // the items in their order, in the API's item shape

const loading = ref(true);
const notFound = ref(false);
const forbidden = ref(false);
const loadError = ref("");
const saving = ref(false);
const error = ref(null); // {field, message} of the last refused save
const savedNote = ref("");
const confirmingLeave = ref(false);
const confirmingSchedule = ref(false);
const confirmingDeactivate = ref(false);
const pageEl = ref(null);
const dialog = ref(null);
const snapshot = ref(null);
let loadSeq = 0;

const isNew = computed(() => route.name === "pm-template-new");
const dirty = computed(() => snapshot.value !== null && formSnapshot([form.value, items.value]) !== snapshot.value);
provide(FORM_DIRTY, dirty);

// The trigger's choices: the active counters, and the template's own type when it is no longer one of them
const counters = computed(() => (meterTypes.value ?? []).filter(
  (t) => t.kind === "counter" && (t.active || t.id === Number(form.value.meter_type_id))));
const chosenCounter = computed(() => counters.value.find((t) => t.id === Number(form.value.meter_type_id)) ?? null);
const refusedItem = computed(() => (error.value?.field === "items" ? refusedItemNumber(error.value.message) : null));
const PAGE_FIELDS = ["name", "performer", "needs_verification", "trigger_kind", "calendar_every", "calendar_unit",
  "meter_type_id", "meter_every", "items"];
const topError = computed(() => (error.value && !PAGE_FIELDS.includes(error.value.field) ? error.value.message : ""));
const fieldError = (name) => (error.value?.field === name ? error.value.message : "");
const planCount = computed(() => template.value?.plan_count ?? 0);

function markClean() {
  snapshot.value = formSnapshot([form.value, items.value]);
}

async function load() {
  const id = route.params.id;
  if (!isNew.value && id === undefined) return; // the route is changing to another page
  const seq = ++loadSeq;
  loading.value = true;
  notFound.value = false;
  forbidden.value = false;
  loadError.value = "";
  error.value = null;
  confirmingLeave.value = false;
  confirmingSchedule.value = false;
  confirmingDeactivate.value = false;
  snapshot.value = null;
  try {
    if (isNew.value) {
      const [list] = await Promise.all([apiGet("/api/pm/templates"), ensureMeterTypes()]);
      if (seq !== loadSeq) return;
      if (!list.can_add) {
        forbidden.value = true;
        return;
      }
      template.value = null;
      canEdit.value = true;
      form.value = newTemplateForm();
      items.value = [];
    } else {
      const [loaded] = await Promise.all([apiGet(`/api/pm/templates/${id}`), ensureMeterTypes()]);
      if (seq !== loadSeq) return;
      template.value = loaded;
      canEdit.value = loaded.can_edit;
      form.value = templateForm(loaded);
      items.value = loaded.items;
    }
    await nextTick();
    markClean();
  } catch (err) {
    if (seq !== loadSeq) return;
    if (err.status === 404) notFound.value = true;
    else if (err.status === 403) forbidden.value = true;
    else loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

watch(() => [route.name, route.params.id], load, { immediate: true });

// A refusal is always in view (S026): post flush, so is-invalid is in the DOM
watch(error, (refusal) => {
  if (refusal) revealError(pageEl.value);
}, { flush: "post" });

function onPerformerChange() {
  form.value.needs_verification = form.value.performer === "maintenance";
}

function onItemDone({ item, index }) {
  if (index === null) items.value = [...items.value, item];
  else items.value = items.value.map((existing, i) => (i === index ? item : existing));
}

function onItemRemove(index) {
  items.value = items.value.filter((_, i) => i !== index);
}

function move(index, step) {
  items.value = moveItem(items.value, index, step);
}

function afterSave(saved) {
  savedNote.value = savedNoteText(saved.plans_failed);
}

async function send(body) {
  saving.value = true;
  error.value = null;
  savedNote.value = "";
  try {
    if (isNew.value) {
      const saved = await apiPost("/api/pm/templates", body);
      markClean();
      await router.replace(`/masters/pm-templates/${saved.id}`);
      afterSave(saved);
      return;
    }
    const saved = await apiPut(`/api/pm/templates/${template.value.id}`, body);
    await load();
    afterSave(saved);
  } catch (err) {
    // BR1-12: after a commit the plans are settled in the same request; a lost connection then answers 503
    const message = err.status === 503 ? "The template may be saved. Reload the page to see it." : err.message;
    error.value = { field: err.field, message };
  } finally {
    saving.value = false;
  }
}

function save() {
  const body = templateBody(form.value, items.value);
  if (!confirmingSchedule.value && planCount.value > 1 && scheduleChanged(template.value, body)) {
    confirmingSchedule.value = true; // ISO 55001 § 8.2: a schedule change on several machines is confirmed
    return;
  }
  confirmingSchedule.value = false;
  send(body);
}

function cancel() {
  if (dirty.value) confirmingLeave.value = true;
  else router.push(MASTERS_PATH);
}

async function setActive(active) {
  confirmingDeactivate.value = false;
  saving.value = true;
  error.value = null;
  try {
    await apiPut(`/api/pm/templates/${template.value.id}`, { active });
  } catch (err) {
    error.value = { field: err.field, message: err.message };
    return;
  } finally {
    saving.value = false;
  }
  await load();
}

const verifyText = (t) => (t.needs_verification ? "An engineer verifies each job" : "No verification");
</script>

<template>
  <div ref="pageEl" class="py-3">
    <div v-if="loading && !template && !forbidden && !notFound" class="text-secondary">Loading…</div>
    <div v-else-if="notFound" class="alert alert-warning">
      PM template not found.
      <router-link :to="MASTERS_PATH" class="alert-link ms-1">Back to PM templates</router-link>
    </div>
    <div v-else-if="forbidden" class="alert alert-warning">
      You can't add PM templates.
      <router-link :to="MASTERS_PATH" class="alert-link ms-1">Back to PM templates</router-link>
    </div>
    <div v-else-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger tap-target" @click="load">Retry</button>
    </div>

    <template v-else-if="isNew || template">
      <nav class="small mb-2" aria-label="Path">
        <router-link to="/masters">Masters</router-link>
        <span class="text-secondary"> › </span>
        <router-link :to="MASTERS_PATH">PM templates</router-link>
      </nav>
      <div class="d-flex flex-wrap align-items-center gap-2 mb-1">
        <h4 class="mb-0 template-name">{{ isNew ? "New PM template" : template.name }}</h4>
        <span v-if="template && !template.active" class="badge text-bg-secondary">Inactive</span>
      </div>
      <p v-if="template" class="text-secondary mb-3" data-testid="pm-used-on">{{ usedOnText(template.plan_count) }}</p>
      <p v-if="canEdit" class="small text-secondary mb-3">{{ CHANGE_NOTE }}</p>
      <div v-if="template && !template.active" class="alert alert-secondary">
        This template is inactive. Its machines get no jobs.
      </div>
      <div v-if="savedNote" class="alert alert-success py-2" role="status">{{ savedNote }}</div>
      <div v-if="topError" class="alert alert-danger py-2">{{ topError }}</div>

      <div class="row g-3">
        <div class="col-lg-6">
          <!-- Template -->
          <div class="card mb-3">
            <div class="card-header">Template</div>
            <div class="card-body">
              <template v-if="canEdit">
                <div class="mb-3">
                  <label class="form-label" for="pm-name">Name</label>
                  <input id="pm-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" autocomplete="off" />
                  <div class="form-text">For example: Press — monthly hydraulic check</div>
                  <div v-if="fieldError('name')" class="invalid-feedback d-block">{{ fieldError("name") }}</div>
                </div>
                <div class="mb-3">
                  <label class="form-label" for="pm-performer">Done by</label>
                  <select id="pm-performer" v-model="form.performer" class="form-select" :class="{ 'is-invalid': fieldError('performer') }" @change="onPerformerChange">
                    <option v-for="p in PERFORMERS" :key="p.value" :value="p.value">{{ p.label }}</option>
                  </select>
                  <div v-if="fieldError('performer')" class="invalid-feedback d-block">{{ fieldError("performer") }}</div>
                </div>
                <div class="form-check">
                  <input id="pm-verify" v-model="form.needs_verification" class="form-check-input" type="checkbox" />
                  <label class="form-check-label" for="pm-verify">An engineer verifies each job</label>
                  <div class="form-text">Leave it ticked for maintenance work. Untick it for routine checks.</div>
                </div>
              </template>
              <template v-else>
                <div class="mb-3">
                  <div class="form-label mb-1">Done by</div>
                  <div>{{ performerLabel(template.performer) }}</div>
                </div>
                <div>
                  <div class="form-label mb-1">Verification</div>
                  <div>{{ verifyText(template) }}</div>
                </div>
              </template>
            </div>
          </div>

          <!-- When is it due? -->
          <div class="card mb-3">
            <div class="card-header">When is it due?</div>
            <div class="card-body">
              <template v-if="canEdit">
                <div class="mb-3">
                  <div class="d-flex flex-wrap align-items-center gap-2">
                    <div class="form-check mb-0">
                      <input id="pm-calendar-on" v-model="form.calendarOn" class="form-check-input" type="checkbox" />
                      <label class="form-check-label" for="pm-calendar-on">By calendar: every</label>
                    </div>
                    <input v-model="form.calendar_every" class="form-control every-number" :class="{ 'is-invalid': fieldError('calendar_every') }" inputmode="numeric" aria-label="Calendar interval" :disabled="!form.calendarOn" />
                    <select v-model="form.calendar_unit" class="form-select every-unit" :class="{ 'is-invalid': fieldError('calendar_unit') }" aria-label="Calendar unit" :disabled="!form.calendarOn">
                      <option v-for="u in CALENDAR_UNITS" :key="u.value" :value="u.value">{{ u.label }}</option>
                    </select>
                  </div>
                  <div v-if="fieldError('calendar_every')" class="invalid-feedback d-block">{{ fieldError("calendar_every") }}</div>
                  <div v-if="fieldError('calendar_unit')" class="invalid-feedback d-block">{{ fieldError("calendar_unit") }}</div>
                </div>
                <div class="mb-2">
                  <div class="d-flex flex-wrap align-items-center gap-2">
                    <div class="form-check mb-0">
                      <input id="pm-meter-on" v-model="form.meterOn" class="form-check-input" type="checkbox" />
                      <label class="form-check-label" for="pm-meter-on">By meter: every</label>
                    </div>
                    <input v-model="form.meter_every" class="form-control every-number" :class="{ 'is-invalid': fieldError('meter_every') }" inputmode="decimal" aria-label="Meter interval" :disabled="!form.meterOn" />
                    <span v-if="chosenCounter">{{ chosenCounter.unit }}</span>
                    <span>of</span>
                    <select v-model="form.meter_type_id" class="form-select every-meter" :class="{ 'is-invalid': fieldError('meter_type_id') }" aria-label="Meter type" :disabled="!form.meterOn">
                      <option value="">Choose a meter type…</option>
                      <option v-for="t in counters" :key="t.id" :value="t.id">{{ t.name }}</option>
                    </select>
                  </div>
                  <div v-if="fieldError('meter_type_id')" class="invalid-feedback d-block">{{ fieldError("meter_type_id") }}</div>
                  <div v-if="fieldError('meter_every')" class="invalid-feedback d-block">{{ fieldError("meter_every") }}</div>
                </div>
                <div class="form-text mb-2" data-testid="pm-meter-note">{{ METER_NOTE }}</div>
                <div class="form-text">Both ticked: the job is due at whichever comes first.</div>
                <div v-if="fieldError('trigger_kind')" class="invalid-feedback d-block">{{ fieldError("trigger_kind") }}</div>
              </template>
              <template v-else>
                <div class="fw-semibold" data-testid="pm-trigger">{{ template.trigger_text }}</div>
              </template>
            </div>
          </div>
        </div>

        <div class="col-lg-6">
          <!-- Items -->
          <div class="card mb-3" data-testid="pm-items">
            <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
              <span>Items ({{ items.length }})</span>
              <button v-if="canEdit" type="button" class="btn btn-sm btn-primary tap-target" @click="dialog.openAdd()">
                <i class="fa-solid fa-plus me-1"></i>Add item
              </button>
            </div>
            <div v-if="fieldError('items')" class="alert alert-danger py-2 m-2 mb-0">{{ fieldError("items") }}</div>
            <div v-if="items.length === 0" class="card-body text-secondary">No items yet. Add the first item.</div>
            <template v-else>
              <!-- From md: a table -->
              <table class="table align-middle mb-0 d-none d-md-table">
                <thead>
                  <tr><th>#</th><th>Type</th><th>Item</th><th>Limits / meter type</th><th>Photo</th><th v-if="canEdit"></th></tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in items" :key="item.id ?? `new-${index}`" :class="{ 'refused-row': refusedItem === index + 1 }">
                    <td>{{ index + 1 }}</td>
                    <td><span class="badge" :class="itemType(item.item_type).badge">{{ itemType(item.item_type).label }}</span></td>
                    <td class="item-text">
                      <button v-if="canEdit" type="button" class="btn btn-link p-0 text-start" @click="dialog.openEditAt(item, index)">{{ item.text }}</button>
                      <span v-else>{{ item.text }}</span>
                      <div v-if="item.help_text" class="small text-secondary help-text">{{ item.help_text }}</div>
                    </td>
                    <td class="small">{{ item.limits_text ?? "—" }}</td>
                    <td class="small">{{ photoLabel(item.photo) }}</td>
                    <td v-if="canEdit" class="text-nowrap">
                      <button v-if="index > 0" type="button" class="btn btn-sm btn-outline-secondary tap-target me-1" aria-label="Move up" @click="move(index, -1)"><i class="fa-solid fa-arrow-up"></i></button>
                      <button v-if="index < items.length - 1" type="button" class="btn btn-sm btn-outline-secondary tap-target" aria-label="Move down" @click="move(index, 1)"><i class="fa-solid fa-arrow-down"></i></button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <!-- Below md: a list, one item per row -->
              <ul class="list-group list-group-flush d-md-none" data-testid="pm-item-list">
                <li v-for="(item, index) in items" :key="item.id ?? `new-${index}`" class="list-group-item d-flex gap-2" :class="{ 'refused-row': refusedItem === index + 1 }">
                  <div class="flex-grow-1 item-text">
                    <div>
                      <span class="me-1">{{ index + 1 }}.</span>
                      <span class="badge me-1" :class="itemType(item.item_type).badge">{{ itemType(item.item_type).label }}</span>
                      <button v-if="canEdit" type="button" class="btn btn-link p-0 text-start align-baseline" @click="dialog.openEditAt(item, index)">{{ item.text }}</button>
                      <span v-else>{{ item.text }}</span>
                    </div>
                    <div class="small text-secondary">
                      <template v-if="item.limits_text">{{ item.limits_text }} · </template>Photo: {{ photoLabel(item.photo) }}
                    </div>
                    <div v-if="item.help_text" class="small text-secondary help-text">{{ item.help_text }}</div>
                  </div>
                  <div v-if="canEdit" class="d-flex flex-column gap-1">
                    <button v-if="index > 0" type="button" class="btn btn-sm btn-outline-secondary tap-target" aria-label="Move up" @click="move(index, -1)"><i class="fa-solid fa-arrow-up"></i></button>
                    <button v-if="index < items.length - 1" type="button" class="btn btn-sm btn-outline-secondary tap-target" aria-label="Move down" @click="move(index, 1)"><i class="fa-solid fa-arrow-down"></i></button>
                  </div>
                </li>
              </ul>
            </template>
            <div class="card-footer small text-secondary">
              <template v-for="t in ITEM_TYPES" :key="t.value">{{ t.legend }} </template>
            </div>
          </div>
        </div>
      </div>

      <div class="d-flex flex-column flex-md-row flex-wrap justify-content-md-end align-items-stretch align-items-md-center gap-2">
        <div v-if="canEdit && template" class="me-md-auto">
          <span v-if="!template.active">
            <button type="button" class="btn btn-outline-secondary tap-target" :disabled="saving || dirty" @click="setActive(true)">
              <i class="fa-solid fa-rotate-left me-1"></i>Reactivate template
            </button>
          </span>
          <span v-else-if="confirmingDeactivate" class="d-inline-flex flex-wrap align-items-center gap-2" role="alert">
            <span>{{ deactivateQuestion(template.plan_count) }}</span>
            <button type="button" class="btn btn-sm btn-danger tap-target" :disabled="saving" @click="setActive(false)">Yes</button>
            <button type="button" class="btn btn-sm btn-outline-secondary tap-target" @click="confirmingDeactivate = false">No</button>
          </span>
          <button v-else type="button" class="btn btn-outline-danger tap-target" :disabled="saving || dirty" @click="confirmingDeactivate = true">
            <i class="fa-solid fa-ban me-1"></i>Deactivate template
          </button>
          <div v-if="dirty" class="small text-secondary mt-1">Save your changes first, or cancel them</div>
        </div>
        <template v-if="confirmingLeave">
          <span class="fw-semibold" role="alert">Leave without saving? Your changes are lost.</span>
          <button type="button" class="btn btn-danger tap-target" @click="router.push(MASTERS_PATH)">Yes</button>
          <button type="button" class="btn btn-outline-secondary tap-target" @click="confirmingLeave = false">No</button>
        </template>
        <template v-else-if="confirmingSchedule">
          <span class="fw-semibold" role="alert">{{ scheduleChangeQuestion(planCount) }}</span>
          <button type="button" class="btn btn-primary tap-target" :disabled="saving" @click="save">Yes, change the schedule</button>
          <button type="button" class="btn btn-outline-secondary tap-target" @click="confirmingSchedule = false">No</button>
        </template>
        <template v-else-if="canEdit">
          <button type="button" class="btn btn-outline-secondary tap-target" :disabled="saving" @click="cancel">Cancel</button>
          <button type="button" class="btn btn-primary tap-target" :disabled="saving" @click="save">
            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>{{ saving ? "Saving…" : "Save template" }}
          </button>
        </template>
        <router-link v-else :to="MASTERS_PATH" class="btn btn-outline-secondary tap-target">Back to PM templates</router-link>
      </div>

      <p v-if="template" class="small text-secondary mt-3 mb-0" data-testid="pm-stamps">
        Created {{ formatDate(template.created_at) }} by {{ template.created_by_name }}
        <template v-if="template.updated_at"> · Changed {{ formatDate(template.updated_at) }} by {{ template.updated_by_name }}</template>
      </p>

      <PmItemDialog v-if="canEdit" ref="dialog" :meter-types="meterTypes ?? []" @done="onItemDone" @remove="onItemRemove" />
    </template>
  </div>
</template>

<style scoped>
.template-name,
.item-text {
  overflow-wrap: anywhere;
  min-width: 0;
}
.help-text {
  white-space: pre-line;
}
.every-number {
  width: 6rem;
}
.every-unit {
  width: auto;
}
.every-meter {
  width: auto;
  max-width: 100%;
}
.refused-row {
  outline: 2px solid var(--bs-danger);
  outline-offset: -2px;
}
</style>
