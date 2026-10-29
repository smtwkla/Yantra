<script setup>
/**
 * The dialog *Drop improvement* (docs/steps/S073-verified-close-screens/1-brief.md § 5.5): the
 * reason and the consequence. Final: the open countermeasures are cancelled with it. The submit
 * is FormModal's standard button; the red is on the page's button and in the consequence line.
 */
import { watch } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { CLOSE_REMARK_MAX } from "../../utils/improvementLabels";

const props = defineProps({
  improvement: { type: Object, required: true },
});
const emit = defineEmits(["saved", "reload"]);

const { modal, form, saving, dirty, error, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: () => ({ reason: "" }),
  afterSave: (result) => emit("saved", result),
});

watch(error, (value) => {
  if (value && !value.field && value.status === 409) emit("reload");
});

function open() {
  openCreate();
}

function save() {
  return send(() => apiPost(`/api/improvements/${props.improvement.id}/drop`, { reason: form.value.reason }));
}

defineExpose({ open });
</script>

<template>
  <FormModal ref="modal" title="Drop improvement" :saving="saving" :dirty="dirty" :error="modalError" save-label="Drop improvement" @save="save">
    <p class="fw-semibold text-danger">
      Drop {{ improvement.serial }}? Its open countermeasures are cancelled. You cannot undo this.
    </p>
    <div class="mb-3">
      <label class="form-label" for="drop-reason">Why drop it?</label>
      <textarea
        id="drop-reason"
        v-model="form.reason"
        class="form-control"
        :class="{ 'is-invalid': fieldError('reason') }"
        rows="3"
        :maxlength="CLOSE_REMARK_MAX"
        aria-describedby="drop-reason-help"
      ></textarea>
      <div v-if="fieldError('reason')" class="invalid-feedback d-block">{{ fieldError("reason") }}</div>
      <div id="drop-reason-help" class="form-text">For example: started by mistake, or the same problem is analysed in IM-…</div>
    </div>
  </FormModal>
</template>
