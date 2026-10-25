<script setup>
/**
 * Find a node by code or name among the user's units, at any level (S017 § 1; shared since S050
 * § 1.3, BR1-04): up to 20 matches of GET /api/equipment?level=all&q=, each "code — name" with its
 * full path. Emits @pick with the node's id; the screen decides what a pick does (Raise ticket
 * opens the form, the readings register shows the node's readings).
 */
import { ref, watch } from "vue";
import { apiGet } from "../api";
import { useDebounced } from "../composables/useDebounced";

const PICKER_SIZE = 20;

const emit = defineEmits(["pick"]);

const searchText = ref("");
const results = ref(null);
const searching = ref(false);
const searchError = ref("");
let searchSeq = 0;

async function search() {
  const text = searchText.value.trim();
  const seq = ++searchSeq;
  searchError.value = "";
  if (!text) {
    results.value = null;
    return;
  }
  searching.value = true;
  try {
    const params = new URLSearchParams({ level: "all", q: text, per_page: String(PICKER_SIZE) });
    const page = await apiGet(`/api/equipment?${params}`);
    if (seq === searchSeq) results.value = page;
  } catch (err) {
    if (seq === searchSeq) searchError.value = err.message;
  } finally {
    if (seq === searchSeq) searching.value = false;
  }
}

const { schedule: scheduleSearch } = useDebounced(search);
watch(searchText, scheduleSearch);
</script>

<template>
  <div>
    <label class="form-label" for="equipment-search">Which equipment?</label>
    <input
      id="equipment-search"
      v-model="searchText"
      class="form-control form-control-lg mb-2"
      type="search"
      placeholder="Code or name"
      autocomplete="off"
    />
    <div v-if="searching" class="text-secondary small">Searching…</div>
    <div v-if="searchError" class="alert alert-danger py-2">{{ searchError }}</div>
    <div v-else-if="results && results.items.length === 0" class="text-secondary">No equipment found at your units.</div>
    <div v-else-if="results" class="list-group">
      <button
        v-for="e in results.items"
        :key="e.id"
        type="button"
        class="list-group-item list-group-item-action py-3"
        @click="emit('pick', e.id)"
      >
        <span class="fw-semibold">{{ e.code }}</span> — {{ e.name }}
        <div class="small text-secondary">{{ e.full_path }}</div>
      </button>
      <div v-if="results.total > results.items.length" class="list-group-item small text-secondary">
        More found — type more of the code or name.
      </div>
    </div>
  </div>
</template>
