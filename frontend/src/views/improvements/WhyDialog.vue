<script setup>
/**
 * Add why / Edit why (docs/steps/S069-improvement-why-why/1-brief.md § 5.7): one dialog on one
 * useFormModal. The answer of the line above shows over the fields, so the engineer writes the
 * next "why" from it on a phone without scrolling the page (TPM why-why). An edit also offers
 * the place in the chain. The API judges every rule; the 20-whys refusal has no field and shows
 * at the top.
 */
import { computed, ref } from "vue";
import { apiPost, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ANSWER_MAX, EVIDENCE_MAX, QUESTION_MAX, whyBody } from "../../utils/improvementLabels";

const props = defineProps({
  improvement: { type: Object, required: true },
});
const emit = defineEmits(["saved"]);

const previousAnswer = ref(""); // the answer of the line above, "" for the first line
let openedPosition = null; // the place the edit opened with; position is sent only when it changed

const { modal, form, editingId, saving, dirty, fieldError, modalError, openCreate, openEdit, send } = useFormModal({
  path: null,
  // useFormModal calls blank() with no seed at set-up: every field is then an empty string
  blank: () => ({ question: "", answer: "", evidence: "" }),
  fromRecord: (why) => ({ question: why.question, answer: why.answer, evidence: why.evidence ?? "", position: why.position }),
  afterSave: (result) => emit("saved", result),
});

const isEdit = computed(() => editingId.value !== null);
const count = computed(() => props.improvement.whys.length);

function openAdd() {
  previousAnswer.value = props.improvement.whys.at(-1)?.answer ?? "";
  openCreate();
}

function openChange(why) {
  const above = props.improvement.whys.find((w) => w.position === why.position - 1);
  previousAnswer.value = above?.answer ?? "";
  openedPosition = why.position;
  openEdit(why);
}

function save() {
  const base = `/api/improvements/${props.improvement.id}/whys`;
  const body = whyBody(form.value, isEdit.value, openedPosition);
  if (isEdit.value) return send(() => apiPut(`${base}/${editingId.value}`, body));
  return send(() => apiPost(base, body));
}

defineExpose({ openAdd, openChange });
</script>

<template>
  <FormModal
    ref="modal"
    :title="isEdit ? 'Edit why' : 'Add why'"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :save-label="isEdit ? 'Save why' : 'Add why'"
    @save="save"
  >
    <p v-if="previousAnswer" class="text-secondary text-break mb-3" data-testid="why-previous">Because: {{ previousAnswer }}</p>
    <div class="mb-3">
      <label class="form-label" for="why-question">Why?</label>
      <textarea
        id="why-question"
        v-model="form.question"
        class="form-control"
        :class="{ 'is-invalid': fieldError('question') }"
        rows="2"
        :maxlength="QUESTION_MAX"
        placeholder="Why did the press not start?"
      ></textarea>
      <div v-if="fieldError('question')" class="invalid-feedback d-block">{{ fieldError("question") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="why-answer">Because</label>
      <textarea
        id="why-answer"
        v-model="form.answer"
        class="form-control"
        :class="{ 'is-invalid': fieldError('answer') }"
        rows="3"
        :maxlength="ANSWER_MAX"
      ></textarea>
      <div v-if="fieldError('answer')" class="invalid-feedback d-block">{{ fieldError("answer") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="why-evidence">Evidence (optional)</label>
      <input
        id="why-evidence"
        v-model="form.evidence"
        class="form-control"
        :class="{ 'is-invalid': fieldError('evidence') }"
        type="text"
        :maxlength="EVIDENCE_MAX"
        aria-describedby="why-evidence-help"
      />
      <div v-if="fieldError('evidence')" class="invalid-feedback d-block">{{ fieldError("evidence") }}</div>
      <div id="why-evidence-help" class="form-text">What you saw or measured: a photo, a reading, a part.</div>
    </div>
    <div v-if="isEdit && count > 1" class="mb-3">
      <label class="form-label" for="why-position">Place in the chain</label>
      <select id="why-position" v-model="form.position" class="form-select" :class="{ 'is-invalid': fieldError('position') }">
        <option v-for="n in count" :key="n" :value="n">{{ n }}</option>
      </select>
      <div v-if="fieldError('position')" class="invalid-feedback d-block">{{ fieldError("position") }}</div>
    </div>
  </FormModal>
</template>
