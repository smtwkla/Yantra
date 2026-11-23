<script setup>
/**
 * The inline cancel of a row (S107 § 5.4, D3; taken out of S071's CountermeasureItem): the
 * question, "Why cancel it?" with a help line, the confirm button and "Keep it". No dialog, so no
 * FormModal "Cancel" stands beside "Cancel …" (S071 D7).
 *
 * The row mounts it while it asks (v-if), so each ask starts with an empty reason and the field
 * focused. It holds the reason and makes no call: it emits `cancel(reason)` (trimmed) and `keep`;
 * the page sends the call and passes `busy` and `error` ({field, message} of the last refusal: a
 * `reason` refusal under the field, any other under the buttons).
 */
import { computed, nextTick, onMounted, ref } from "vue";
import { CANCEL_REASON_MAX } from "../utils/improvementLabels";

const props = defineProps({
  question: { type: String, required: true },
  help: { type: String, required: true },
  confirmLabel: { type: String, required: true },
  busy: { type: Boolean, default: false },
  error: { type: Object, default: null },
  // Makes the field's id unique on the page: cancel-reason-<idSuffix>
  idSuffix: { type: [String, Number], required: true },
});
const emit = defineEmits(["cancel", "keep"]);

const reason = ref("");
const reasonField = ref(null);
const reasonId = computed(() => `cancel-reason-${props.idSuffix}`);
const reasonError = computed(() => (props.error?.field === "reason" ? props.error.message : ""));
const rowError = computed(() => (props.error && props.error.field !== "reason" ? props.error.message : ""));

onMounted(() => nextTick(() => reasonField.value?.focus()));
</script>

<template>
  <div class="mt-2">
    <p class="mb-2">{{ question }}</p>
    <label class="form-label" :for="reasonId">Why cancel it?</label>
    <textarea
      :id="reasonId"
      ref="reasonField"
      v-model="reason"
      class="form-control"
      :class="{ 'is-invalid': reasonError }"
      rows="2"
      :maxlength="CANCEL_REASON_MAX"
    ></textarea>
    <div v-if="reasonError" class="invalid-feedback d-block">{{ reasonError }}</div>
    <div class="form-text">{{ help }}</div>
    <div class="d-flex flex-wrap justify-content-end gap-2 mt-2">
      <button type="button" class="btn btn-danger" :disabled="busy || !reason.trim()" @click="emit('cancel', reason.trim())">
        {{ confirmLabel }}
      </button>
      <button type="button" class="btn btn-outline-secondary" :disabled="busy" @click="emit('keep')">Keep it</button>
    </div>
    <div v-if="rowError" class="alert alert-danger py-2 mt-2 mb-0">{{ rowError }}</div>
  </div>
</template>
