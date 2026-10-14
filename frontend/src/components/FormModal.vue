<script setup>
/**
 * FormModal — a Bootstrap modal around a form, shared by the masters panels.
 *
 * The parent calls open()/close() through a template ref, puts the fields in
 * the default slot, and handles @save. `error` is a message not tied to one
 * field; field messages are shown by the fields themselves.
 */
import { onBeforeUnmount, onMounted, ref } from "vue";
import { Modal } from "bootstrap";

defineProps({
  title: { type: String, required: true },
  saving: { type: Boolean, default: false },
  error: { type: String, default: "" },
});
defineEmits(["save"]);

const el = ref(null);
let modal = null;

onMounted(() => {
  modal = Modal.getOrCreateInstance(el.value);
});
onBeforeUnmount(() => {
  modal?.dispose();
});

defineExpose({
  open: () => modal.show(),
  close: () => modal.hide(),
});
</script>

<template>
  <div ref="el" class="modal fade" tabindex="-1">
    <div class="modal-dialog">
      <form class="modal-content" novalidate @submit.prevent="$emit('save')">
        <div class="modal-header">
          <h5 class="modal-title">{{ title }}</h5>
          <button type="button" class="btn-close" aria-label="Close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
          <slot />
        </div>
        <div class="modal-footer">
          <div class="me-auto"><slot name="footer-left" /></div>
          <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="saving">
            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>Save
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
