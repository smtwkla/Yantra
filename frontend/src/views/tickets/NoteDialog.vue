<script setup>
/**
 * Add or correct a work note (docs/steps/S027-work-notes/1-brief.md § 1.2, § 1.5): what was
 * found and tried, one text field.
 * - openAdd(): *Add note*, Save *Save note* — POST /api/tickets/<id>/notes;
 * - openEdit(note): *Edit note*, filled with the note's text, with the hint that steers new
 *   findings into a new note; Save *Save changes* — PUT /api/tickets/<id>/notes/<event_id>.
 * The API decides every refusal; the field's own ones show under it. A closed ticket (409,
 * no field) shows at the top, and the page behind reloads, as in MoveDialog.
 */
import { computed, ref, watch } from "vue";
import { apiPost, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";

const props = defineProps({
  ticket: { type: Object, required: true },
});
const emit = defineEmits(["saved", "reload"]);

const NOTE_MAX = 1000; // ticket_events.remark

const editingNote = ref(null); // the event being corrected; null when adding

const { modal, form, saving, dirty, error, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: (seed) => ({ remark: "", ...seed }),
  afterSave: (result) => emit("saved", result),
});

const editing = computed(() => editingNote.value !== null);

watch(error, (value) => {
  if (value && !value.field && value.status === 409) emit("reload");
});

function openAdd() {
  editingNote.value = null;
  openCreate();
}

function openEdit(note) {
  editingNote.value = note;
  openCreate({ remark: note.remark ?? "" });
}

function save() {
  const base = `/api/tickets/${props.ticket.id}/notes`;
  const body = { remark: form.value.remark };
  return send(() => (editing.value ? apiPut(`${base}/${editingNote.value.id}`, body) : apiPost(base, body)));
}

defineExpose({ openAdd, openEdit });
</script>

<template>
  <FormModal
    ref="modal"
    :title="editing ? 'Edit note' : 'Add note'"
    :save-label="editing ? 'Save changes' : 'Save note'"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    @save="save"
  >
    <p v-if="editing" class="text-secondary">Fix a typo or wrong information here. To record new findings, add a note.</p>
    <div class="mb-3">
      <label class="form-label" for="note-text">Note</label>
      <textarea
        id="note-text"
        v-model="form.remark"
        class="form-control"
        :class="{ 'is-invalid': fieldError('remark') }"
        rows="4"
        :maxlength="NOTE_MAX"
        autofocus
      ></textarea>
      <div v-if="fieldError('remark')" class="invalid-feedback d-block">{{ fieldError("remark") }}</div>
    </div>
  </FormModal>
</template>
