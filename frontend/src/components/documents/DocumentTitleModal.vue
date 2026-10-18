<script setup>
/**
 * Edit-title dialog for a document or photo (docs/steps/S006-equipment-documents/1-brief.md § 5.8).
 * Sends only `title`: the file, kind and owner never change.
 *
 * The parent calls open(doc) through a template ref and handles @saved, and passes the
 * owner's documents collection URL (a node or a model: S012).
 */
import { apiPut } from "../../api";
import FormModal from "../FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";

const props = defineProps({
  basePath: { type: String, required: true },
});
const emit = defineEmits(["saved"]);

const TITLE_MAX = 200;

// The path depends on the owner, which can change while this component is reused, so the
// PUT goes through send() rather than useFormModal's fixed-path save()
const { modal, form, editingId, saving, dirty, fieldError, modalError, openEdit, send } = useFormModal({
  path: null,
  blank: () => ({ title: "" }),
  fromRecord: (doc) => ({ title: doc.title }),
  afterSave: (result) => emit("saved", result),
  label: (doc) => doc.title,
});

function save() {
  return send(() => apiPut(`${props.basePath}/${editingId.value}`, { title: form.value.title }));
}

defineExpose({ open: openEdit });
</script>

<template>
  <FormModal ref="modal" title="Edit title" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
    <div class="mb-0">
      <label class="form-label" for="doc-edit-title">Title</label>
      <input
        id="doc-edit-title"
        v-model="form.title"
        class="form-control"
        :class="{ 'is-invalid': fieldError('title') }"
        :maxlength="TITLE_MAX"
      />
      <div class="invalid-feedback">{{ fieldError("title") }}</div>
    </div>
  </FormModal>
</template>
