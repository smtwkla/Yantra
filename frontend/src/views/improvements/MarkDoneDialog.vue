<script setup>
/**
 * Mark countermeasure done (docs/steps/S071-countermeasure-screens/1-brief.md § 5.5): what was
 * done, when (the S051 time field with a Now tick) and photos of the work. One dialog for the
 * improvement page and for Me; the caller gives `open({ improvementId, action })`.
 *
 * It does not use useFormModal's send(), which closes the modal as soon as its request resolves.
 * save() posts the done first, so the record never waits for a slow upload, then uploads the
 * photos with the dialog still blocked (`saving`), then closes. A photo that fails leaves the
 * dialog open in its close-only phase, with the reason and "Add photos" again: the countermeasure
 * is done already, and S070 allows photos on a done one.
 *
 * Events: `saved(detail)` right after the done (the page replaces its copy, so the row reads
 * Done behind the dialog); `reload` when the page behind is stale (409) or a photo went up (the
 * page reloads its detail, so the row reads "Photos (n)").
 */
import { computed, ref } from "vue";
import { apiGet, apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { usePhotoUploads } from "../../composables/usePhotoUploads";
import { ACCEPT, IPHONE_PHOTO_HINT, isHeicFile } from "../../utils/documentTypes";
import { DONE_TEXT_MAX } from "../../utils/improvementLabels";
import EventFields from "../tickets/EventFields.vue";

const emit = defineEmits(["saved", "reload"]);

// The fields this dialog shows a refusal beside; any other goes to the top
const SHOWN_FIELDS = ["done_text", "done_at"];

// Copied at open(): the row may be gone from Me after the first reload (BR2-01)
const target = ref({ improvementId: null, id: null, text: "" });
const uploadLimitMb = ref(null);
const donePhase = ref(false); // marked done, a photo failed: close-only
const opens = ref(0); // EventFields is keyed on it: every opening starts at "Now"

const { modal, form, saving, dirty, error, fieldError, markClean, openCreate } = useFormModal({
  path: null,
  blank: (seed = {}) => ({ done_text: "", done_at: null, ...seed }),
  afterSave: () => {},
});
const { files, add, remove, uploadAll, revokeAll } = usePhotoUploads({
  path: () => `/api/improvements/actions/${target.value.id}/documents`,
  maxMb: uploadLimitMb,
  previews: true,
});

const topError = computed(() => (error.value && !SHOWN_FIELDS.includes(error.value.field) ? error.value.message : ""));
const failed = computed(() => files.value.filter((f) => f.state === "failed"));
const showHeicHint = computed(() => failed.value.some((f) => isHeicFile(f.file)));

async function loadLimit() {
  try {
    uploadLimitMb.value = (await apiGet(`/api/improvements/actions/${target.value.id}/documents`)).upload_max_mb;
  } catch {
    uploadLimitMb.value = null; // the server still checks each upload
  }
}

function open({ improvementId, action }) {
  target.value = { improvementId, id: action.id, text: action.text };
  revokeAll();
  files.value = [];
  donePhase.value = false;
  opens.value += 1;
  openCreate({ done_text: "", done_at: null });
  loadLimit();
}

async function uploadChosen() {
  saving.value = true;
  try {
    const uploaded = await uploadAll();
    if (uploaded > 0) emit("reload");
    return uploaded;
  } finally {
    saving.value = false;
  }
}

async function save() {
  error.value = null;
  saving.value = true;
  let detail;
  try {
    detail = await apiPost(`/api/improvements/${target.value.improvementId}/actions/${target.value.id}/done`, {
      done_text: form.value.done_text,
      done_at: form.value.done_at,
    });
  } catch (err) {
    error.value = { field: err.field, message: err.message, status: err.status };
    // A stale page (409, no field): ask the caller to reload what is behind the dialog
    if (!err.field && err.status === 409) emit("reload");
    saving.value = false;
    return;
  }
  emit("saved", detail);
  markClean(); // a close now asks no "Discard your changes?"
  // saving stays true while the photos go: the close buttons stay blocked
  const uploaded = await uploadAll();
  if (uploaded > 0) emit("reload");
  if (failed.value.length) {
    donePhase.value = true;
    saving.value = false;
    return;
  }
  modal.value.close();
  saving.value = false;
}

async function onPhotosChosen(event) {
  const chosen = [...event.target.files];
  event.target.value = ""; // the same photo can be picked again after a failure
  add(chosen);
  // After the done, a photo goes up at once; before it, it waits for "Mark done"
  if (donePhase.value) await uploadChosen();
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    title="Mark countermeasure done"
    save-label="Mark done"
    :saving="saving"
    :dirty="!donePhase && (dirty || files.length > 0)"
    :error="topError"
    :close-only="donePhase"
    @save="save"
  >
    <p class="text-secondary text-break mb-3" data-testid="done-target">{{ target.text }}</p>

    <div v-if="donePhase" class="alert alert-warning py-2">Marked done. A photo was not saved. Add it again, or close.</div>
    <template v-else>
      <div class="mb-3">
        <label class="form-label" for="done-text">What did you do?</label>
        <textarea
          id="done-text"
          v-model="form.done_text"
          class="form-control"
          :class="{ 'is-invalid': fieldError('done_text') }"
          rows="3"
          :maxlength="DONE_TEXT_MAX"
          placeholder="New gasket fitted."
          autofocus
        ></textarea>
        <div v-if="fieldError('done_text')" class="invalid-feedback d-block">{{ fieldError("done_text") }}</div>
      </div>
      <EventFields
        :key="opens"
        v-model:time="form.done_at"
        :with-remark="false"
        time-label="Done on"
        id-prefix="done"
        :time-error="fieldError('done_at')"
      />
    </template>

    <label class="btn btn-outline-primary btn-lg w-100 mb-2" :class="{ disabled: saving }">
      <i class="fa-solid fa-camera me-2"></i>Add photos
      <input class="visually-hidden" type="file" multiple :accept="ACCEPT.photo" :disabled="saving" @change="onPhotosChosen" />
    </label>
    <div class="form-text mb-3">
      <template v-if="uploadLimitMb">At most {{ uploadLimitMb }} MB each. </template><template v-if="showHeicHint">{{ IPHONE_PHOTO_HINT }}</template>
    </div>
    <ul v-if="files.length" class="list-group">
      <li v-for="f in files" :key="f.key" class="list-group-item d-flex align-items-center gap-2" :data-photo="f.name">
        <img v-if="f.previewUrl" :src="f.previewUrl" alt="" class="thumb" />
        <div class="flex-grow-1 text-break">
          <div>{{ f.name }}</div>
          <div v-if="f.message" class="small text-danger">{{ f.message }}</div>
        </div>
        <i
          class="fa-solid"
          :class="{
            'fa-spinner fa-spin text-secondary': f.state === 'uploading',
            'fa-check text-success': f.state === 'done',
            'fa-xmark text-danger': f.state === 'failed',
          }"
        ></i>
        <button
          v-if="f.state === 'pending' || f.state === 'failed'"
          type="button"
          class="btn btn-outline-secondary"
          :aria-label="`Remove ${f.name}`"
          :disabled="saving"
          @click="remove(f.key)"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </li>
    </ul>
  </FormModal>
</template>

<style scoped>
.thumb {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 0.25rem;
  flex: none;
}
</style>
