<script setup>
/**
 * Documents and Photos cards on the equipment page (docs/steps/S006-equipment-documents/1-brief.md).
 *
 * Files are fetched as blobs with the token and shown through object URLs (§ 6.3):
 * - thumbnails and large photos: revoked when the list reloads, when the page follows a
 *   new node and on unmount, so a long session does not keep every image in memory;
 * - PDFs: revoked only on unmount, because a tab opened from one may still be loading it.
 * Open a PDF opens the tab synchronously, before the fetch, so it is not blocked as a pop-up.
 */
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { apiDelete, apiGet, apiGetBlob } from "../../api";
import { formatDateTime } from "../../utils/datetime";
import { formatBytes } from "../../utils/format";
import DocumentTitleModal from "./DocumentTitleModal.vue";
import DocumentUploadModal from "./DocumentUploadModal.vue";
import PhotoViewer from "./PhotoViewer.vue";

const props = defineProps({
  nodeId: { type: Number, required: true },
  // Upload, edit title and remove (equipment:edit, not scrapped); the parent decides
  canEdit: { type: Boolean, default: false },
});

const items = ref([]);
const uploadMaxMb = ref(null);
const loading = ref(false);
const loadError = ref("");
const actionError = ref("");
const confirmingRemoveId = ref(null);
const removing = ref(false);
let loadSeq = 0;

const uploadModal = ref(null);
const titleModal = ref(null);
const viewer = ref(null);

const documents = computed(() => items.value.filter((d) => d.kind === "document"));
const photos = computed(() => items.value.filter((d) => d.kind === "photo"));

// Object URLs, by document id.  Image URLs are cached as promises, so two requests for
// the same image share one fetch.
const thumbUrls = ref({});      // id -> URL, for the grid
const thumbFailed = ref({});    // id -> true when the thumbnail could not be fetched
let fullImages = new Map();     // id -> Promise<URL>, for the viewer
const pdfUrls = new Map();      // id -> URL; kept until unmount

const docsPath = (nodeId) => `/api/equipment/${nodeId}/documents`;
const fileUrl = (doc) => `${docsPath(props.nodeId)}/${doc.id}/file`;

async function objectUrl(url) {
  return URL.createObjectURL(await apiGetBlob(url));
}

function revokeImages() {
  Object.values(thumbUrls.value).forEach((url) => URL.revokeObjectURL(url));
  thumbUrls.value = {};
  thumbFailed.value = {};
  const pending = fullImages;
  fullImages = new Map();
  pending.forEach((promise) => promise.then((url) => URL.revokeObjectURL(url), () => {}));
}

function loadThumbs(nodeId, seq) {
  for (const photo of photos.value) {
    const url = `${docsPath(nodeId)}/${photo.id}/${photo.has_thumb ? "thumb" : "file"}`;
    objectUrl(url).then(
      (loaded) => {
        // A reload or a new node since: this URL belongs to nobody
        if (seq === loadSeq) thumbUrls.value[photo.id] = loaded;
        else URL.revokeObjectURL(loaded);
      },
      () => {
        if (seq === loadSeq) thumbFailed.value[photo.id] = true;
      },
    );
  }
}

async function load() {
  const nodeId = props.nodeId;
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const result = await apiGet(docsPath(nodeId));
    if (seq !== loadSeq) return;
    revokeImages();
    items.value = result.items;
    uploadMaxMb.value = result.upload_max_mb;
    loadThumbs(nodeId, seq);
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

// Vue Router reuses the equipment page when only :id changes, so follow the node
watch(() => props.nodeId, () => {
  revokeImages();
  items.value = [];
  confirmingRemoveId.value = null;
  actionError.value = "";
  load();
}, { immediate: true });

onBeforeUnmount(() => {
  loadSeq += 1;
  revokeImages();
  pdfUrls.forEach((url) => URL.revokeObjectURL(url));
  pdfUrls.clear();
});

// ---------------------------------------------------------------------------
// PDFs and photos
// ---------------------------------------------------------------------------

async function pdfUrl(doc) {
  if (!pdfUrls.has(doc.id)) pdfUrls.set(doc.id, await objectUrl(fileUrl(doc)));
  return pdfUrls.get(doc.id);
}

async function downloadPdf(doc) {
  actionError.value = "";
  try {
    const link = document.createElement("a");
    link.href = await pdfUrl(doc);
    // A blob URL has no name of its own; without this Android saves a nameless file
    link.download = `${doc.title}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } catch (err) {
    actionError.value = err.message;
  }
}

async function openPdf(doc) {
  actionError.value = "";
  // Before any await: a tab opened after one is blocked as a pop-up (Safari; Chrome on slow loads)
  const tab = window.open("", "_blank");
  if (!tab) {
    // Some in-app browsers (e.g. inside WhatsApp) open no tab at all
    await downloadPdf(doc);
    return;
  }
  try {
    tab.location = await pdfUrl(doc);
  } catch (err) {
    tab.close();
    actionError.value = err.message;
  }
}

function loadFullImage(photo) {
  if (!fullImages.has(photo.id)) fullImages.set(photo.id, objectUrl(fileUrl(photo)));
  return fullImages.get(photo.id);
}

// ---------------------------------------------------------------------------
// Edit title, remove
// ---------------------------------------------------------------------------

async function editFromViewer(photo) {
  await viewer.value.close();
  titleModal.value.open(photo);
}

async function remove(doc) {
  removing.value = true;
  actionError.value = "";
  try {
    await apiDelete(`${docsPath(props.nodeId)}/${doc.id}`);
    confirmingRemoveId.value = null;
    await load();
  } catch (err) {
    actionError.value = err.message;
  } finally {
    // From the viewer: close it either way, so the photo is gone or the error is visible
    if (doc.kind === "photo") await viewer.value.close();
    removing.value = false;
  }
}
</script>

<template>
  <div class="row g-3 mt-0">
    <div v-if="loadError" class="col-12">
      <div class="alert alert-danger d-flex justify-content-between align-items-center mb-0">
        <span>Documents could not be loaded: {{ loadError }}</span>
        <button class="btn btn-sm btn-outline-danger" @click="load">Retry</button>
      </div>
    </div>
    <div v-if="actionError" class="col-12">
      <div class="alert alert-danger py-2 mb-0">{{ actionError }}</div>
    </div>

    <div class="col-lg-6">
      <div class="card h-100">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>Documents</span>
          <button v-if="canEdit" class="btn btn-sm btn-outline-primary" @click="uploadModal.open('document')">
            <i class="fa-solid fa-plus me-1"></i>Add document
          </button>
        </div>
        <div v-if="!documents.length" class="card-body text-secondary">
          {{ loading ? "Loading…" : "No documents yet." }}
        </div>
        <ul v-else class="list-group list-group-flush">
          <li v-for="doc in documents" :key="doc.id" class="list-group-item">
            <div class="d-flex flex-wrap align-items-start gap-2">
              <i class="fa-regular fa-file-pdf text-danger mt-1"></i>
              <div class="flex-grow-1 doc-text">
                <div class="fw-semibold">{{ doc.title }}</div>
                <div class="small text-secondary">
                  {{ doc.original_name }} · {{ formatBytes(doc.size_bytes) }} ·
                  {{ doc.created_by }}, {{ formatDateTime(doc.created_at) }}
                </div>
              </div>
              <div class="d-flex flex-wrap gap-1">
                <button class="btn btn-sm btn-outline-secondary" title="Open in a new tab" @click="openPdf(doc)">
                  <i class="fa-solid fa-up-right-from-square"></i><span class="ms-1 d-none d-sm-inline">Open</span>
                </button>
                <button class="btn btn-sm btn-outline-secondary" title="Download" @click="downloadPdf(doc)">
                  <i class="fa-solid fa-download"></i><span class="ms-1 d-none d-sm-inline">Download</span>
                </button>
                <template v-if="canEdit">
                  <button class="btn btn-sm btn-outline-primary" title="Edit title" @click="titleModal.open(doc)">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                  <button
                    v-if="confirmingRemoveId !== doc.id"
                    class="btn btn-sm btn-outline-danger"
                    title="Remove"
                    @click="confirmingRemoveId = doc.id"
                  >
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </template>
              </div>
            </div>
            <div v-if="canEdit && confirmingRemoveId === doc.id" class="d-flex align-items-center justify-content-end gap-2 mt-2">
              <span>Remove this document?</span>
              <button class="btn btn-sm btn-danger" :disabled="removing" @click="remove(doc)">Yes</button>
              <button class="btn btn-sm btn-outline-secondary" @click="confirmingRemoveId = null">No</button>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <div class="col-lg-6">
      <div class="card h-100">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>Photos</span>
          <button v-if="canEdit" class="btn btn-sm btn-outline-primary" @click="uploadModal.open('photo')">
            <i class="fa-solid fa-camera me-1"></i>Add photo
          </button>
        </div>
        <div class="card-body">
          <div v-if="!photos.length" class="text-secondary">{{ loading ? "Loading…" : "No photos yet." }}</div>
          <div v-else class="d-flex flex-wrap gap-2">
            <button
              v-for="(photo, i) in photos"
              :key="photo.id"
              type="button"
              class="photo-tile btn p-0 border"
              :title="photo.title"
              @click="viewer.open(i)"
            >
              <img v-if="thumbUrls[photo.id]" :src="thumbUrls[photo.id]" :alt="photo.title" />
              <span v-else class="photo-placeholder text-secondary">
                <i class="fa-solid" :class="thumbFailed[photo.id] ? 'fa-image' : 'fa-spinner fa-spin'"></i>
              </span>
              <span class="photo-caption small text-truncate">{{ photo.title }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <DocumentUploadModal ref="uploadModal" :node-id="nodeId" :upload-max-mb="uploadMaxMb" @saved="load" />
    <DocumentTitleModal ref="titleModal" :node-id="nodeId" @saved="load" />
    <PhotoViewer
      ref="viewer"
      :photos="photos"
      :load-image="loadFullImage"
      :can-edit="canEdit"
      :removing="removing"
      @edit="editFromViewer"
      @remove="remove"
    />
  </div>
</template>

<style scoped>
.doc-text {
  min-width: 0;
  overflow-wrap: anywhere;
}
.photo-tile {
  width: 128px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.photo-tile img,
.photo-placeholder {
  width: 100%;
  height: 128px;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
}
.photo-caption {
  padding: 2px 4px;
  max-width: 100%;
}
</style>
