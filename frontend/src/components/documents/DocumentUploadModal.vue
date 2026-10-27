<script setup>
/**
 * Upload dialog — file and title (docs/steps/S006-equipment-documents/1-brief.md § 1, § 5.2, § 6.3).
 *
 * The parent calls open(kind) through a template ref and handles @saved: Add document and Add
 * photo each pass their kind, and the dialog's title names it (S064 UX-11: no Kind choice). The
 * title is pre-filled from the file name without its extension, except a camera's own name
 * (IMG_…, PXL_…), which says nothing: the title then stays empty for the user to fill. A file
 * above the upload limit is refused here before sending, to save mobile data; the backend checks
 * again and decides the file type from its first bytes.
 *
 * The file input has no `capture` attribute, so a phone offers the camera and the gallery.
 *
 * The parent passes the owner's documents collection URL (a node or a model: S012; a
 * ticket: S017). Who may add which kind is the parent's: it shows only the buttons the user may
 * use (S018).
 *
 * The iPhone note (Most Compatible) shows only after the server refused a HEIC / HEIF file.
 */
import { computed, nextTick, ref } from "vue";
import { apiUpload } from "../../api";
import FormModal from "../FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ACCEPT, IPHONE_PHOTO_HINT, isCameraName, isHeicFile, withoutExtension } from "../../utils/documentTypes";

const props = defineProps({
  basePath: { type: String, required: true },
  // A model document: shown at every site (S012 § 2, ISO 27001 A.5.12)
  everySite: { type: Boolean, default: false },
  // From the list response; null until the list has loaded (the backend still checks)
  uploadMaxMb: { type: Number, default: null },
});
const emit = defineEmits(["saved"]);

const MB = 1024 * 1024;
// A ticket's files are seen by everyone who sees the ticket (S017 § 5.5); the owner is known by its URL
const ticketOwner = computed(() => props.basePath.startsWith("/api/tickets/"));
const TITLE_MAX = 200;

// Uploads are multipart, so they go through send() rather than useFormModal's JSON save()
const { modal, form, saving, dirty, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: (kind = "document") => ({ kind, title: "", file: null }),
  afterSave: (result) => emit("saved", result),
});

// Bumped to give the file input a fresh element: an <input type="file"> cannot be cleared from code
const fileInputKey = ref(0);
const titleInput = ref(null);
let prefilledTitle = "";
// The chosen file has a camera's name: the title field asks what the photo shows
const cameraNamed = ref(false);

const tooLarge = computed(() =>
  Boolean(form.value.file && props.uploadMaxMb && form.value.file.size > props.uploadMaxMb * MB),
);
const fileError = computed(() => (tooLarge.value ? `Larger than ${props.uploadMaxMb} MB` : fieldError("file")));
const saveDisabledReason = computed(() => {
  if (!form.value.file) return "Choose a file";
  if (tooLarge.value) return fileError.value;
  return form.value.title.trim() === "" ? "Enter a title" : "";
});
// After the server refused the chosen HEIC file (the error is on the file field or the dialog)
const showIphoneHint = computed(() => isHeicFile(form.value.file) && Boolean(fieldError("file") || modalError.value));

function onFileChosen(event) {
  const file = event.target.files[0] ?? null;
  form.value.file = file;
  cameraNamed.value = Boolean(file) && isCameraName(file.name);
  // Pre-fill the title, unless the user has typed one of their own
  if (file && (form.value.title === "" || form.value.title === prefilledTitle)) {
    prefilledTitle = cameraNamed.value ? "" : withoutExtension(file.name).slice(0, TITLE_MAX);
    form.value.title = prefilledTitle;
    if (cameraNamed.value) nextTick(() => titleInput.value?.focus());
  }
}

function open(kind) {
  prefilledTitle = "";
  cameraNamed.value = false;
  openCreate(kind);
  fileInputKey.value += 1;
}

function save() {
  if (saveDisabledReason.value) return;
  const body = new FormData();
  body.append("kind", form.value.kind);
  body.append("title", form.value.title);
  body.append("file", form.value.file);
  return send(() => apiUpload(props.basePath, body));
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    :title="form.kind === 'photo' ? 'Add photo' : 'Add document'"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :save-disabled-reason="saveDisabledReason"
    save-label="Upload"
    @save="save"
  >
    <div class="mb-3">
      <label class="form-label" for="doc-file">File</label>
      <input
        id="doc-file"
        :key="fileInputKey"
        class="form-control"
        :class="{ 'is-invalid': fileError }"
        type="file"
        :accept="ACCEPT[form.kind]"
        @change="onFileChosen"
      />
      <div v-if="fileError" class="invalid-feedback d-block">{{ fileError }}</div>
      <div class="form-text">
        <template v-if="uploadMaxMb">At most {{ uploadMaxMb }} MB.</template>
        <template v-if="showIphoneHint"> {{ IPHONE_PHOTO_HINT }}</template>
      </div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="doc-title">Title</label>
      <input
        id="doc-title"
        ref="titleInput"
        v-model="form.title"
        :placeholder="cameraNamed ? 'What does the photo show?' : null"
        class="form-control"
        :class="{ 'is-invalid': fieldError('title') }"
        :maxlength="TITLE_MAX"
      />
      <div v-if="fieldError('title')" class="invalid-feedback d-block">{{ fieldError("title") }}</div>
      <div v-if="everySite" class="form-text">Visible at every site: no confidential documents (contracts, prices).</div>
      <div v-else-if="ticketOwner" class="form-text">Everyone who can see this ticket can see it.</div>
      <div v-else class="form-text">Everyone who can see this equipment can see it: no confidential documents (contracts, prices).</div>
    </div>
  </FormModal>
</template>
