<script setup>
/**
 * Upload dialog — kind, title, file (docs/steps/S006-equipment-documents/1-brief.md § 1, § 5.2, § 6.3).
 *
 * The parent calls open(kind) through a template ref and handles @saved. The title is
 * pre-filled from the file name without its extension. A file above the upload limit is
 * refused here before sending, to save mobile data; the backend checks again and decides
 * the file type from its first bytes.
 *
 * The file input has no `capture` attribute, so a phone offers the camera and the gallery.
 *
 * The parent passes the owner's documents collection URL (a node or a model: S012; a
 * ticket: S017). With `photosOnly` (a ticket, which takes photos only) the Kind choice is
 * hidden and the kind is photo, so a PDF is never picked only to be refused by the server.
 */
import { computed, ref, watch } from "vue";
import { apiUpload } from "../../api";
import FormModal from "../FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ACCEPT, IPHONE_PHOTO_HINT, withoutExtension } from "../../utils/documentTypes";

const props = defineProps({
  basePath: { type: String, required: true },
  // A model document: shown at every site (S012 § 2, ISO 27001 A.5.12)
  everySite: { type: Boolean, default: false },
  // From the list response; null until the list has loaded (the backend still checks)
  uploadMaxMb: { type: Number, default: null },
  // A ticket's photos (S017): no Kind choice
  photosOnly: { type: Boolean, default: false },
});
const emit = defineEmits(["saved"]);

const MB = 1024 * 1024;
const TITLE_MAX = 200;
const KIND_LABELS = {
  document: "Document (PDF)",
  photo: "Photo (JPEG, PNG or WebP)",
};

// Uploads are multipart, so they go through send() rather than useFormModal's JSON save()
const { modal, form, saving, dirty, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: (kind = "document") => ({ kind, title: "", file: null }),
  afterSave: (result) => emit("saved", result),
});

// Bumped to give the file input a fresh element: an <input type="file"> cannot be cleared from code
const fileInputKey = ref(0);
let prefilledTitle = "";

const tooLarge = computed(() =>
  Boolean(form.value.file && props.uploadMaxMb && form.value.file.size > props.uploadMaxMb * MB),
);
const fileError = computed(() => (tooLarge.value ? `Larger than ${props.uploadMaxMb} MB` : fieldError("file")));
const saveDisabledReason = computed(() => {
  if (!form.value.file) return "Choose a file";
  return tooLarge.value ? fileError.value : "";
});

function clearFile() {
  form.value.file = null;
  fileInputKey.value += 1;
}

// A file chosen for one kind may not suit the other
watch(() => form.value.kind, clearFile);

function onFileChosen(event) {
  const file = event.target.files[0] ?? null;
  form.value.file = file;
  // Pre-fill the title, unless the user has typed one of their own
  if (file && (form.value.title === "" || form.value.title === prefilledTitle)) {
    prefilledTitle = withoutExtension(file.name).slice(0, TITLE_MAX);
    form.value.title = prefilledTitle;
  }
}

function open(kind) {
  prefilledTitle = "";
  openCreate(props.photosOnly ? "photo" : kind);
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
    <div v-if="!photosOnly" class="mb-3">
      <label class="form-label d-block">Kind</label>
      <div v-for="(label, kind) in KIND_LABELS" :key="kind" class="form-check form-check-inline">
        <input :id="`doc-kind-${kind}`" v-model="form.kind" class="form-check-input" type="radio" :value="kind" />
        <label class="form-check-label" :for="`doc-kind-${kind}`">{{ label }}</label>
      </div>
      <div v-if="fieldError('kind')" class="invalid-feedback d-block">{{ fieldError("kind") }}</div>
    </div>
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
      <div class="invalid-feedback">{{ fileError }}</div>
      <div class="form-text">
        <template v-if="uploadMaxMb">At most {{ uploadMaxMb }} MB.</template>
        <template v-if="form.kind === 'photo'">{{ IPHONE_PHOTO_HINT }}</template>
      </div>
    </div>
    <div class="mb-0">
      <label class="form-label" for="doc-title">Title</label>
      <input
        id="doc-title"
        v-model="form.title"
        class="form-control"
        :class="{ 'is-invalid': fieldError('title') }"
        :maxlength="TITLE_MAX"
      />
      <div class="invalid-feedback">{{ fieldError("title") }}</div>
      <div v-if="everySite" class="form-text">Visible at every site: no confidential documents (contracts, prices).</div>
      <div v-else-if="photosOnly" class="form-text">Everyone who can see this ticket can see it.</div>
      <div v-else class="form-text">Everyone who can see this equipment can see it: no confidential documents (contracts, prices).</div>
    </div>
  </FormModal>
</template>
