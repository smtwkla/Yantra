<script setup>
/**
 * The dialog *Add note* (docs/steps/S073-verified-close-screens/1-brief.md § 5.6): a note on the
 * improvement's timeline. Not the ticket's NoteDialog, which is bound to a ticket and its
 * correction (D6). A closed improvement's 409 shows at the top and asks the page to reload.
 */
import { watch } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { NOTE_MAX } from "../../utils/improvementLabels";

const props = defineProps({
  improvement: { type: Object, required: true },
});
const emit = defineEmits(["saved", "reload"]);

const { modal, form, saving, dirty, error, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: () => ({ remark: "" }),
  afterSave: (result) => emit("saved", result),
});

watch(error, (value) => {
  if (value && !value.field && value.status === 409) emit("reload");
});

function open() {
  openCreate();
}

function save() {
  return send(() => apiPost(`/api/improvements/${props.improvement.id}/notes`, { remark: form.value.remark }));
}

defineExpose({ open });
</script>

<template>
  <FormModal ref="modal" title="Add note" :saving="saving" :dirty="dirty" :error="modalError" save-label="Save note" @save="save">
    <div class="mb-3">
      <label class="form-label" for="improvement-note">Note</label>
      <textarea
        id="improvement-note"
        v-model="form.remark"
        class="form-control"
        :class="{ 'is-invalid': fieldError('remark') }"
        rows="4"
        :maxlength="NOTE_MAX"
        aria-describedby="improvement-note-help"
        autofocus
      ></textarea>
      <div v-if="fieldError('remark')" class="invalid-feedback d-block">{{ fieldError("remark") }}</div>
      <div id="improvement-note-help" class="form-text">What you saw or know, for example the same dust on another panel.</div>
    </div>
  </FormModal>
</template>
