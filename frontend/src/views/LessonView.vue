<script setup>
/**
 * One-point lesson page (docs/steps/S077-one-point-lesson-screens/1-brief.md § 5.2; mock-up
 * docs/roadmap/R05-mockups/06-lesson.html): the machine and class it is for, the title, the photos
 * with their captions and the text in large type, one column. TPM practice: the lesson is read at the
 * machine and printed to post there ("Print lesson", the browser's print with main.css's rules).
 *
 * Photos are the full files (the 400 px thumbnail is too small to read a dusty contactor from),
 * fetched as blobs with the token and shown through object URLs, kept by document id across a reload
 * and revoked on unmount. Every button follows the detail's `can_edit`, so none ends in a refusal.
 * Each write answers with the whole detail, which replaces the page's copy.
 *
 * Retire asks first, in place of the button row (as the Meters card); bringing back asks nothing.
 */
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiGet, apiGetBlob, apiPut } from "../api";
import DocumentsCards from "../components/documents/DocumentsCards.vue";
import { formatDateTime } from "../utils/datetime";
import { downloadBlobUrl } from "../utils/download";
import { lessonDate, lessonTargetText } from "../utils/lessonLabels";
import LessonDialog from "./equipment/LessonDialog.vue";

const route = useRoute();

const lesson = ref(null);
const loading = ref(true);
const notFound = ref(false);
const loadError = ref("");
const actionError = ref("");
const busy = ref(false);
const confirmingRetire = ref(false);
const editingPhotos = ref(false);
const photoUrls = ref({}); // document id -> object URL
const photoFailed = ref({}); // document id -> true when its fetch failed
const dialog = ref(null);
let loadSeq = 0;

const photos = computed(() => (lesson.value?.documents ?? []).filter((d) => d.kind === "photo"));
const files = computed(() => (lesson.value?.documents ?? []).filter((d) => d.kind === "document"));
const documentsPath = computed(() => `/api/procedures/${lesson.value.id}/documents`);

function revokePhotos() {
  Object.values(photoUrls.value).forEach((url) => URL.revokeObjectURL(url));
  photoUrls.value = {};
  photoFailed.value = {};
}

// A reload (a photo added or removed under "Edit photos") keeps the photos it has and fetches only
// the new ones, so the page does not flash
function syncPhotos(seq) {
  const wanted = new Set(photos.value.map((d) => d.id));
  for (const [id, url] of Object.entries(photoUrls.value)) {
    if (!wanted.has(Number(id))) {
      URL.revokeObjectURL(url);
      delete photoUrls.value[id];
    }
  }
  for (const doc of photos.value) {
    if (photoUrls.value[doc.id]) continue;
    delete photoFailed.value[doc.id]; // a reload tries again
    apiGetBlob(`${documentsPath.value}/${doc.id}/file`).then(
      (blob) => {
        const url = URL.createObjectURL(blob);
        // A reload or another lesson since: this URL belongs to nobody (or to the copy already there)
        if (seq === loadSeq && !photoUrls.value[doc.id]) photoUrls.value[doc.id] = url;
        else URL.revokeObjectURL(url);
      },
      () => {
        // The caption stays; a line says the picture is missing
        if (seq === loadSeq) photoFailed.value[doc.id] = true;
      },
    );
  }
}

async function load() {
  const id = route.params.id;
  if (id === undefined) return; // the route is changing to another page
  const seq = ++loadSeq;
  if (lesson.value && String(lesson.value.id) !== String(id)) {
    lesson.value = null;
    revokePhotos();
    editingPhotos.value = false;
    confirmingRetire.value = false;
  }
  loading.value = true;
  notFound.value = false;
  loadError.value = "";
  try {
    const loaded = await apiGet(`/api/procedures/${id}`);
    if (seq !== loadSeq) return;
    lesson.value = loaded;
    syncPhotos(seq);
  } catch (err) {
    if (seq !== loadSeq) return;
    if (err.status === 404) {
      lesson.value = null;
      notFound.value = true;
    } else {
      loadError.value = err.message;
    }
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

watch(() => route.params.id, load, { immediate: true });

onBeforeUnmount(() => {
  loadSeq += 1;
  revokePhotos();
});

async function setActive(active) {
  busy.value = true;
  actionError.value = "";
  try {
    lesson.value = await apiPut(`/api/procedures/${lesson.value.id}`, { active });
    confirmingRetire.value = false;
  } catch (err) {
    actionError.value = err.message;
  } finally {
    busy.value = false;
  }
}

const printLesson = () => window.print();

// The dialog answered with the whole detail
function onSaved(saved) {
  lesson.value = saved;
}

async function downloadDocument(doc) {
  actionError.value = "";
  try {
    const url = URL.createObjectURL(await apiGetBlob(`${documentsPath.value}/${doc.id}/file`));
    downloadBlobUrl(url, `${doc.title}.pdf`);
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (err) {
    actionError.value = err.message;
  }
}
</script>

<template>
  <div class="py-3 lesson-page">
    <div v-if="loading && !lesson" class="text-secondary">Loading…</div>
    <div v-else-if="notFound" class="alert alert-warning">
      Lesson not found, or not at your units.
      <router-link to="/equipment" class="alert-link ms-1">Back to the list</router-link>
    </div>
    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger tap-target" @click="load">Retry</button>
    </div>

    <template v-if="lesson && !notFound">
      <div class="small mb-2" data-testid="lesson-target">
        <router-link v-if="lesson.machine" :to="`/equipment/${lesson.machine.id}`">
          <i class="fa-solid fa-gears me-1"></i>{{ lessonTargetText(lesson) }}
        </router-link>
        <span v-else class="text-secondary"><i class="fa-solid fa-gears me-1"></i>{{ lessonTargetText(lesson) }}</span>
      </div>

      <div v-if="!lesson.active" class="alert alert-secondary" data-testid="retired-banner">
        Retired — this lesson is no longer shown on the machine's page.
      </div>

      <div class="card mb-3">
        <div class="card-body">
          <div class="small text-uppercase text-secondary">One-point lesson</div>
          <div class="small text-secondary mb-2">
            {{ lesson.serial }} · {{ lessonDate(lesson.created_at) }} · {{ lesson.created_by_name }}
          </div>
          <h2 class="fs-3 lesson-title">{{ lesson.title }}</h2>

          <figure v-for="p in photos" :key="p.id" class="mb-3" :data-photo="p.title">
            <img v-if="photoUrls[p.id]" :src="photoUrls[p.id]" :alt="p.title" class="lesson-photo" />
            <div v-else-if="photoFailed[p.id]" class="lesson-photo-wait text-secondary small text-center" data-testid="photo-failed">
              The photo could not be loaded. Reload the page.
            </div>
            <div v-else class="lesson-photo-wait text-secondary"><i class="fa-solid fa-spinner fa-spin"></i></div>
            <figcaption class="small lesson-title">{{ p.title }}</figcaption>
          </figure>

          <div class="fs-5 lesson-body" data-testid="lesson-body">{{ lesson.body }}</div>

          <ul v-if="files.length" class="list-unstyled mt-3 mb-0 no-print">
            <li v-for="f in files" :key="f.id">
              <button type="button" class="btn btn-link p-0 text-start" @click="downloadDocument(f)">
                <i class="fa-regular fa-file-pdf text-danger me-1"></i>{{ f.title }}
              </button>
            </li>
          </ul>
        </div>
      </div>

      <p v-if="lesson.source" class="small mb-2">
        From improvement
        <router-link :to="`/tickets/improvements/${lesson.source.improvement.id}`">
          {{ lesson.source.improvement.serial }} · {{ lesson.source.improvement.title }}
        </router-link>
      </p>
      <p v-if="lesson.updated_at" class="small text-secondary mb-3">
        Last changed {{ formatDateTime(lesson.updated_at) }} by {{ lesson.updated_by_name }}
      </p>

      <div v-if="actionError" class="alert alert-danger py-2 no-print">{{ actionError }}</div>

      <div v-if="confirmingRetire" class="no-print">
        <p class="mb-2">Retire {{ lesson.serial }}? It leaves the machine's page. You can bring it back.</p>
        <div class="d-flex flex-wrap gap-2">
          <button type="button" class="btn btn-danger tap-target" :disabled="busy" @click="setActive(false)">Retire lesson</button>
          <button type="button" class="btn btn-outline-secondary tap-target" :disabled="busy" @click="confirmingRetire = false">Keep it</button>
        </div>
      </div>
      <div v-else class="d-flex flex-column flex-sm-row flex-wrap gap-2 no-print">
        <button type="button" class="btn btn-outline-secondary tap-target" @click="printLesson">
          <i class="fa-solid fa-print me-1"></i>Print lesson
        </button>
        <template v-if="lesson.can_edit">
          <button type="button" class="btn btn-primary tap-target" @click="dialog.openChange(lesson)">
            <i class="fa-solid fa-pen me-1"></i>Change lesson
          </button>
          <button type="button" class="btn btn-outline-primary tap-target" :aria-expanded="editingPhotos" @click="editingPhotos = !editingPhotos">
            <i class="fa-solid fa-camera me-1"></i>Edit photos
          </button>
          <button v-if="lesson.active" type="button" class="btn btn-outline-danger tap-target" @click="confirmingRetire = true">
            Retire lesson
          </button>
          <button v-else type="button" class="btn btn-outline-success tap-target" :disabled="busy" @click="setActive(true)">
            Bring back lesson
          </button>
        </template>
      </div>

      <div v-if="lesson.can_edit && editingPhotos" class="mt-3 no-print">
        <DocumentsCards :base-path="documentsPath" can-edit large-add @changed="load" />
      </div>

      <LessonDialog ref="dialog" @saved="onSaved" />
    </template>
  </div>
</template>

<style scoped>
.lesson-page {
  max-width: 720px;
  margin-inline: auto;
}
.lesson-title,
.lesson-body {
  overflow-wrap: anywhere;
}
.lesson-body {
  white-space: pre-line;
}
.lesson-photo {
  display: block;
  width: 100%;
  max-height: 60vh;
  object-fit: contain;
}
.lesson-photo-wait {
  height: 8rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
/* The sheet posted at the machine: the card on one A4 page where it fits, plain links */
@media print {
  .lesson-photo {
    max-height: 40vh;
  }
  .lesson-page a {
    color: inherit;
    text-decoration: none;
  }
  .lesson-page {
    max-width: none;
  }
}
</style>
