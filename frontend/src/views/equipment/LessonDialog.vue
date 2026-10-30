<script setup>
/**
 * Add lesson / Change lesson (docs/steps/S077-one-point-lesson-screens/1-brief.md § 5.3): title, the
 * lesson text, the class tick and, when adding, the photos.
 *
 * Callers: `openCreate({ machine, body, action_id })` — `machine` is `{id, code, name, class?}`, from the
 * equipment page (with its class) or from a countermeasure (the improvement's machine, no class), and
 * `body` / `action_id` come from the countermeasure — and `openChange(lesson)`, the lesson's detail.
 *
 * `equipment_id` and `action_id` are not form fields: they sit in `seed`, and toBody() adds them only
 * on a create (a change never sends `action_id`, which S075 refuses to clear). A refusal on either is no
 * form key, so useFormModal's modalError shows it at the top.
 *
 * Like MarkDoneDialog, it does not use useFormModal's send(), which closes the modal before afterSave:
 * save() posts the lesson first, so the record never waits for a slow upload, then uploads the photos
 * with the dialog still blocked (`saving`), then closes. A photo that fails leaves the dialog in its
 * close-only phase, with the reasons and "Add photos" again.
 *
 * It navigates nowhere. `saved(lesson)` comes from FormModal's `closed`, once, after the fade — by the
 * close after the photos or by the close-only Close — and the caller decides what to show.
 */
import { computed, ref } from "vue";
import { apiGet, apiPost, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { usePhotoUploads } from "../../composables/usePhotoUploads";
import { ensureEquipmentClasses, equipmentClasses } from "../../stores/masters";
import { ACCEPT, IPHONE_PHOTO_HINT, isHeicFile } from "../../utils/documentTypes";
import { classTickLabel, LESSON_BODY_MAX, LESSON_TITLE_MAX } from "../../utils/lessonLabels";

const emit = defineEmits(["saved"]);

const PATH = "/api/procedures";

// What a create adds to the body, and what the tick's label needs; set by openCreate / openChange
const seed = ref({ machine: null, action_id: null });
const className = ref("");
const showTick = ref(true);
const uploadLimitMb = ref(null);
const savedLesson = ref(null); // the answer of the save, handed on when the dialog has closed
const closePhase = ref(false); // saved, a photo failed: close-only

// A change sends no `action_id`: a lesson written from a countermeasure keeps its link (S075 § 5.3).
// Without the tick (an engineer of another site) it sends no `for_class` either.
function toBody(f) {
  if (editingId.value === null) return { ...f, equipment_id: seed.value.machine.id, action_id: seed.value.action_id };
  return showTick.value ? { ...f } : { title: f.title, body: f.body };
}

const { modal, form, editingId, saving, dirty, error, fieldError, modalError, markClean, openCreate: openForm, openEdit } = useFormModal({
  path: PATH,
  blank: (given = {}) => ({ title: given.title ?? "", body: given.body ?? "", for_class: false }),
  fromRecord: (lesson) => ({ title: lesson.title, body: lesson.body, for_class: lesson.for_class }),
  toBody,
  label: (lesson) => lesson.serial,
  afterSave: () => {},
});
const { files, add, remove, uploadAll, revokeAll } = usePhotoUploads({
  path: () => `${PATH}/${savedLesson.value?.id}/documents`,
  maxMb: uploadLimitMb,
  previews: true,
});

const failed = computed(() => files.value.filter((f) => f.state === "failed"));
const showHeicHint = computed(() => failed.value.some((f) => isHeicFile(f.file)));
const creating = computed(() => editingId.value === null);

// The class name for the tick: given by the caller, else read from the machine (a machine lesson's
// detail has no class, nor has the improvement's machine; BR2-02). A failed read keeps the plain label.
async function readClassName(machineId) {
  try {
    const [machine] = await Promise.all([apiGet(`/api/equipment/${machineId}`), ensureEquipmentClasses()]);
    const cls = (equipmentClasses.value ?? []).find((c) => c.id === machine.class_id);
    className.value = cls ? cls.name : "";
  } catch {
    className.value = "";
  }
}

async function readUploadLimit(machineId) {
  try {
    uploadLimitMb.value = (await apiGet(`/api/equipment/${machineId}/documents`)).upload_max_mb;
  } catch {
    uploadLimitMb.value = null; // the server still checks each upload
  }
}

function reset() {
  revokeAll();
  files.value = [];
  savedLesson.value = null;
  closePhase.value = false;
}

function openCreate({ machine, body = "", action_id: actionId = null }) {
  reset();
  seed.value = { machine, action_id: actionId };
  showTick.value = true;
  className.value = machine.class?.name ?? "";
  openForm({ body: body.slice(0, LESSON_BODY_MAX) });
  if (!className.value) readClassName(machine.id);
  readUploadLimit(machine.id);
}

function openChange(lesson) {
  reset();
  seed.value = { machine: lesson.machine, action_id: null };
  showTick.value = lesson.can_change_class;
  className.value = lesson.class?.name ?? "";
  openEdit(lesson);
  if (showTick.value && !className.value && lesson.machine) readClassName(lesson.machine.id);
}

async function save() {
  error.value = null;
  saving.value = true;
  let lesson;
  try {
    const body = toBody(form.value);
    lesson = await (editingId.value === null ? apiPost(PATH, body) : apiPut(`${PATH}/${editingId.value}`, body));
  } catch (err) {
    error.value = { field: err.field, message: err.message, status: err.status };
    saving.value = false;
    return;
  }
  savedLesson.value = lesson;
  markClean(); // a close now asks no "Discard your changes?"
  // saving stays true while the photos go: the close buttons stay blocked
  if (creating.value) await uploadAll();
  if (failed.value.length) {
    closePhase.value = true;
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
  // After the save a photo goes up at once; before it, it waits for "Save lesson"
  if (closePhase.value) {
    saving.value = true;
    try {
      await uploadAll();
    } finally {
      saving.value = false;
    }
  }
}

function onClosed() {
  if (!savedLesson.value) return;
  const lesson = savedLesson.value;
  savedLesson.value = null;
  emit("saved", lesson);
}

defineExpose({ openCreate, openChange });
</script>

<template>
  <FormModal
    ref="modal"
    :title="creating ? 'Add lesson' : 'Change lesson'"
    save-label="Save lesson"
    :saving="saving"
    :dirty="!closePhase && (dirty || files.length > 0)"
    :error="modalError"
    :close-only="closePhase"
    @save="save"
    @closed="onClosed"
  >
    <div v-if="closePhase" class="alert alert-warning py-2">Lesson saved. A photo was not saved. Add it again, or close.</div>
    <template v-else>
      <div class="mb-3">
        <label class="form-label" for="lesson-title">Title</label>
        <input
          id="lesson-title"
          v-model="form.title"
          class="form-control"
          :class="{ 'is-invalid': fieldError('title') }"
          type="text"
          :maxlength="LESSON_TITLE_MAX"
          autofocus
        />
        <div class="form-text text-end">{{ form.title.length }} / {{ LESSON_TITLE_MAX }}</div>
        <div v-if="fieldError('title')" class="invalid-feedback d-block">{{ fieldError("title") }}</div>
      </div>

      <div class="mb-3">
        <label class="form-label" for="lesson-body">Lesson text</label>
        <textarea
          id="lesson-body"
          v-model="form.body"
          class="form-control"
          :class="{ 'is-invalid': fieldError('body') }"
          rows="5"
          :maxlength="LESSON_BODY_MAX"
        ></textarea>
        <div class="form-text d-flex justify-content-between gap-2">
          <span>One point: what to do and why. Write in Tamil, English or both.</span>
          <span class="text-nowrap">{{ form.body.length }} / {{ LESSON_BODY_MAX }}</span>
        </div>
        <div v-if="fieldError('body')" class="invalid-feedback d-block">{{ fieldError("body") }}</div>
      </div>

      <div v-if="showTick" class="form-check mb-3">
        <input id="lesson-for-class" v-model="form.for_class" class="form-check-input" type="checkbox" />
        <label class="form-check-label" for="lesson-for-class">{{ classTickLabel(className) }}</label>
        <div class="form-text">The lesson then shows on every machine of this class, at every site.</div>
        <div v-if="fieldError('for_class')" class="invalid-feedback d-block">{{ fieldError("for_class") }}</div>
      </div>
    </template>

    <template v-if="creating || closePhase">
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
    </template>
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
