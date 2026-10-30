<script setup>
/**
 * The Lessons card on the equipment page (docs/steps/S077-one-point-lesson-screens/1-brief.md § 5.1):
 * the machine's own one-point lessons and its class's, each with its first photo, its title in large
 * type and a badge when it is for the whole class. A row opens the lesson's page.
 *
 * It loads its own list (`GET /api/procedures?equipment_id=`), as MetersCard loads the node's meters.
 * It shows nothing for a reader of a machine with no lessons (no empty box on the floor); an engineer
 * or manager (`can_add`) always sees it, with "Add lesson". Retired lessons sit behind "Retired lessons
 * (n)" for the writers (the server sends `retired` only to them).
 *
 * Covers are fetched as blobs with the token (`/thumb` when the file has one, else `/file`, the rule of
 * DocumentsCards) and shown through object URLs, revoked on every reload and on unmount.
 *
 * The dialog is inside the card; the card emits `saved(lesson)` when it has closed after an add, and
 * the page decides what to show (it opens the lesson).
 */
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { apiGet, apiGetBlob } from "../../api";
import { equipmentClasses } from "../../stores/masters";
import { classBadgeText } from "../../utils/lessonLabels";
import LessonDialog from "./LessonDialog.vue";

const props = defineProps({
  node: { type: Object, required: true },
});
const emit = defineEmits(["saved"]);

const lessons = ref(null); // {items, retired, total, can_add}; null while loading
const loadError = ref("");
const showRetired = ref(false);
const covers = ref({}); // lesson id -> object URL
const dialog = ref(null);
let loadSeq = 0;

const visible = computed(() => {
  if (loadError.value) return true;
  const l = lessons.value;
  return Boolean(l) && (l.items.length > 0 || l.can_add || l.retired.length > 0);
});

// The active lessons, then the retired ones once "Retired lessons (n)" is tapped
const rows = computed(() => (lessons.value ? [...lessons.value.items, ...(showRetired.value ? lessons.value.retired : [])] : []));

function revokeCovers() {
  Object.values(covers.value).forEach((url) => URL.revokeObjectURL(url));
  covers.value = {};
}

function loadCovers(list, seq) {
  for (const lesson of list) {
    if (!lesson.cover) continue;
    const { doc_id: docId, has_thumb: hasThumb } = lesson.cover;
    apiGetBlob(`/api/procedures/${lesson.id}/documents/${docId}/${hasThumb ? "thumb" : "file"}`).then(
      (blob) => {
        const url = URL.createObjectURL(blob);
        // A reload or another machine since: this URL belongs to nobody
        if (seq === loadSeq) covers.value[lesson.id] = url;
        else URL.revokeObjectURL(url);
      },
      () => {}, // the row keeps its icon
    );
  }
}

async function load() {
  const seq = ++loadSeq;
  loadError.value = "";
  try {
    const loaded = await apiGet(`/api/procedures?equipment_id=${props.node.id}`);
    if (seq !== loadSeq) return;
    revokeCovers();
    lessons.value = loaded;
    loadCovers([...loaded.items, ...loaded.retired], seq);
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  }
}

// Vue Router reuses the page when only :id changes
watch(() => props.node.id, () => {
  lessons.value = null;
  showRetired.value = false;
  revokeCovers();
  load();
}, { immediate: true });

onBeforeUnmount(() => {
  loadSeq += 1;
  revokeCovers();
});

// The node's class for the dialog's tick; the page loaded the classes before the node
const nodeClass = computed(() => {
  const cls = (equipmentClasses.value ?? []).find((c) => c.id === props.node.class_id);
  return cls ? { id: cls.id, code: cls.code, name: cls.name } : null;
});

function openAdd() {
  const { id, code, name } = props.node;
  dialog.value.openCreate({ machine: { id, code, name, class: nodeClass.value } });
}

async function onSaved(lesson) {
  await load();
  emit("saved", lesson);
}
</script>

<template>
  <div class="order-0">
    <div v-if="visible" class="card mb-3" data-testid="lessons-card">
      <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
        <span>Lessons<template v-if="lessons?.total > 0"> ({{ lessons.total }})</template></span>
        <button v-if="lessons?.can_add" type="button" class="btn btn-sm btn-primary tap-target" @click="openAdd">
          <i class="fa-solid fa-plus me-1"></i>Add lesson
        </button>
      </div>
      <div v-if="loadError" class="card-body text-danger">Lessons could not be loaded: {{ loadError }}</div>
      <template v-else>
        <div v-if="rows.length === 0" class="card-body text-secondary">No lessons in use.</div>
        <div v-else class="list-group list-group-flush">
          <router-link
            v-for="l in rows"
            :key="l.id"
            :to="`/equipment/lessons/${l.id}`"
            class="list-group-item list-group-item-action d-flex align-items-center gap-3"
            :data-lesson="l.serial"
          >
            <img v-if="covers[l.id]" :src="covers[l.id]" alt="" class="cover" />
            <span v-else class="cover cover-icon text-secondary"><i class="fa-solid fa-chalkboard-user"></i></span>
            <span class="flex-grow-1 lesson-text">
              <span class="d-block fs-5">{{ l.title }}</span>
              <span class="small text-secondary">{{ l.serial }}</span>
              <span v-if="!l.active" class="badge text-bg-secondary ms-2">Retired</span>
              <span v-if="l.for_class" class="badge text-bg-info ms-2">{{ classBadgeText(l.class) }}</span>
            </span>
          </router-link>
        </div>
        <div v-if="lessons.retired.length" class="card-footer">
          <button type="button" class="btn btn-link p-0 tap-target" :aria-expanded="showRetired" @click="showRetired = !showRetired">
            Retired lessons ({{ lessons.retired.length }})
          </button>
        </div>
      </template>
    </div>
    <LessonDialog ref="dialog" @saved="onSaved" />
  </div>
</template>

<style scoped>
.cover {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 0.25rem;
  flex: none;
}
.cover-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bs-secondary-bg);
  font-size: 1.5rem;
}
.lesson-text {
  min-width: 0;
  overflow-wrap: anywhere;
}
</style>
