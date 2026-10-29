<script setup>
/**
 * Add ticket (docs/steps/S068-improvement-screens/1-brief.md § 5.3): a search box and a radio list
 * of tickets. With no search, the newest tickets of the improvement's machine; with text, any
 * ticket of the site (serial or text). Tickets already in this improvement and not-a-fault
 * tickets are left out; the API judges the rest (another open improvement, another site).
 */
import { computed, ref } from "vue";
import { apiGet, apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import IntensityBadge from "../../components/IntensityBadge.vue";
import { useDebounced } from "../../composables/useDebounced";
import { useFormModal } from "../../composables/useFormModal";
import { problemText, stateLabel } from "../../utils/ticketLabels";

const PICKER_SIZE = 10;

const props = defineProps({
  improvement: { type: Object, required: true },
});
const emit = defineEmits(["saved"]);

const searchText = ref("");
const tickets = ref(null); // null until the first answer
const loading = ref(false);
const loadError = ref("");
let loadSeq = 0;

const { modal, form, saving, dirty, error, fieldError, openCreate, send } = useFormModal({
  path: null,
  blank: () => ({ ticket_id: null }),
  afterSave: (result) => emit("saved", result),
});

const topError = computed(() => loadError.value || (error.value && error.value.field !== "ticket_id" ? error.value.message : ""));
const hereIds = computed(() => props.improvement.tickets.map((t) => t.id));
const choices = computed(() => (tickets.value ?? []).filter((t) => !hereIds.value.includes(t.id) && !t.not_a_fault));

function listUrl() {
  const text = searchText.value.trim();
  const params = new URLSearchParams({ state: "all", per_page: String(PICKER_SIZE) });
  if (text) {
    params.set("site_id", String(props.improvement.unit.site_id));
    params.set("q", text);
  } else {
    params.set("equipment_id", String(props.improvement.machine.id));
  }
  return `/api/tickets?${params}`;
}

async function load() {
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const result = await apiGet(listUrl());
    if (seq !== loadSeq) return;
    tickets.value = result.items;
    if (!tickets.value.some((t) => t.id === form.value.ticket_id)) form.value.ticket_id = null;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

const { schedule: scheduleSearch } = useDebounced(load);

function open() {
  searchText.value = "";
  tickets.value = null;
  openCreate();
  load();
}

function save() {
  if (!form.value.ticket_id) {
    error.value = { field: "ticket_id", message: "Choose a ticket" };
    return;
  }
  return send(() => apiPost(`/api/improvements/${props.improvement.id}/tickets`, { ticket_id: form.value.ticket_id }));
}

defineExpose({ open });
</script>

<template>
  <FormModal ref="modal" title="Add ticket" :saving="saving" :dirty="dirty" :error="topError" save-label="Add ticket" @save="save">
    <label class="form-label" for="add-ticket-search">Which ticket belongs here?</label>
    <input
      id="add-ticket-search"
      v-model="searchText"
      class="form-control mb-2"
      type="search"
      placeholder="Search serial or text…"
      @input="scheduleSearch"
    />
    <div class="form-text mb-2">
      Without a search, the newest tickets of {{ improvement.machine.code }} show. A search looks at every ticket of the site.
    </div>
    <div v-if="loading && !tickets" class="text-secondary">Loading…</div>
    <div v-else-if="tickets && !choices.length" class="text-secondary">No tickets match.</div>
    <div v-else class="list-group" role="radiogroup" aria-label="Tickets">
      <label v-for="t in choices" :key="t.id" class="list-group-item list-group-item-action d-flex gap-2 align-items-start">
        <input v-model="form.ticket_id" class="form-check-input mt-1 flex-shrink-0" type="radio" name="add-ticket" :value="t.id" />
        <span class="flex-grow-1 text-break">
          <span class="d-flex flex-wrap align-items-center gap-2">
            <span class="fw-semibold">{{ t.serial }}</span>
            <IntensityBadge :intensity="t.intensity" />
            <span class="small text-secondary">{{ stateLabel(t) }}</span>
          </span>
          <span class="d-block small">{{ t.machine.code }} · {{ problemText(t) }}</span>
        </span>
      </label>
    </div>
    <div v-if="fieldError('ticket_id')" class="invalid-feedback d-block mt-2">{{ fieldError("ticket_id") }}</div>
  </FormModal>
</template>
