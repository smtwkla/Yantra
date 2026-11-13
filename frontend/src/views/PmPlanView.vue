<script setup>
/**
 * A machine's PM plan (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.10, mock-up 11; S096 before it):
 * `/equipment/pm/<plan id>`, opened from the PM card. The work comes from the plan's template, shown read-only
 * with *Open template*; this page holds only the machine's own settings: *Assign jobs to*, *Last done (before
 * Yantra)*, and the meters the template uses on this machine (read-only, matched by type on the machine's own
 * meters, else the part's meter link: S104 A1). *Save plan* sends the settings; *Remove from this machine* takes
 * the template off the machine (its history stays; attaching it again brings it back). A *Last done* meter value
 * entered for another meter than the plan uses now is not answered by the API and not shown (A1.6.3).
 *
 * Every input and button follows the detail's `can_edit` / `can_remove` (pm_plan:edit at the node's site, the
 * node not scrapped, the plan linked); a reader sees the same cards as text. Leaving through the nav loses unsaved
 * changes without asking, as on Raise ticket (S096 § 9 A5); Cancel asks first.
 */
import { computed, nextTick, provide, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiPost, apiPut } from "../api";
import { formatDate } from "../utils/datetime";
import { FORM_DIRTY } from "../utils/formDirty";
import { formSnapshot } from "../utils/formSnapshot";
import { formatReading } from "../utils/meterLabels";
import {
  itemType, lastDoneHint, meterUseText, personLabel, photoLabel, planSettingsBody, planSettingsForm, templateSummary,
} from "../utils/pmLabels";
import { revealError } from "../utils/revealError";

const WORK_NOTE = "The work comes from the template. To change it for this machine only, attach a template of its own.";

const route = useRoute();
const router = useRouter();

const plan = ref(null); // the detail (§ 6)
const people = ref([]); // GET /api/tickets/people: the site's people, `assignable` marked
const form = ref(null);

const loading = ref(true);
const notFound = ref(false);
const loadError = ref("");
const saving = ref(false);
const error = ref(null); // {field, message} of the last refused save
const confirmingLeave = ref(false);
const confirmingRemove = ref(false);
const pageEl = ref(null);
const snapshot = ref(null);
let loadSeq = 0;

const dirty = computed(() => snapshot.value !== null && formSnapshot(form.value) !== snapshot.value);
provide(FORM_DIRTY, dirty);

const equipment = computed(() => plan.value?.equipment ?? null);
const template = computed(() => plan.value?.template ?? null);
const isOperator = computed(() => template.value?.performer === "operator");
const triggerMeter = computed(() => template.value?.meter_type ?? null);
const assignable = computed(() => people.value.filter((p) => p.assignable));
const lostAssignee = computed(() => {
  const a = plan.value?.assignee;
  if (!plan.value?.can_edit || !a || form.value?.assignee_id !== a.id) return null;
  return assignable.value.some((p) => p.id === a.id) ? null : a;
});
const pathParts = computed(() => (equipment.value ? equipment.value.full_path.split(".") : []));
const equipmentPath = computed(() => (equipment.value ? `/equipment/${equipment.value.id}` : "/equipment"));
const templatePath = computed(() => (template.value ? `/masters/pm-templates/${template.value.id}` : "/masters"));
const PAGE_FIELDS = ["assignee_id", "last_done_on", "last_done_meter"];
const topError = computed(() => (error.value && !PAGE_FIELDS.includes(error.value.field) ? error.value.message : ""));
const fieldError = (name) => (error.value?.field === name ? error.value.message : "");
// The IST date today, the most a "Last done" date may be
const today = computed(() => new Date(Date.now() + 330 * 60_000).toISOString().slice(0, 10));

function markClean() {
  snapshot.value = formSnapshot(form.value);
}

async function load() {
  const id = route.params.id;
  if (id === undefined) return; // the route is changing to another page
  const seq = ++loadSeq;
  loading.value = true;
  notFound.value = false;
  loadError.value = "";
  error.value = null;
  confirmingLeave.value = false;
  confirmingRemove.value = false;
  snapshot.value = null;
  try {
    const loaded = await apiGet(`/api/pm/plans/${id}`);
    if (loaded.can_edit) {
      const answer = await apiGet(`/api/tickets/people?equipment_id=${loaded.equipment.id}`);
      people.value = answer.items;
    }
    if (seq !== loadSeq) return;
    plan.value = loaded;
    form.value = planSettingsForm(loaded);
    await nextTick();
    markClean();
  } catch (err) {
    if (seq !== loadSeq) return;
    if (err.status === 404) notFound.value = true;
    else loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

watch(() => route.params.id, load, { immediate: true });

// A refusal is always in view (S026): post flush, so is-invalid is in the DOM
watch(error, (refusal) => {
  if (refusal) revealError(pageEl.value);
}, { flush: "post" });

async function save() {
  saving.value = true;
  error.value = null;
  try {
    await apiPut(`/api/pm/plans/${plan.value.id}`, planSettingsBody(form.value, plan.value));
  } catch (err) {
    error.value = { field: err.field, message: err.message };
    return;
  } finally {
    saving.value = false;
  }
  markClean();
  router.push(equipmentPath.value);
}

function cancel() {
  if (dirty.value) confirmingLeave.value = true;
  else router.push(equipmentPath.value);
}

async function remove() {
  confirmingRemove.value = false;
  saving.value = true;
  error.value = null;
  try {
    await apiPost(`/api/pm/plans/${plan.value.id}/remove`, {});
  } catch (err) {
    error.value = { field: err.field, message: err.message };
    return;
  } finally {
    saving.value = false;
  }
  await load();
}

const assigneeText = (p) => {
  if (p.template.performer === "operator") return "Operator plans have no assignee.";
  return p.assignee ? personLabel(p.assignee) : "No one yet";
};
const whenText = (p) => {
  const parts = [];
  if (p.last_done_on) parts.push(formatDate(p.last_done_on));
  if (p.last_done_meter !== null && p.template.meter_type) {
    parts.push(`at ${formatReading(p.last_done_meter, p.template.meter_type)}`);
  }
  return parts.length ? parts.join(" ") : "Not known";
};
</script>

<template>
  <div ref="pageEl" class="py-3">
    <div v-if="loading && !plan" class="text-secondary">Loading…</div>
    <div v-else-if="notFound" class="alert alert-warning">
      PM plan not found, or not at your units.
      <router-link to="/equipment" class="alert-link ms-1">Back to the equipment</router-link>
    </div>
    <div v-else-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger tap-target" @click="load">Retry</button>
    </div>

    <template v-else-if="plan">
      <nav class="small mb-2" aria-label="Path">
        <span class="text-secondary">{{ pathParts.slice(0, -1).join(" › ") }} › </span>
        <router-link :to="equipmentPath">{{ equipment.code }}</router-link>
        <span class="text-secondary"> › PM plans</span>
      </nav>
      <div class="d-flex flex-wrap align-items-center gap-2 mb-1">
        <h4 class="mb-0 plan-title">{{ template.name }}</h4>
        <span v-if="!plan.linked" class="badge text-bg-secondary">Removed from this machine</span>
        <span v-else-if="!template.active" class="badge text-bg-secondary">Template inactive</span>
      </div>
      <p class="text-secondary mb-3" data-testid="pm-plan-equipment">{{ equipment.code }} — {{ equipment.name }}</p>
      <div v-if="plan.stop_remark" class="alert alert-secondary py-2" data-testid="pm-stop-remark">
        {{ plan.stop_remark }} This plan makes no jobs.
      </div>
      <div v-if="topError" class="alert alert-danger py-2">{{ topError }}</div>

      <div class="row g-3">
        <div class="col-lg-6">
          <!-- The template's work, read-only -->
          <div class="card mb-3" data-testid="pm-plan-template">
            <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
              <span>Template</span>
              <router-link :to="templatePath" class="btn btn-sm btn-outline-primary tap-target">Open template</router-link>
            </div>
            <div class="card-body">
              <div class="fw-semibold">{{ template.name }}</div>
              <div class="small text-secondary mb-2">{{ templateSummary(template) }}</div>
              <div class="mb-2" data-testid="pm-trigger">{{ template.trigger_text }}</div>
              <div class="small text-secondary mb-2" data-testid="pm-plan-source">{{ plan.linked ? "Attached to this machine" : "Removed from this machine" }}</div>
              <ol class="mb-2 ps-3 small" data-testid="pm-plan-items">
                <li v-for="item in template.items" :key="item.id" class="item-text">
                  <span class="badge me-1" :class="itemType(item.item_type).badge">{{ itemType(item.item_type).label }}</span>{{ item.text }}
                  <span v-if="item.limits_text" class="text-secondary"> · {{ item.limits_text }}</span>
                  <span class="text-secondary"> · Photo: {{ photoLabel(item.photo) }}</span>
                </li>
              </ol>
              <div class="form-text">{{ WORK_NOTE }}</div>
            </div>
          </div>
        </div>

        <div class="col-lg-6">
          <!-- The machine's own settings -->
          <div class="card mb-3">
            <div class="card-header">This machine</div>
            <div class="card-body">
              <div class="mb-3">
                <template v-if="plan.can_edit">
                  <label class="form-label" for="pm-assignee">Assign jobs to</label>
                  <div v-if="isOperator" class="text-secondary">Operator plans have no assignee.</div>
                  <template v-else>
                    <select id="pm-assignee" v-model="form.assignee_id" class="form-select" :class="{ 'is-invalid': fieldError('assignee_id') || lostAssignee }">
                      <option v-if="lostAssignee" :value="lostAssignee.id">{{ lostAssignee.name }} — no longer at this site</option>
                      <option :value="null">No one yet</option>
                      <option v-for="p in assignable" :key="p.id" :value="p.id">{{ personLabel(p) }}</option>
                    </select>
                    <div v-if="lostAssignee && !fieldError('assignee_id')" class="invalid-feedback d-block">Choose another person, or No one yet.</div>
                  </template>
                  <div v-if="fieldError('assignee_id')" class="invalid-feedback d-block">{{ fieldError("assignee_id") }}</div>
                </template>
                <template v-else>
                  <div class="form-label mb-1">Assign jobs to</div>
                  <div>{{ assigneeText(plan) }}</div>
                </template>
              </div>

              <div class="mb-3" data-testid="pm-plan-meters">
                <div class="form-label mb-1">Meters this plan uses</div>
                <div v-if="plan.meters.length === 0" class="text-secondary">None: this template has no meter.</div>
                <div v-for="m in plan.meters" :key="m.meter_type.id">
                  <template v-if="m.equipment">{{ meterUseText(m) }}</template>
                  <template v-else>
                    <span class="text-secondary">Does not apply: no {{ m.meter_type.name }} meter on {{ equipment.code }}</span>
                    <!-- S104 A1.6.7: a part may use the meter of a node above it -->
                    <div v-if="equipment.level !== 'equipment'" class="small" data-testid="pm-plan-link-hint">
                      Add a {{ m.meter_type.name }} meter on {{ equipment.code }}, or use one from a node above (Meters card).
                    </div>
                  </template>
                </div>
              </div>

              <template v-if="plan.can_edit">
                <div class="row g-2">
                  <div class="col-sm-6">
                    <label class="form-label" for="pm-last-on">Last done (before Yantra)</label>
                    <input id="pm-last-on" v-model="form.last_done_on" type="date" class="form-control" :class="{ 'is-invalid': fieldError('last_done_on') }" :max="today" />
                    <div v-if="fieldError('last_done_on')" class="invalid-feedback d-block">{{ fieldError("last_done_on") }}</div>
                  </div>
                  <div v-if="triggerMeter" class="col-sm-6">
                    <label class="form-label" for="pm-last-meter">Meter reading then</label>
                    <div class="input-group">
                      <input id="pm-last-meter" v-model="form.last_done_meter" class="form-control" :class="{ 'is-invalid': fieldError('last_done_meter') }" inputmode="decimal" autocomplete="off" />
                      <span class="input-group-text">{{ triggerMeter.unit }}</span>
                    </div>
                    <div v-if="fieldError('last_done_meter')" class="invalid-feedback d-block">{{ fieldError("last_done_meter") }}</div>
                  </div>
                  <div class="col-12 form-text mt-1" data-testid="pm-last-hint">{{ lastDoneHint() }}</div>
                </div>
              </template>
              <div v-else class="small"><span class="text-secondary">Last done:</span> {{ whenText(plan) }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="d-flex flex-column flex-md-row flex-wrap justify-content-md-end align-items-stretch align-items-md-center gap-2">
        <div v-if="plan.can_remove" class="me-md-auto">
          <span v-if="confirmingRemove" class="d-inline-flex flex-wrap align-items-center gap-2" role="alert">
            <span>Remove this template from {{ equipment.code }}? Its job that has not started is cancelled. Its history stays, and attaching it again brings it back.</span>
            <button type="button" class="btn btn-sm btn-danger tap-target" :disabled="saving" @click="remove">Yes</button>
            <button type="button" class="btn btn-sm btn-outline-secondary tap-target" @click="confirmingRemove = false">No</button>
          </span>
          <button v-else type="button" class="btn btn-outline-danger tap-target" :disabled="saving" @click="confirmingRemove = true">
            Remove from this machine
          </button>
        </div>
        <template v-if="confirmingLeave">
          <span class="fw-semibold" role="alert">Leave without saving? Your changes are lost.</span>
          <button type="button" class="btn btn-danger tap-target" @click="router.push(equipmentPath)">Yes</button>
          <button type="button" class="btn btn-outline-secondary tap-target" @click="confirmingLeave = false">No</button>
        </template>
        <template v-else-if="plan.can_edit">
          <button type="button" class="btn btn-outline-secondary tap-target" :disabled="saving" @click="cancel">Cancel</button>
          <button type="button" class="btn btn-primary tap-target" :disabled="saving" @click="save">
            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>{{ saving ? "Saving…" : "Save plan" }}
          </button>
        </template>
        <router-link v-else :to="equipmentPath" class="btn btn-outline-secondary tap-target">Back to the equipment</router-link>
      </div>

      <p class="small text-secondary mt-3 mb-0" data-testid="pm-stamps">
        Attached {{ formatDate(plan.created_at) }} by {{ plan.created_by_name }}
        <template v-if="plan.updated_at"> · Changed {{ formatDate(plan.updated_at) }} by {{ plan.updated_by_name }}</template>
      </p>
    </template>
  </div>
</template>

<style scoped>
.plan-title,
.item-text {
  overflow-wrap: anywhere;
  min-width: 0;
}
</style>
