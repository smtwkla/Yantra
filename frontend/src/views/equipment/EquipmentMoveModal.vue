<script setup>
/**
 * Move dialog (docs/steps/S003-equipment-screens/1-brief.md § 4.4): equipment moves to
 * another unit, a part to another parent. Sends only unit_id or only parent_id.
 *
 * The parent calls open(node) through a template ref and handles @saved.
 */
import { computed, ref, watch } from "vue";
import { apiGet } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useDebounced } from "../../composables/useDebounced";
import { useFormModal } from "../../composables/useFormModal";
import { ensureMyUnits, myUnits, pickableUnits } from "../../stores/equipment";
import { ensureSites, ensureUnits, sites, units } from "../../stores/masters";

const emit = defineEmits(["saved"]);

const SEARCH_LIMIT = 20; // per search; the hint below tells when there are more

const node = ref(null);
const search = ref("");
const matches = ref([]);
const searching = ref(false);
const searchError = ref("");
const moreMatches = ref(false); // the API found more than the dialog shows
const chosen = ref(null); // the parent picked in the list, for display
let searchSeq = 0;

const isEquipment = computed(() => node.value?.level === "equipment");
const currentParentId = computed(() => node.value?.ancestors?.at(-1)?.id ?? null);

const {
  modal, form, saving, error, fieldError, modalError, openEdit, save,
} = useFormModal({
  path: "/api/equipment",
  blank: () => ({ unit_id: "" }),
  fromRecord: (record) => (record.level === "equipment" ? { unit_id: "" } : { parent_id: null }),
  afterSave: (result) => emit("saved", result),
});

// Units the user may move to, grouped by site; the current unit cannot be picked
// because the API silently ignores a move to the same unit
const groups = computed(() => {
  const pickable = myUnits.value ? pickableUnits(units.value, myUnits.value) : [];
  return (sites.value ?? [])
    .map((s) => ({ site: s, units: pickable.filter((u) => u.site_id === s.id && u.id !== node.value?.unit_id) }))
    .filter((g) => g.units.length);
});

const saveDisabledReason = computed(() => {
  if (isEquipment.value) return form.value.unit_id === "" ? "Choose a unit" : "";
  return form.value.parent_id === null ? "Choose a new parent" : "";
});

async function runSearch() {
  const text = search.value.trim();
  const seq = ++searchSeq;
  searchError.value = "";
  if (text === "") {
    matches.value = [];
    moreMatches.value = false;
    searching.value = false;
    return;
  }
  searching.value = true;
  // A component-unit's parent is equipment; a component's is equipment or a component-unit.
  // Separate searches per level, so components can never use up the row limit.
  const levels = node.value.level === "component_unit" ? ["equipment"] : ["equipment", "component_unit"];
  try {
    const pages = await Promise.all(levels.map(
      (level) => apiGet(`/api/equipment?level=${level}&per_page=${SEARCH_LIMIT}&q=${encodeURIComponent(text)}`)
    ));
    if (seq !== searchSeq) return;
    matches.value = pages
      .flatMap((p) => p.items)
      .filter((m) => m.id !== node.value.id && m.id !== currentParentId.value);
    moreMatches.value = pages.some((p) => p.total > p.items.length);
  } catch (err) {
    if (seq !== searchSeq) return;
    searchError.value = err.message;
    matches.value = [];
    moreMatches.value = false;
  } finally {
    if (seq === searchSeq) searching.value = false;
  }
}

const { schedule: scheduleSearch } = useDebounced(runSearch);
watch(search, scheduleSearch);

function choose(match) {
  chosen.value = match;
  form.value.parent_id = match.id;
}

async function open(target) {
  let loadError = null;
  try {
    await Promise.all([ensureSites(), ensureUnits(), ensureMyUnits()]);
  } catch (err) {
    loadError = err.message;
  }
  node.value = target;
  search.value = "";
  matches.value = [];
  moreMatches.value = false;
  searchError.value = "";
  chosen.value = null;
  openEdit(target);
  if (loadError) error.value = { field: null, message: loadError };
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    :title="`Move ${node?.code ?? ''}`"
    :saving="saving"
    :error="modalError"
    :save-disabled-reason="saveDisabledReason"
    @save="save"
  >
    <template v-if="node && isEquipment">
      <div class="mb-3">
        <label class="form-label">Current unit</label>
        <div class="form-control-plaintext py-0">{{ node.unit }}</div>
      </div>
      <div class="mb-0">
        <label class="form-label" for="move-unit">Move to unit</label>
        <select id="move-unit" v-model="form.unit_id" class="form-select" :class="{ 'is-invalid': fieldError('unit_id') }">
          <option value="" disabled>Select a unit…</option>
          <optgroup v-for="g in groups" :key="g.site.id" :label="g.site.code">
            <option v-for="u in g.units" :key="u.id" :value="u.id">{{ u.full_code }} — {{ u.name }}</option>
          </optgroup>
        </select>
        <div class="invalid-feedback">{{ fieldError("unit_id") }}</div>
        <div class="form-text">Its parts move with it.</div>
      </div>
    </template>
    <template v-else-if="node">
      <div class="mb-3">
        <label class="form-label">Current parent</label>
        <div class="form-control-plaintext py-0">{{ node.ancestors.at(-1)?.code }}</div>
      </div>
      <div class="mb-0">
        <label class="form-label" for="move-search">New parent</label>
        <input
          id="move-search"
          v-model="search"
          class="form-control"
          :class="{ 'is-invalid': fieldError('parent_id') }"
          placeholder="Search by code or name…"
          autocomplete="off"
        />
        <div class="invalid-feedback">{{ fieldError("parent_id") }}</div>
        <div v-if="chosen" class="mt-2 small">Chosen: <strong>{{ chosen.code }}</strong> — {{ chosen.name }}</div>
        <div v-if="searchError" class="text-danger small mt-2">{{ searchError }}</div>
        <div v-else-if="searching" class="text-secondary small mt-2">Searching…</div>
        <div v-else-if="search.trim() && matches.length === 0" class="text-secondary small mt-2">No matching parent.</div>
        <div v-if="matches.length" class="list-group mt-2">
          <button
            v-for="m in matches"
            :key="m.id"
            type="button"
            class="list-group-item list-group-item-action"
            :class="{ active: form.parent_id === m.id }"
            @click="choose(m)"
          >
            <span class="fw-semibold">{{ m.code }}</span> {{ m.name }}
            <div class="small">{{ m.full_path }}</div>
          </button>
        </div>
        <div v-if="moreMatches && !searching" class="text-secondary small mt-2">
          More matches — type more of the code or name to refine the search.
        </div>
      </div>
    </template>
  </FormModal>
</template>
