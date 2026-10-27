<script setup>
/**
 * ActiveToggle — Deactivate / Reactivate button for the footer of a master's edit dialog.
 *
 * Deactivating hides the record from pick-lists, so it asks first, inline
 * ("Deactivate X? Yes / No") rather than with a browser confirm(). Reactivating
 * needs no confirmation. The parent owns the state (see useMasterForm).
 *
 * Both close the dialog after their own save (useMasterForm.changeActive sends only {active}),
 * so while the surrounding FormModal has unsaved changes both are blocked, with the reason as
 * text (S064 UX-16).  Outside a FormModal nothing is injected and the form counts as clean.
 */
import { computed, inject } from "vue";
import { FORM_DIRTY } from "../utils/formDirty";

defineProps({
  active: { type: Boolean, required: true },
  label: { type: String, required: true },
  confirming: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});
defineEmits(["ask", "cancel", "change"]);

const dirty = inject(FORM_DIRTY, computed(() => false));
</script>

<template>
  <span v-if="!active" class="d-inline-flex flex-wrap align-items-center gap-2">
    <button type="button" class="btn btn-outline-secondary" :disabled="disabled || dirty" @click="$emit('change', true)">
      <i class="fa-solid fa-rotate-left me-1"></i>Reactivate
    </button>
    <span v-if="dirty" class="small text-secondary">Save your changes first, or cancel them</span>
  </span>
  <span v-else-if="confirming" class="d-inline-flex flex-wrap align-items-center gap-2">
    <span>Deactivate <strong>{{ label }}</strong>?</span>
    <button type="button" class="btn btn-sm btn-danger" :disabled="disabled || dirty" @click="$emit('change', false)">Yes</button>
    <button type="button" class="btn btn-sm btn-outline-secondary" @click="$emit('cancel')">No</button>
  </span>
  <span v-else class="d-inline-flex flex-wrap align-items-center gap-2">
    <button type="button" class="btn btn-outline-danger" :disabled="disabled || dirty" @click="$emit('ask')">
      <i class="fa-solid fa-ban me-1"></i>Deactivate
    </button>
    <span v-if="dirty" class="small text-secondary">Save your changes first, or cancel them</span>
  </span>
</template>
