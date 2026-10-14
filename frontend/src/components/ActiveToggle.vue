<script setup>
/**
 * ActiveToggle — Deactivate / Reactivate button for the footer of a master's edit dialog.
 *
 * Deactivating hides the record from pick-lists, so it asks first, inline
 * ("Deactivate X? Yes / No") rather than with a browser confirm(). Reactivating
 * needs no confirmation. The parent owns the state (see useMasterForm).
 */
defineProps({
  active: { type: Boolean, required: true },
  label: { type: String, required: true },
  confirming: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});
defineEmits(["ask", "cancel", "change"]);
</script>

<template>
  <button v-if="!active" type="button" class="btn btn-outline-secondary" :disabled="disabled" @click="$emit('change', true)">
    <i class="fa-solid fa-rotate-left me-1"></i>Reactivate
  </button>
  <span v-else-if="confirming" class="d-inline-flex align-items-center gap-2">
    <span>Deactivate <strong>{{ label }}</strong>?</span>
    <button type="button" class="btn btn-sm btn-danger" :disabled="disabled" @click="$emit('change', false)">Yes</button>
    <button type="button" class="btn btn-sm btn-outline-secondary" @click="$emit('cancel')">No</button>
  </span>
  <button v-else type="button" class="btn btn-outline-danger" :disabled="disabled" @click="$emit('ask')">
    <i class="fa-solid fa-ban me-1"></i>Deactivate
  </button>
</template>
