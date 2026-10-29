<script setup>
/**
 * Root cause (docs/steps/S069-improvement-why-why/1-brief.md § 5.7): the text, one cause of the
 * failure-cause list (ISO 14224's five groups, the list the tickets use) and the other causes.
 * With no root cause yet, the text starts as the last why's answer (TPM: the chain ends at the
 * root cause; D5). A cause that was deactivated after it was chosen stays in the list, last.
 */
import { computed, ref } from "vue";
import { apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { CAUSE_GROUPS, ensureFailureCauses, failureCauses } from "../../stores/masters";
import { CONTRIBUTING_MAX, defaultRootCause, ROOT_CAUSE_MAX } from "../../utils/improvementLabels";

const props = defineProps({
  improvement: { type: Object, required: true },
});
const emit = defineEmits(["saved"]);

const loadError = ref("");

const { modal, form, saving, dirty, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  // useFormModal calls blank() with no seed at set-up: every field is then an empty string
  blank: (seed = {}) => ({
    root_cause: seed.improvement?.root_cause?.text ?? defaultRootCause(seed.improvement?.whys ?? []),
    root_cause_id: seed.improvement?.root_cause?.cause.id ?? "",
    contributing_causes: seed.improvement?.contributing_causes ?? "",
  }),
  afterSave: (result) => emit("saved", result),
});

const topError = computed(() => modalError.value || loadError.value);
const stored = computed(() => props.improvement.root_cause?.cause ?? null);
const causeGroups = computed(() => CAUSE_GROUPS
  .map((g) => ({ label: g.label, causes: (failureCauses.value ?? []).filter((c) => c.active && c.cause_group === g.value) }))
  .filter((g) => g.causes.length));

async function open() {
  loadError.value = "";
  openCreate({ improvement: props.improvement });
  try {
    await ensureFailureCauses();
  } catch (err) {
    loadError.value = `The list of causes could not be loaded: ${err.message}`;
  }
}

function save() {
  const f = form.value;
  return send(() => apiPut(`/api/improvements/${props.improvement.id}/root-cause`, {
    root_cause: f.root_cause,
    root_cause_id: f.root_cause_id === "" ? null : Number(f.root_cause_id),
    contributing_causes: f.contributing_causes.trim() ? f.contributing_causes : null,
  }));
}

defineExpose({ open });
</script>

<template>
  <FormModal ref="modal" title="Root cause" :saving="saving" :dirty="dirty" :error="topError" save-label="Save root cause" @save="save">
    <div class="mb-3">
      <label class="form-label" for="root-cause-text">Root cause</label>
      <textarea
        id="root-cause-text"
        v-model="form.root_cause"
        class="form-control"
        :class="{ 'is-invalid': fieldError('root_cause') }"
        rows="3"
        :maxlength="ROOT_CAUSE_MAX"
        aria-describedby="root-cause-text-help"
      ></textarea>
      <div v-if="fieldError('root_cause')" class="invalid-feedback d-block">{{ fieldError("root_cause") }}</div>
      <div id="root-cause-text-help" class="form-text">What the plant can change. Often the last answer of the why-why.</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="root-cause-cause">Cause</label>
      <select id="root-cause-cause" v-model="form.root_cause_id" class="form-select" :class="{ 'is-invalid': fieldError('root_cause_id') }">
        <option value="">Choose the cause</option>
        <optgroup v-for="g in causeGroups" :key="g.label" :label="g.label">
          <option v-for="c in g.causes" :key="c.id" :value="c.id">{{ c.code }} {{ c.label }}</option>
        </optgroup>
        <option v-if="stored && !stored.active" :value="stored.id">{{ stored.code }} {{ stored.label }} (inactive)</option>
      </select>
      <div v-if="fieldError('root_cause_id')" class="invalid-feedback d-block">{{ fieldError("root_cause_id") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="root-cause-other">Other causes (optional)</label>
      <textarea
        id="root-cause-other"
        v-model="form.contributing_causes"
        class="form-control"
        :class="{ 'is-invalid': fieldError('contributing_causes') }"
        rows="3"
        :maxlength="CONTRIBUTING_MAX"
        aria-describedby="root-cause-other-help"
      ></textarea>
      <div v-if="fieldError('contributing_causes')" class="invalid-feedback d-block">{{ fieldError("contributing_causes") }}</div>
      <div id="root-cause-other-help" class="form-text">Causes that helped, but are not the root.</div>
    </div>
  </FormModal>
</template>
