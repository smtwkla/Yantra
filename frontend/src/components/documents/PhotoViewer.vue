<script setup>
/**
 * Photo viewer — one photo large, with previous/next (docs/steps/S006-equipment-documents/1-brief.md § 1).
 *
 * The parent owns the photos and their object URLs: `loadImage(photo)` resolves to a URL
 * of the full image, so revoking stays in one place (DocumentsCards). The parent calls
 * open(index) / close() through a template ref; close() resolves once the modal is hidden,
 * so another dialog can open after it. Edit and Remove are emitted, not done here, and
 * offered only on the owner's own photos (`photo.own`), not on a model's shown on a node
 * (S012).
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Modal } from "bootstrap";

const props = defineProps({
  photos: { type: Array, required: true },
  loadImage: { type: Function, required: true },
  canEdit: { type: Boolean, default: false },
  removing: { type: Boolean, default: false },
  // Added to the remove confirmation, e.g. that a model photo leaves every machine of the model
  removeNote: { type: String, default: "" },
});
const emit = defineEmits(["edit", "remove"]);

const el = ref(null);
let modal = null;
const shown = ref(false);

const index = ref(0);
const url = ref("");
const loadError = ref("");
const confirmingRemove = ref(false);
let loadSeq = 0;

const photo = computed(() => props.photos[index.value] ?? null);
const editable = computed(() => props.canEdit && Boolean(photo.value?.own));

async function show() {
  const current = photo.value;
  const seq = ++loadSeq;
  url.value = "";
  loadError.value = "";
  confirmingRemove.value = false;
  if (!current) return;
  try {
    const loaded = await props.loadImage(current);
    if (seq === loadSeq) url.value = loaded;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  }
}

function step(delta) {
  const count = props.photos.length;
  if (count) index.value = (index.value + delta + count) % count;
}

watch(() => photo.value?.id, () => {
  if (shown.value) show();
});
// The list reloads after an edit or a removal: keep the index inside it
watch(() => props.photos.length, (count) => {
  if (index.value >= count) index.value = Math.max(count - 1, 0);
});

function open(at) {
  shown.value = true;
  // A new index loads through the watcher above; the same one is loaded here
  if (index.value === at) show();
  else index.value = at;
  modal.show();
}

function close() {
  if (!shown.value) return Promise.resolve();
  return new Promise((resolve) => {
    el.value.addEventListener("hidden.bs.modal", () => resolve(), { once: true });
    modal.hide();
  });
}

function onHidden() {
  shown.value = false;
  loadSeq += 1;
}

onMounted(() => {
  modal = Modal.getOrCreateInstance(el.value);
  el.value.addEventListener("hidden.bs.modal", onHidden);
});
onBeforeUnmount(() => {
  modal?.dispose();
});

defineExpose({ open, close });
</script>

<template>
  <div ref="el" class="modal fade" tabindex="-1">
    <!-- The whole screen on a phone, the photo sized to the space left, so Previous / Next stay
         on screen (S064 UX-09) -->
    <div class="modal-dialog modal-xl modal-dialog-centered modal-fullscreen-sm-down">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title photo-title">{{ photo?.title }}</h5>
          <button type="button" class="btn-close" aria-label="Close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body text-center photo-body">
          <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
          <img v-else-if="url" :src="url" :alt="photo?.title" class="photo-large" />
          <div v-else class="text-secondary py-5">Loading…</div>
        </div>
        <div class="modal-footer">
          <div class="me-auto d-flex flex-wrap align-items-center gap-2">
            <template v-if="editable">
              <span v-if="confirmingRemove" class="d-inline-flex align-items-center gap-2">
                <span>Remove this photo?<template v-if="removeNote"> {{ removeNote }}</template></span>
                <button type="button" class="btn btn-sm btn-danger" :disabled="removing" @click="emit('remove', photo)">Yes</button>
                <button type="button" class="btn btn-sm btn-outline-secondary" @click="confirmingRemove = false">No</button>
              </span>
              <template v-else>
                <button type="button" class="btn btn-sm btn-outline-primary" @click="emit('edit', photo)">
                  <i class="fa-solid fa-pen me-1"></i>Edit title
                </button>
                <button type="button" class="btn btn-sm btn-outline-danger" @click="confirmingRemove = true">
                  <i class="fa-solid fa-trash me-1"></i>Remove
                </button>
              </template>
            </template>
          </div>
          <span v-if="photos.length > 1" class="text-secondary small">{{ index + 1 }} / {{ photos.length }}</span>
          <button type="button" class="btn btn-outline-secondary" :disabled="photos.length < 2" title="Previous" @click="step(-1)">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <button type="button" class="btn btn-outline-secondary" :disabled="photos.length < 2" title="Next" @click="step(1)">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.photo-body {
  min-height: 200px;
}
.photo-large {
  max-width: 100%;
  max-height: 75vh;
  object-fit: contain;
}
/* A long title wraps to two lines, then is cut */
.photo-title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  overflow-wrap: anywhere;
}
/* Below sm the dialog is the screen: the photo takes what the header and footer leave */
@media (max-width: 575.98px) {
  .photo-large {
    max-height: calc(100dvh - 9rem);
  }
}
</style>
