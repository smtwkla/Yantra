<script setup>
/**
 * Assign a person to a ticket (docs/steps/S018-work-tickets/1-brief.md § 1 Assign, § 5.8):
 * a technician, engineer or manager at the ticket's site (the picker's `assignable`), the
 * people already assigned left out, the user's own person first. The API checks the role
 * again; assigning someone twice changes nothing.
 */
import { computed } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import PersonPicker from "./PersonPicker.vue";

const props = defineProps({
  ticket: { type: Object, required: true },
  people: { type: Array, default: () => [] },
  ownPersonId: { type: Number, default: null },
});
const emit = defineEmits(["saved"]);

const { modal, form, saving, dirty, error, fieldError, openCreate, send } = useFormModal({
  path: null,
  blank: () => ({ person_id: null }),
  afterSave: (result) => emit("saved", result),
});

const assigneeIds = computed(() => props.ticket.assignees.map((a) => a.id));
const topError = computed(() => (error.value && error.value.field !== "person_id" ? error.value.message : ""));

function save() {
  if (!form.value.person_id) {
    error.value = { field: "person_id", message: "Choose a person" };
    return;
  }
  return send(() => apiPost(`/api/tickets/${props.ticket.id}/assignees`, { person_id: form.value.person_id }));
}

defineExpose({ open: () => openCreate() });
</script>

<template>
  <FormModal ref="modal" title="Assign" :saving="saving" :dirty="dirty" :error="topError" save-label="Assign" @save="save">
    <label class="form-label" for="assign-person-filter">Who should work on it?</label>
    <PersonPicker
      v-model="form.person_id"
      :people="people"
      :own-person-id="ownPersonId"
      :exclude-ids="assigneeIds"
      assignable-only
      :invalid="Boolean(fieldError('person_id'))"
      id-prefix="assign-person"
    />
    <div v-if="fieldError('person_id')" class="invalid-feedback d-block">{{ fieldError("person_id") }}</div>
  </FormModal>
</template>
