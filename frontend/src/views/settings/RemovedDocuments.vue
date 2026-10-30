<script setup>
/**
 * Removed documents card on the Settings page (docs/steps/S008-removed-documents/1-brief.md).
 * For equipment:purge_documents: lists removed documents and photos, restores one, or deletes
 * one for good (row, file and thumbnail). A removed file is never shown or opened here
 * (S006 § 5.5): restore it to look at it. Filters are local state, not the URL.
 *
 * Rows are a node's documents or, since S012, an equipment model's (`owner`). Each row brings
 * its owner's documents URL (`path`); restore and purge are that URL + the id + the action.
 * A model row shows "Model <label>" as plain text: Masters sections are not routes.
 * Since S017 a row can also be a ticket's photo: "Ticket <serial>" and its unit; Restore is
 * disabled on a closed ticket, as on scrapped equipment (the server refuses both).
 * Since S071 a row can be a countermeasure's photo: "Countermeasure IM-… · Corrective" and its
 * unit; Restore is disabled on a cancelled countermeasure (S070 § 5.8), and since S072 A1 also
 * when its improvement is closed or dropped, as on a closed ticket.
 * Since S077 a row can be a one-point lesson's photo: "Lesson OPL-007", its machine's code and its unit;
 * a lesson has no state rule, so Restore is never disabled for one.
 */
import { onMounted, ref, watch } from "vue";
import { apiGet, apiPost } from "../../api";
import PagerBar from "../../components/PagerBar.vue";
import { useDebounced } from "../../composables/useDebounced";
import { formatDateTime } from "../../utils/datetime";
import { formatBytes } from "../../utils/format";
import { actionKindLabel } from "../../utils/improvementLabels";

const PAGE_SIZE = 50; // sent explicitly, so the pager and the request agree if the API default changes

const result = ref(null); // {items, total, page, per_page}
const loading = ref(false);
const loadError = ref("");
const actionError = ref("");
const note = ref(null); // {text, warning}
const confirmingId = ref(null);
const busy = ref(false);
const pageNumber = ref(1);
const searchText = ref("");
const kind = ref("");
let loadSeq = 0;

function listPath(page) {
  const params = new URLSearchParams({ page: String(page), per_page: String(PAGE_SIZE) });
  if (kind.value) params.set("kind", kind.value);
  if (searchText.value.trim()) params.set("q", searchText.value.trim());
  return `/api/equipment/removed-documents?${params}`;
}

// afterAction: a restore or purge just removed one item, so an empty page > 1 means it held the
// last one; step back once (one action removes at most one item). A plain load never steps back.
async function load(afterAction = false) {
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  confirmingId.value = null;
  try {
    let page = pageNumber.value;
    let loaded = await apiGet(listPath(page));
    if (afterAction === true && loaded.items.length === 0 && page > 1) {
      page -= 1;
      loaded = await apiGet(listPath(page));
    }
    if (seq !== loadSeq) return;
    pageNumber.value = page;
    result.value = loaded;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

function restart() {
  pageNumber.value = 1;
  load();
}

const { schedule: scheduleSearch } = useDebounced(restart);
watch(searchText, scheduleSearch);
watch(kind, restart);

function goToPage(page) {
  pageNumber.value = page;
  load();
}

const actionPath = (item, action) => `${item.path}/${item.id}/${action}`;

// Why Restore is disabled for a row, or "" when it is not: the server would refuse it
function restoreBlocked(item) {
  if (item.lifecycle === "scrapped") return "Scrapped equipment cannot be changed";
  if (item.owner === "ticket" && item.state === "closed") return "Closed tickets cannot be changed";
  if (item.owner === "action" && item.state === "cancelled") return "Cancelled countermeasures cannot be changed";
  // S072 A1: a closed or dropped improvement is read-only
  if (item.owner === "action" && item.improvement_open === false) return "Closed improvements cannot be changed";
  return "";
}

async function act(item, action, onDone) {
  busy.value = true;
  actionError.value = "";
  note.value = null;
  try {
    onDone(await apiPost(actionPath(item, action)));
  } catch (err) {
    actionError.value = err.message;
    confirmingId.value = null;
  } finally {
    busy.value = false;
  }
  // Reload on failure too, so a stale row (already restored or purged by someone else) disappears;
  // load() leaves actionError alone, so the alert stays visible.
  await load(true);
}

const restore = (item) => act(item, "restore", () => {
  note.value = { text: `Restored '${item.title}'.`, warning: false };
});

// 200 with a warning: the record is gone but a file is still on the share
const purge = (item) => act(item, "purge", (answer) => {
  note.value = answer?.warning
    ? { text: answer.warning, warning: true }
    : { text: `Deleted '${item.title}' for good.`, warning: false };
});

onMounted(load);
</script>

<template>
  <div class="card mt-3">
    <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
      <span>
        <i class="fa-solid fa-trash-can-arrow-up me-2"></i>Removed documents
        <span v-if="result" class="text-secondary small">({{ result.total }})</span>
      </span>
      <div class="d-flex flex-wrap gap-2">
        <input
          v-model="searchText"
          type="search"
          class="form-control form-control-sm removed-search"
          placeholder="Search equipment code, model, ticket, improvement, lesson number, title or file name…"
          aria-label="Search removed documents"
        />
        <select v-model="kind" class="form-select form-select-sm removed-kind" aria-label="Kind">
          <option value="">All</option>
          <option value="document">Documents</option>
          <option value="photo">Photos</option>
        </select>
      </div>
    </div>
    <div class="card-body">
      <div v-if="note" class="alert py-2" :class="note.warning ? 'alert-warning' : 'alert-success'">{{ note.text }}</div>
      <div v-if="actionError" class="alert alert-danger py-2">{{ actionError }}</div>

      <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center mb-0">
        <span>Removed documents could not be loaded: {{ loadError }}</span>
        <button class="btn btn-sm btn-outline-danger" @click="load()">Retry</button>
      </div>
      <div v-else-if="!result" class="text-secondary">Loading…</div>
      <template v-else>
        <div v-if="loading" class="text-secondary small mb-1">Loading…</div>
        <div v-if="result.total === 0" class="text-secondary">
          {{ kind || searchText.trim() ? "No removed documents match." : "No removed documents." }}
        </div>
        <div v-else-if="result.items.length === 0" class="text-secondary">No removed documents on this page.</div>
        <div v-else class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead>
              <tr>
                <th>Removed</th>
                <th>Title</th>
                <th>Belongs to</th>
                <th>Uploaded</th>
                <th>Size</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in result.items" :key="item.id" :class="{ 'text-secondary': restoreBlocked(item) }">
                <td>
                  {{ formatDateTime(item.removed_at) }}
                  <div class="small text-secondary">{{ item.removed_by }}</div>
                </td>
                <td class="text-break">
                  <i
                    class="fa-regular me-1"
                    :class="item.kind === 'photo' ? 'fa-image text-success' : 'fa-file-pdf text-danger'"
                  ></i>{{ item.title }}
                  <div class="small text-secondary">{{ item.original_name }}</div>
                </td>
                <td v-if="item.owner === 'model'">
                  Model <em>{{ item.name }}</em>
                  <div class="small text-secondary">Every machine of this model</div>
                </td>
                <td v-else-if="item.owner === 'ticket'">
                  Ticket {{ item.name }}
                  <div v-if="item.state === 'closed'" class="small">closed</div>
                  <div class="small text-secondary">{{ item.unit }}</div>
                </td>
                <td v-else-if="item.owner === 'action'">
                  Countermeasure {{ item.name }} · {{ actionKindLabel(item.action_kind) }}
                  <div v-if="item.state === 'cancelled'" class="small">cancelled</div>
                  <div class="small text-secondary">{{ item.unit }}</div>
                </td>
                <td v-else-if="item.owner === 'procedure'">
                  Lesson {{ item.name }}
                  <div class="small text-secondary">{{ item.code }} · {{ item.unit }}</div>
                </td>
                <td v-else>
                  <router-link :to="`/equipment/${item.equipment_id}`">{{ item.code }}</router-link>
                  {{ item.name }}
                  <div v-if="item.lifecycle === 'scrapped'" class="small">scrapped</div>
                  <div class="small text-secondary">{{ item.full_path }}</div>
                </td>
                <td>
                  {{ item.created_by }}
                  <div class="small text-secondary">{{ formatDateTime(item.created_at) }}</div>
                </td>
                <td class="text-nowrap">{{ formatBytes(item.size_bytes) }}</td>
                <td class="text-end">
                  <span v-if="confirmingId === item.id" class="d-inline-flex flex-wrap align-items-center justify-content-end gap-2">
                    <span>Delete for good? The file cannot be recovered.</span>
                    <button class="btn btn-sm btn-danger" :disabled="busy" @click="purge(item)">Delete for good</button>
                    <button class="btn btn-sm btn-outline-secondary" :disabled="busy" @click="confirmingId = null">No</button>
                  </span>
                  <span v-else class="d-inline-flex flex-wrap gap-1 justify-content-end">
                    <!-- Bootstrap gives a disabled .btn no pointer events, so the title (and the tab stop, for keyboard users) sits on the wrapper, only when blocked -->
                    <span
                      class="d-inline-block"
                      :tabindex="restoreBlocked(item) ? 0 : undefined"
                      :title="restoreBlocked(item) || undefined"
                    >
                      <button
                        class="btn btn-sm btn-outline-primary"
                        :disabled="busy || Boolean(restoreBlocked(item))"
                        @click="restore(item)"
                      >
                        <i class="fa-solid fa-rotate-left me-1"></i>Restore
                      </button>
                    </span>
                    <button class="btn btn-sm btn-outline-danger" :disabled="busy" @click="confirmingId = item.id">
                      <i class="fa-solid fa-trash me-1"></i>Delete for good
                    </button>
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <PagerBar :page="result.page" :total="result.total" :per-page="result.per_page" @page="goToPage" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.removed-search {
  width: 20rem;
  max-width: 100%;
}
.removed-kind {
  width: auto;
}
</style>
