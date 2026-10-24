<script setup>
/**
 * FormModal — a Bootstrap modal around a form, shared by the masters panels and the equipment dialogs.
 *
 * The parent calls open()/close() through a template ref, puts the fields in
 * the default slot, and handles @save. `error` is a message not tied to one
 * field; field messages are shown by the fields themselves.
 *
 * Typed input is never lost by accident (docs/steps/S007-dialog-guard-deploy-fixes/1-brief.md § 5.1):
 * a click outside does not close the dialog, and when the parent says the form is `dirty`,
 * Esc / ✕ / Cancel ask "Discard your changes?" in the footer first. Every close passes
 * one gate, the cancellable `hide.bs.modal` event; close() (after a successful save) and
 * Discard are the only ways past it.
 *
 * The cursor starts in the first field marked `autofocus` (S027 § 1.2): Bootstrap ignores the
 * attribute in a modal and focuses the modal itself at the end of the open fade, then fires
 * `shown.bs.modal`, where the field takes the focus (inside the focus trap, so it stays).
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Modal } from "bootstrap";
import { revealError } from "../utils/revealError";

const props = defineProps({
  title: { type: String, required: true },
  saving: { type: Boolean, default: false },
  error: { type: String, default: "" },
  // When set, Save is disabled and the reason shows as its tooltip
  saveDisabledReason: { type: String, default: "" },
  // The submit button's text, e.g. "Upload"
  saveLabel: { type: String, default: "Save" },
  // The form differs from how it was when the dialog opened (the parent compares)
  dirty: { type: Boolean, default: false },
  // Nothing to save (S035: a class with no properties yet): the footer shows only Close
  closeOnly: { type: Boolean, default: false },
});
const emit = defineEmits(["save"]);

const el = ref(null);
const keepEditingButton = ref(null);
const confirming = ref(false); // the "Discard your changes?" bar replaces the footer buttons
let modal = null;
let allowHide = false; // set only around our own hide() calls
let visible = false; // from open() until Bootstrap's hidden event: the dialog is shown or still closing
let focusBeforeConfirm = null;

// Bootstrap's cancellable event; prevented, hide() stops there (no shake, no focus change)
function onHide(event) {
  if (allowHide) return;
  if (props.saving) {
    event.preventDefault();
  } else if (confirming.value) {
    // Only Esc gets here (✕ is disabled while the bar shows): Esc means Keep editing
    event.preventDefault();
    keepEditing();
  } else if (props.dirty) {
    event.preventDefault();
    askToDiscard();
  }
}

// Focus moves wait for nextTick (the bar is rendered or removed by then). A removed focused
// button sends the focus to <body>, where Esc would no longer reach Bootstrap's listener on
// the dialog, so fall back to the dialog itself.
function focusOrDialog(target) {
  if (target && el.value.contains(target)) target.focus();
  if (!el.value.contains(document.activeElement)) el.value.focus();
}

function askToDiscard() {
  focusBeforeConfirm = document.activeElement;
  confirming.value = true;
  nextTick(() => focusOrDialog(keepEditingButton.value));
}

function keepEditing() {
  confirming.value = false;
  nextTick(() => focusOrDialog(focusBeforeConfirm));
}

// hide() returns without firing the event while a transition runs, so the flag is
// cleared here and not in the event handler
function hideNow() {
  allowHide = true;
  try {
    modal.hide();
  } finally {
    allowHide = false;
  }
}

// A refusal is always in view (S026): scroll the first message into view and focus its field.
// Called by useFormModal on its own error state, and below for the top bar's `error` prop.
function reveal() {
  revealError(el.value?.querySelector(".modal-body"));
}

// post flush: the message and its is-invalid class are in the DOM when the search runs
watch(() => props.error, (message) => {
  if (message) reveal();
}, { flush: "post" });

function focusAutofocusField() {
  el.value.querySelector(".modal-body [autofocus]")?.focus();
}

function onSubmit() {
  if (!confirming.value && !props.closeOnly) emit("save");
}

onMounted(() => {
  modal = Modal.getOrCreateInstance(el.value, { backdrop: "static" });
  // addEventListener, not a template @hide.bs.modal: Vue would read that as the event "hide" with modifiers
  el.value.addEventListener("hide.bs.modal", onHide);
  el.value.addEventListener("shown.bs.modal", focusAutofocusField);
  el.value.addEventListener("hidden.bs.modal", () => {
    visible = false;
  });
});
// A page that navigates away right after close() unmounts this component while the dialog is
// still fading out; disposing then makes Bootstrap's pending callback fail on a null element
// ("Cannot read properties of null (reading 'style')").  So a dialog that is still visible is
// closed and disposed only once Bootstrap says it is hidden.
onBeforeUnmount(() => {
  const element = el.value;
  const instance = modal;
  if (!instance) return;
  if (!visible) {
    element.removeEventListener("hide.bs.modal", onHide);
    instance.dispose();
    return;
  }
  element.addEventListener(
    "hidden.bs.modal",
    () => {
      element.removeEventListener("hide.bs.modal", onHide);
      instance.dispose();
    },
    { once: true },
  );
  hideNow();
});

defineExpose({
  open: () => {
    confirming.value = false;
    visible = true;
    modal.show();
  },
  close: hideNow,
  revealError: reveal,
});
</script>

<template>
  <div ref="el" class="modal fade" tabindex="-1">
    <!-- Scrollable: the body scrolls, header and footer (Save) stay on a phone's screen (S018 BR3-03) -->
    <div class="modal-dialog modal-dialog-scrollable">
      <form class="modal-content" novalidate @submit.prevent="onSubmit">
        <div class="modal-header">
          <h5 class="modal-title">{{ title }}</h5>
          <button
            type="button"
            class="btn-close"
            aria-label="Close"
            data-bs-dismiss="modal"
            :disabled="saving || confirming"
          ></button>
        </div>
        <div class="modal-body">
          <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
          <slot />
        </div>
        <div v-if="confirming" class="modal-footer">
          <span class="me-auto fw-semibold" role="alert">Discard your changes?</span>
          <button ref="keepEditingButton" type="button" class="btn btn-primary" @click="keepEditing">Keep editing</button>
          <button type="button" class="btn btn-outline-danger" @click="hideNow">Discard</button>
        </div>
        <div v-else-if="closeOnly" class="modal-footer">
          <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Close</button>
        </div>
        <div v-else class="modal-footer">
          <div class="me-auto"><slot name="footer-left" /></div>
          <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal" :disabled="saving">Cancel</button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="saving || Boolean(saveDisabledReason)"
            :title="saveDisabledReason || null"
          >
            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>{{ saveLabel }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
