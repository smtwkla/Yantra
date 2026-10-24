<script setup>
/**
 * Log reading (S039 § 1.3): one reading of one meter of a node.
 * - A number meter: Value with its unit beside it and the phone's decimal keypad; an amount
 *   explains its period; a counter has Meter reset.
 * - A Yes / No meter: its question as the title and two large toggles, Yes and No. The user
 *   picks, then saves with the dialog's Save (decision 11), so a note typed after the answer is
 *   kept and a mis-tap is corrected before saving.
 * - Time taken is "Now · Change" (EventFields): Now sends no taken_at, so the server's clock
 *   decides and a phone a few minutes off is never refused.
 *
 * The rules are the server's (meters_core): a refusal shows beside its field. With the database
 * down or no network the typed values stay and the dialog says to try again (§ 5.5).
 *
 * The parent calls open(node, meter) through a template ref and handles @saved({ meter, reading }).
 */
import { computed, ref } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { formatDateTime } from "../../utils/datetime";
import { formatReading, notSavedOr } from "../../utils/meterLabels";
import EventFields from "../tickets/EventFields.vue";

const NOTE_MAX = 200; // meters_core.NOTE_MAX

const emit = defineEmits(["saved"]);

const node = ref(null);
const meter = ref(null);

const { modal, form, saving, dirty, fieldError, modalError, openCreate, send } = useFormModal({
  path: "/api/equipment",
  blank: () => ({ value: "", taken_at: null, is_reset: false, note: "" }),
  fromRecord: () => ({}), // a reading is never edited, only removed (§ 7 decision 5)
  afterSave: (reading) => emit("saved", { meter: meter.value, reading }),
});

const meterType = computed(() => meter.value?.meter_type ?? null);
const kind = computed(() => meterType.value?.kind);
const title = computed(() => {
  if (!meterType.value) return "Log reading";
  // A Yes / No meter's name is its question (S037), so it is the heading
  return kind.value === "yes_no" ? meterType.value.name : `Log reading · ${meterType.value.name}`;
});
const lastLine = computed(() => {
  const last = meter.value?.last;
  if (!last) return "";
  return `Last reading: ${formatReading(last.value, meterType.value)} on ${formatDateTime(last.taken_at)}`;
});
const saveDisabledReason = computed(() => (kind.value === "yes_no" && !form.value.value ? "Pick Yes or No" : ""));

function open(target, targetMeter) {
  node.value = target;
  meter.value = targetMeter;
  openCreate();
}

function save() {
  const body = {
    meter_type_id: meterType.value.id,
    value: typeof form.value.value === "string" ? form.value.value.trim() : form.value.value,
    is_reset: kind.value === "counter" && form.value.is_reset,
    note: form.value.note.trim() || null,
  };
  if (form.value.taken_at) body.taken_at = form.value.taken_at;
  return send(async () => {
    try {
      return await apiPost(`/api/equipment/${node.value.id}/readings`, body);
    } catch (err) {
      throw notSavedOr(err);
    }
  });
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    :title="title"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :save-disabled-reason="saveDisabledReason"
    @save="save"
  >
    <p class="text-secondary small">
      {{ node?.code }} — {{ node?.name }}
      <template v-if="lastLine"><br />{{ lastLine }}</template>
    </p>

    <div v-if="kind === 'yes_no'" class="mb-3">
      <div class="d-flex gap-2" role="group" :aria-label="meterType.name">
        <button
          v-for="answer in ['yes', 'no']"
          :key="answer"
          type="button"
          class="btn btn-lg flex-fill answer-button"
          :class="form.value === answer ? 'btn-primary' : 'btn-outline-primary'"
          :aria-pressed="form.value === answer"
          @click="form.value = answer"
        >
          {{ answer === "yes" ? "Yes" : "No" }}
        </button>
      </div>
      <div v-if="fieldError('value')" class="invalid-feedback d-block">{{ fieldError("value") }}</div>
    </div>
    <div v-else-if="meterType" class="mb-3">
      <label class="form-label" for="reading-value">Value</label>
      <div class="input-group">
        <input
          id="reading-value"
          v-model="form.value"
          class="form-control"
          :class="{ 'is-invalid': fieldError('value') }"
          inputmode="decimal"
          autocomplete="off"
          autofocus
        />
        <span class="input-group-text">{{ meterType.unit }}</span>
      </div>
      <div v-if="fieldError('value')" class="invalid-feedback d-block">{{ fieldError("value") }}</div>
      <div v-if="kind === 'amount'" class="form-text">The amount for the period just ended, such as this shift.</div>
    </div>

    <EventFields
      v-model:time="form.taken_at"
      :with-remark="false"
      time-label="Time taken"
      :time-error="fieldError('taken_at')"
      id-prefix="reading"
    />

    <div v-if="kind === 'counter'" class="mb-3">
      <div class="form-check">
        <input id="reading-reset" v-model="form.is_reset" class="form-check-input" :class="{ 'is-invalid': fieldError('is_reset') }" type="checkbox" />
        <label class="form-check-label" for="reading-reset">Meter reset</label>
      </div>
      <div class="form-text">Tick this only when the meter was replaced or set back to zero</div>
      <div v-if="fieldError('is_reset')" class="invalid-feedback d-block">{{ fieldError("is_reset") }}</div>
    </div>

    <div class="mb-3">
      <label class="form-label" for="reading-note">Note</label>
      <input
        id="reading-note"
        v-model="form.note"
        class="form-control"
        :class="{ 'is-invalid': fieldError('note') }"
        :maxlength="NOTE_MAX"
        autocomplete="off"
      />
      <div v-if="fieldError('note')" class="invalid-feedback d-block">{{ fieldError("note") }}</div>
    </div>
  </FormModal>
</template>

<style scoped>
/* A thumb on a phone (U3): at least 48 px high */
.answer-button {
  min-height: 48px;
}
</style>
