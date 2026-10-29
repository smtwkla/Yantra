<script setup>
/**
 * Documents and Photos cards of one owner — a node on the equipment page, an equipment
 * model in Masters (docs/steps/S006-equipment-documents/1-brief.md; owners: S012, the design
 * of the dropped S009), or a ticket (S017 photos; S018 documents too, added by ticket:work
 * holders only: `canEditDocuments`).
 *
 * `basePath` is the owner's documents collection URL. A node's list also has `inherited`
 * group (its model's documents), shown read-only under its heading;
 * each group brings its own `path`. Every item is tagged with the `path` it is served from
 * and whether it is the owner's `own`, so file URLs and the edit buttons follow the item.
 *
 * Files are fetched as blobs with the token and shown through object URLs (S006 § 6.3):
 * - thumbnails and large photos: revoked when the list reloads, when the cards follow a
 *   new owner and on unmount, so a long session does not keep every image in memory;
 * - PDFs: revoked only on unmount, because a tab opened from one may still be loading it.
 * Open a PDF opens the tab synchronously, before the fetch, so it is not blocked as a pop-up.
 * Document ids are unique across owners, so the caches are keyed by id alone.
 */
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { apiDelete, apiGet, apiGetBlob } from "../../api";
import { formatDateTime } from "../../utils/datetime";
import { formatBytes } from "../../utils/format";
import DocumentTitleModal from "./DocumentTitleModal.vue";
import DocumentUploadModal from "./DocumentUploadModal.vue";
import PhotoViewer from "./PhotoViewer.vue";

const props = defineProps({
  basePath: { type: String, required: true },
  // Upload, edit title and remove of the owner's own items; the parent decides
  canEdit: { type: Boolean, default: false },
  // The same for documents when it differs from photos (a ticket, S018 BS1-02); absent: canEdit.
  // `undefined` default: an absent Boolean prop would otherwise be cast to false
  canEditDocuments: { type: Boolean, default: undefined },
  // Show the "Managed in Masters" line on inherited groups: for users who may edit model
  // documents (equipment:edit held at any site), whatever the node's lifecycle; the parent decides
  showManagedIn: { type: Boolean, default: false },
  // "model" for a Masters owner, whose documents show at every site and on every
  // machine of it; "" for a node
  everySite: { type: String, default: "" },
  // A floor screen (the ticket page): "Add photo" is a large full-width button
  largeAdd: { type: Boolean, default: false },
});
// After a successful upload, title edit or remove (S071 BR1-07): a page that shows a count of the
// owner's items reloads it. Other callers ignore it.
const emit = defineEmits(["changed"]);

const MANAGED_IN = { model: "Models" };

const canEditDocs = computed(() => props.canEditDocuments ?? props.canEdit);

const items = ref([]);
const inherited = ref([]);
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

const ofKind = (list, kind) => list.filter((d) => d.kind === kind);
const documents = computed(() => ofKind(items.value, "document"));
const photos = computed(() => ofKind(items.value, "photo"));
// Inherited groups with at least one item of the kind, for each card
const inheritedOfKind = (kind) =>
  inherited.value.map((g) => ({ ...g, items: ofKind(g.items, kind) })).filter((g) => g.items.length);
const inheritedDocuments = computed(() => inheritedOfKind("document"));
const inheritedPhotos = computed(() => inheritedOfKind("photo"));
// What each card lists: the own items (when there are any), then the inherited groups
const withOwn = (own, groups) => [...(own.length ? [{ own: true, owner: "own", items: own }] : []), ...groups];
const documentGroups = computed(() => withOwn(documents.value, inheritedDocuments.value));
const photoGroups = computed(() => withOwn(photos.value, inheritedPhotos.value));
// The viewer steps through every photo shown: own first, then each group's
const allPhotos = computed(() => [...photos.value, ...inheritedPhotos.value.flatMap((g) => g.items)]);
const removeNote = computed(() =>
  props.everySite ? `It disappears from every machine of this ${props.everySite}.` : "",
);

// Object URLs, by document id.  Image URLs are cached as promises, so two requests for
// the same image share one fetch.
const thumbUrls = ref({});      // id -> URL, for the grid
const thumbFailed = ref({});    // id -> true when the thumbnail could not be fetched
let fullImages = new Map();     // id -> Promise<URL>, for the viewer
const pdfUrls = new Map();      // id -> URL; kept until unmount

const fileUrl = (doc) => `${doc.path}/${doc.id}/file`;
const tagged = (list, path, own) => list.map((d) => ({ ...d, path, own }));

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

function loadThumbs(seq) {
  for (const photo of allPhotos.value) {
    const url = `${photo.path}/${photo.id}/${photo.has_thumb ? "thumb" : "file"}`;
    objectUrl(url).then(
      (loaded) => {
        // A reload or a new owner since: this URL belongs to nobody
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
  const basePath = props.basePath;
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const result = await apiGet(basePath);
    if (seq !== loadSeq) return;
    revokeImages();
    items.value = tagged(result.items, basePath, true);
    inherited.value = (result.inherited ?? []).map((g) => ({ ...g, items: tagged(g.items, g.path, false) }));
    uploadMaxMb.value = result.upload_max_mb;
    loadThumbs(seq);
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

// Follow the owner: Vue Router reuses the equipment page when only :id changes, and a
// Masters panel switches from one model to another
watch(() => props.basePath, () => {
  revokeImages();
  items.value = [];
  inherited.value = [];
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

function openViewer(photo) {
  viewer.value.open(allPhotos.value.findIndex((p) => p.id === photo.id));
}

// ---------------------------------------------------------------------------
// Edit title, remove (own items only)
// ---------------------------------------------------------------------------

async function editFromViewer(photo) {
  await viewer.value.close();
  titleModal.value.open(photo);
}

async function remove(doc) {
  removing.value = true;
  actionError.value = "";
  try {
    await apiDelete(`${props.basePath}/${doc.id}`);
    confirmingRemoveId.value = null;
    await load();
    emit("changed");
  } catch (err) {
    actionError.value = err.message;
  } finally {
    // From the viewer: close it either way, so the photo is gone or the error is visible
    if (doc.kind === "photo") await viewer.value.close();
    removing.value = false;
  }
}

// The upload and the title dialogs: show the new list, then tell the parent
async function onSaved() {
  await load();
  emit("changed");
}

// The equipment page calls this after a node edit: a new model brings other documents
defineExpose({ reload: load });
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
          <button v-if="canEditDocs" class="btn btn-sm btn-outline-primary" @click="uploadModal.open('document')">
            <i class="fa-solid fa-plus me-1"></i>Add document
          </button>
        </div>
        <!-- "No documents yet." is about the own section, so only when nothing is inherited either -->
        <div v-if="!documentGroups.length" class="card-body text-secondary">
          {{ loading ? "Loading…" : "No documents yet." }}
        </div>
        <template v-for="(group, i) in documentGroups" :key="group.owner">
          <div
            v-if="!group.own"
            class="group-heading small d-flex flex-wrap justify-content-between gap-1"
            :class="{ 'border-top': i > 0 }"
          >
            <span>From {{ group.owner }} <em>{{ group.label }}</em></span>
            <span v-if="showManagedIn" class="text-secondary">Managed in Masters › {{ MANAGED_IN[group.owner] }}</span>
          </div>
          <ul class="list-group list-group-flush">
            <li v-for="doc in group.items" :key="doc.id" class="list-group-item">
              <!-- The title opens the PDF; Download is one labelled button; Edit title and Remove sit
                   in the "⋯" menu, apart from it (S064 UX-10) -->
              <div class="d-flex flex-wrap align-items-start gap-2">
                <i class="fa-regular fa-file-pdf text-danger mt-1"></i>
                <div class="flex-grow-1 doc-text">
                  <button
                    type="button"
                    class="btn btn-link p-0 fw-semibold text-start text-decoration-none doc-title"
                    title="Open in a new tab"
                    @click="openPdf(doc)"
                  >
                    {{ doc.title }}
                  </button>
                  <div class="small text-secondary">
                    {{ doc.original_name }} · {{ formatBytes(doc.size_bytes) }} ·
                    {{ doc.created_by }}, {{ formatDateTime(doc.created_at) }}
                  </div>
                  <div v-if="canEditDocs && doc.own && confirmingRemoveId === doc.id" class="d-flex flex-wrap align-items-center gap-2 mt-2">
                    <span>Remove this document?<template v-if="removeNote"> {{ removeNote }}</template></span>
                    <button class="btn btn-sm btn-danger" :disabled="removing" @click="remove(doc)">Yes</button>
                    <button class="btn btn-sm btn-outline-secondary" @click="confirmingRemoveId = null">No</button>
                  </div>
                </div>
                <div class="d-flex gap-2">
                  <button type="button" class="btn btn-outline-secondary tap-target" @click="downloadPdf(doc)">
                    <i class="fa-solid fa-download me-1"></i>Download
                  </button>
                  <div v-if="canEditDocs && doc.own" class="dropdown">
                    <button
                      type="button"
                      class="btn btn-outline-secondary tap-target"
                      data-bs-toggle="dropdown"
                      aria-expanded="false"
                      aria-label="More actions"
                      title="More actions"
                    >
                      <i class="fa-solid fa-ellipsis"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end">
                      <li>
                        <button type="button" class="dropdown-item" @click="titleModal.open(doc)">
                          <i class="fa-solid fa-pen me-2"></i>Edit title
                        </button>
                      </li>
                      <li>
                        <button type="button" class="dropdown-item text-danger" @click="confirmingRemoveId = doc.id">
                          <i class="fa-solid fa-trash me-2"></i>Remove
                        </button>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </template>
      </div>
    </div>

    <div class="col-lg-6">
      <div class="card h-100">
        <div
          class="card-header"
          :class="largeAdd ? 'd-grid gap-2' : 'd-flex justify-content-between align-items-center'"
        >
          <span>Photos</span>
          <button
            v-if="canEdit"
            class="btn btn-outline-primary"
            :class="largeAdd ? 'btn-lg' : 'btn-sm'"
            @click="uploadModal.open('photo')"
          >
            <i class="fa-solid fa-camera me-1"></i>Add photo
          </button>
        </div>
        <div class="card-body">
          <div v-if="!photoGroups.length" class="text-secondary">
            {{ loading ? "Loading…" : "No photos yet." }}
          </div>
          <template v-for="(group, i) in photoGroups" :key="group.owner">
            <div v-if="!group.own" class="small d-flex flex-wrap justify-content-between gap-1 mb-2" :class="{ 'mt-3': i > 0 }">
              <span>From {{ group.owner }} <em>{{ group.label }}</em></span>
              <span v-if="showManagedIn" class="text-secondary">Managed in Masters › {{ MANAGED_IN[group.owner] }}</span>
            </div>
            <div class="d-flex flex-wrap gap-2">
              <button
                v-for="photo in group.items"
                :key="photo.id"
                type="button"
                class="photo-tile btn p-0 border"
                :title="photo.title"
                @click="openViewer(photo)"
              >
                <img v-if="thumbUrls[photo.id]" :src="thumbUrls[photo.id]" :alt="photo.title" />
                <span v-else class="photo-placeholder text-secondary">
                  <i class="fa-solid" :class="thumbFailed[photo.id] ? 'fa-image' : 'fa-spinner fa-spin'"></i>
                </span>
                <span class="photo-caption small text-truncate">{{ photo.title }}</span>
              </button>
            </div>
          </template>
        </div>
      </div>
    </div>

    <DocumentUploadModal
      ref="uploadModal"
      :base-path="basePath"
      :every-site="Boolean(everySite)"
      :upload-max-mb="uploadMaxMb"
      @saved="onSaved"
    />
    <DocumentTitleModal ref="titleModal" :base-path="basePath" @saved="onSaved" />
    <PhotoViewer
      ref="viewer"
      :photos="allPhotos"
      :load-image="loadFullImage"
      :can-edit="canEdit"
      :removing="removing"
      :remove-note="removeNote"
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
.group-heading {
  padding: 0.5rem 1rem 0.25rem;
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
