<script setup>
/**
 * Settings › Notifications (docs/steps/S021-alerts-push/1-brief.md § 1.6): the escalation time per
 * criticality grade — a breakdown nobody acknowledged escalates to the unit's engineers and
 * managers after it — with each grade's meaning (Maintenance-Philosophy § 9), and whether push is
 * set up on this server. Edited with settings:edit (IT admin), read with settings:read.
 *
 * One Save sends every value on the card in one PUT. The server checks the range and answers on
 * the box (escalate_minutes.A …); a refused save is scrolled into view (S026, revealError).
 */
import { computed, nextTick, onMounted, ref } from "vue";
import { apiGet, apiPut } from "../../api";
import { userPermissions } from "../../stores/auth";
import { revealError } from "../../utils/revealError";

const GRADES = [
  { grade: "A", meaning: "Stops a line or a safety risk" },
  { grade: "B", meaning: "Slows production, repair within the shift" },
  { grade: "C", meaning: "No direct impact" },
];
const MINUTES_MIN = 5;
const MINUTES_MAX = 1440;
const FIELD_PREFIX = "escalate_minutes.";

const canEdit = computed(() => userPermissions.value.includes("settings:edit"));
const stored = ref(null);          // {escalate_minutes: {A, B, C}, push_enabled, devices, email_enabled, email_from}
const inputs = ref({ A: null, B: null, C: null });
const loadError = ref("");
const saveError = ref("");         // a refusal about the whole card
const fieldErrors = ref({});       // grade -> message
const saving = ref(false);
const saved = ref(false);
const form = ref(null);

function show(body) {
  stored.value = body;
  inputs.value = { ...body.escalate_minutes };
}

const changed = computed(
  () => stored.value !== null && GRADES.some(({ grade }) => inputs.value[grade] !== stored.value.escalate_minutes[grade]),
);

async function load() {
  loadError.value = "";
  try {
    show(await apiGet("/api/settings/notifications"));
  } catch (err) {
    loadError.value = err.message;
  }
}

async function save() {
  saving.value = true;
  saveError.value = "";
  fieldErrors.value = {};
  saved.value = false;
  try {
    // An empty box is sent as null; the server refuses it on the box with its message
    const minutes = Object.fromEntries(
      GRADES.map(({ grade }) => [grade, Number.isFinite(inputs.value[grade]) ? inputs.value[grade] : null]),
    );
    show(await apiPut("/api/settings/notifications", { escalate_minutes: minutes }));
    saved.value = true;
  } catch (err) {
    if (err.field?.startsWith(FIELD_PREFIX)) {
      fieldErrors.value = { [err.field.slice(FIELD_PREFIX.length)]: err.message };
    } else {
      saveError.value = err.message;
    }
    await nextTick();
    revealError(form.value);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="card settings-card mt-3">
    <div class="card-header"><i class="fa-solid fa-bell me-2"></i>Notifications</div>
    <div class="card-body">
      <div v-if="loadError" class="alert alert-danger mb-0">{{ loadError }}</div>
      <div v-else-if="!stored" class="text-secondary">Loading…</div>
      <template v-else>
        <p class="mb-3">
          <template v-if="stored.push_enabled">
            <span class="badge text-bg-success me-1">Set up</span>Push notifications work on this server.
            {{ stored.devices }} {{ stored.devices === 1 ? "device has" : "devices have" }} them turned on.
          </template>
          <template v-else>
            <span class="badge text-bg-warning me-1">Not set up</span>Push notifications are not set up on this
            server: the push keys are missing.
          </template>
        </p>
        <!-- S032 § 1.7: the email channel -->
        <p class="mb-3 text-break">
          <template v-if="stored.email_enabled">
            <span class="badge text-bg-success me-1">Set up</span>Email: set up, sent from {{ stored.email_from }}.
          </template>
          <template v-else>
            <span class="badge text-bg-warning me-1">Not set up</span>Email: not set up. Fill the SMTP values in the
            server's secrets.
          </template>
        </p>
        <div class="fw-semibold mb-1">Escalate a breakdown not acknowledged after</div>
        <form v-if="canEdit" ref="form" novalidate @submit.prevent="save">
          <div v-for="{ grade, meaning } in GRADES" :key="grade" class="mb-2">
            <label class="form-label mb-1" :for="`escalate-${grade}`">{{ grade }} — {{ meaning }}</label>
            <div class="input-group escalate-minutes">
              <input
                :id="`escalate-${grade}`"
                v-model.number="inputs[grade]"
                type="number"
                class="form-control"
                :class="{ 'is-invalid': fieldErrors[grade] }"
                :min="MINUTES_MIN"
                :max="MINUTES_MAX"
                step="1"
                @input="saved = false"
              />
              <span class="input-group-text">min</span>
            </div>
            <div v-if="fieldErrors[grade]" class="invalid-feedback d-block">{{ fieldErrors[grade] }}</div>
          </div>
          <div v-if="saveError" class="invalid-feedback d-block">{{ saveError }}</div>
          <div class="form-text">
            From {{ MINUTES_MIN }} to {{ MINUTES_MAX }} minutes after the breakdown is recorded, once, to the unit's
            engineers and managers. A change applies to breakdowns raised after it.
          </div>
          <div class="d-flex align-items-center gap-2 mt-2">
            <button type="submit" class="btn btn-primary" :disabled="saving || !changed">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>Save
            </button>
            <span v-if="saved" class="text-success small">Saved</span>
          </div>
        </form>
        <dl v-else class="row mb-0">
          <template v-for="{ grade, meaning } in GRADES" :key="grade">
            <dt class="col-sm-8">{{ grade }} — {{ meaning }}</dt>
            <dd class="col-sm-4 mb-1">{{ stored.escalate_minutes[grade] }} min</dd>
          </template>
        </dl>
      </template>
    </div>
  </div>
</template>

<style scoped>
.settings-card {
  max-width: 640px;
}
.escalate-minutes {
  max-width: 160px;
}
</style>
