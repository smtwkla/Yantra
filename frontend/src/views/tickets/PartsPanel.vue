<script setup>
/**
 * Parts used on a ticket (docs/steps/S020-parts-used/1-brief.md § 1): lines of what was fitted —
 * description, part number and where it comes from, maker, quantity and unit, and the node it was
 * fitted to (the machine or one of its parts). The spare parts of ISO 14224's maintenance record
 * (Table 8), beside the labour. No stock, cost or ordering: those stay in OneERP.
 *
 * On LabourPanel.vue's pattern: a dialog through FormModal, and Remove asks inline first. Lines
 * are added, changed and removed by ticket:work holders until the ticket closes.
 *
 * The dialog, top to bottom (phone first):
 * - Description, and directly under it on Add the "Fitted here before" list: the lines already
 *   recorded on this machine and its parts, on any ticket, newest first (fetched once when the
 *   dialog opens); five show, the rest behind More; typing in Description narrows it; a tap fills
 *   number, kind, maker and description (§ 1.4). Edit does not show it;
 * - Part number with a help line; while it has text, its kind as two choice buttons (default the
 *   standard number) and Maker marked required for a maker's number (BR2-02);
 * - Quantity, sent as the text typed (inputmode decimal, BR2-01), and its unit;
 * - Fitted to: the machine first, then its parts (utils/machineParts.js); the line's own node
 *   stays a choice when it is no longer listed (scrapped since).
 * The API decides every refusal; it is shown beside the field it names.
 */
import { computed, ref } from "vue";
import { apiDelete, apiGet, apiPost, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { keepChoice, loadMachineParts } from "../../utils/machineParts";
import {
  DEFAULT_PART_KIND, matchingParts, PART_KIND_CHOICES, PART_KIND_SHORT, PART_UNITS, partText, quantityText,
} from "../../utils/ticketLabels";

const props = defineProps({
  ticket: { type: Object, required: true },
  canEdit: { type: Boolean, default: false },
});
const emit = defineEmits(["saved"]);

const SHOWN_FIELDS = ["description", "part_number", "number_kind", "maker", "quantity", "qty_unit", "node_id"];
// From this many lines the list flows into columns, so an overhaul's 100+ parts stay scannable
const COLUMNS_FROM = 6;
const SUGGESTIONS_SHOWN = 5; // the newest; the rest behind More (§ 1.4)
const DESCRIPTION_MAX = 200;
const NUMBER_MAX = 60;
const MAKER_MAX = 100;

const confirmingRemoveId = ref(null);
const removing = ref(false);
const removeError = ref("");
const nodes = ref([]);
const nodesError = ref("");
const suggestions = ref([]);
const showAllSuggestions = ref(false);
let openSeq = 0; // a slow answer for an earlier opening is dropped

const { modal, form, editingId, saving, dirty, error, fieldError, openCreate, openEdit, send } = useFormModal({
  path: null,
  blank: (seed) => ({
    description: "", part_number: "", number_kind: DEFAULT_PART_KIND, maker: "", quantity: "1", qty_unit: "nos",
    node_id: "", ...seed,
  }),
  fromRecord: (row) => ({
    description: row.description, part_number: row.part_number ?? "", number_kind: row.number_kind ?? DEFAULT_PART_KIND,
    maker: row.maker ?? "", quantity: quantityText(row.quantity), qty_unit: row.qty_unit, node_id: row.node.id,
  }),
  afterSave: (result) => emit("saved", result),
});

const topError = computed(() => (error.value && !SHOWN_FIELDS.includes(error.value.field) ? error.value.message : ""));
const hasNumber = computed(() => form.value.part_number.trim() !== "");
const makerRequired = computed(() => hasNumber.value && form.value.number_kind === "maker");
const matching = computed(() => (editingId.value === null ? matchingParts(suggestions.value, form.value.description) : []));
const shownSuggestions = computed(() => (showAllSuggestions.value ? matching.value
  : matching.value.slice(0, SUGGESTIONS_SHOWN)));

function lineDetails(p) {
  const number = p.part_number ? `${p.part_number} (${PART_KIND_SHORT[p.number_kind] ?? p.number_kind})` : "";
  return [number, p.maker].filter(Boolean).join(" · ");
}

/** The machine first, then its parts; `current` (the line's node) kept when not listed. */
async function loadNodes(seq, current) {
  const machine = props.ticket.machine;
  nodesError.value = "";
  let parts = [];
  try {
    parts = await loadMachineParts(machine.id);
  } catch (err) {
    if (seq === openSeq) nodesError.value = `The machine's parts could not be loaded: ${err.message}`;
  }
  if (seq !== openSeq) return;
  nodes.value = keepChoice([{ id: machine.id, label: `${machine.code} ${machine.name}` }, ...parts], current);
}

async function loadSuggestions(seq) {
  suggestions.value = [];
  showAllSuggestions.value = false;
  try {
    const result = await apiGet(`/api/tickets/${props.ticket.id}/part-suggestions`);
    if (seq === openSeq) suggestions.value = result.items;
  } catch {
    // Only a help: the dialog works without it, so a failed fetch shows no list
  }
}

function openAdd() {
  const seq = ++openSeq;
  const t = props.ticket;
  const nodeId = t.component?.id ?? t.machine.id;
  // Until the parts arrive, the default is listed alone, so the select shows it
  nodes.value = keepChoice([{ id: t.machine.id, label: `${t.machine.code} ${t.machine.name}` }], t.component);
  openCreate({ node_id: nodeId });
  loadNodes(seq, t.component);
  loadSuggestions(seq);
}

function openChange(row) {
  const seq = ++openSeq;
  suggestions.value = [];
  nodes.value = [{ id: row.node.id, label: `${row.node.code} ${row.node.name}` }];
  openEdit(row);
  loadNodes(seq, row.node);
}

function useSuggestion(s) {
  Object.assign(form.value, {
    description: s.description, part_number: s.part_number ?? "", number_kind: s.number_kind ?? DEFAULT_PART_KIND,
    maker: s.maker ?? "",
  });
}

function save() {
  const f = form.value;
  const number = f.part_number.trim();
  const body = {
    description: f.description.trim(), part_number: number || null, maker: f.maker.trim() || null,
    quantity: f.quantity.trim(), qty_unit: f.qty_unit, node_id: Number(f.node_id),
  };
  if (number) body.number_kind = f.number_kind;
  const base = `/api/tickets/${props.ticket.id}/parts`;
  return send(() => (editingId.value === null ? apiPost(base, body) : apiPut(`${base}/${editingId.value}`, body)));
}

async function remove(row) {
  removing.value = true;
  removeError.value = "";
  try {
    const result = await apiDelete(`/api/tickets/${props.ticket.id}/parts/${row.id}`);
    confirmingRemoveId.value = null;
    emit("saved", result);
  } catch (err) {
    removeError.value = err.message;
  } finally {
    removing.value = false;
  }
}

defineExpose({ openAdd });
</script>

<template>
  <div class="card h-100">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span>Parts used</span>
      <button v-if="canEdit" class="btn btn-outline-primary" @click="openAdd">
        <i class="fa-solid fa-plus me-1"></i>Add part
      </button>
    </div>
    <div v-if="removeError" class="alert alert-danger py-2 m-2">{{ removeError }}</div>
    <div v-if="!ticket.parts.length" class="card-body text-secondary">No parts recorded</div>
    <ul v-else class="list-group list-group-flush" :class="{ 'part-columns': ticket.parts.length >= COLUMNS_FROM }">
      <li v-for="p in ticket.parts" :key="p.id" class="list-group-item part-line">
        <div class="d-flex flex-wrap align-items-center gap-2">
          <div class="flex-grow-1 text-break">
            <span class="fw-semibold">{{ quantityText(p.quantity) }} {{ p.qty_unit }}</span> · {{ p.description }}
            <div v-if="lineDetails(p)" class="small text-secondary">{{ lineDetails(p) }}</div>
            <div class="small text-secondary">Fitted to {{ p.node.code }} {{ p.node.name }}</div>
          </div>
          <template v-if="canEdit && confirmingRemoveId !== p.id">
            <button class="btn btn-outline-primary" title="Change" @click="openChange(p)">
              <i class="fa-solid fa-pen"></i>
            </button>
            <button class="btn btn-outline-danger" title="Remove" @click="confirmingRemoveId = p.id">
              <i class="fa-solid fa-trash"></i>
            </button>
          </template>
        </div>
        <div v-if="canEdit && confirmingRemoveId === p.id" class="d-flex flex-wrap align-items-center justify-content-end gap-3 mt-2">
          <span>Remove?</span>
          <button class="btn btn-danger" :disabled="removing" @click="remove(p)">Yes</button>
          <button class="btn btn-outline-secondary" @click="confirmingRemoveId = null">No</button>
        </div>
      </li>
    </ul>

    <FormModal
      ref="modal"
      :title="editingId === null ? 'Add part' : 'Change part'"
      :saving="saving"
      :dirty="dirty"
      :error="topError || nodesError"
      @save="save"
    >
      <div class="mb-3">
        <label class="form-label" for="part-description">Description</label>
        <input
          id="part-description"
          v-model="form.description"
          class="form-control"
          :class="{ 'is-invalid': fieldError('description') }"
          type="text"
          autocomplete="off"
          :maxlength="DESCRIPTION_MAX"
          placeholder="e.g. Deep-groove ball bearing"
        />
        <div v-if="fieldError('description')" class="invalid-feedback d-block">{{ fieldError("description") }}</div>
        <div v-if="matching.length" class="fitted-before mt-2">
          <div class="small text-secondary mb-1">Fitted here before</div>
          <div class="list-group">
            <button
              v-for="(s, i) in shownSuggestions"
              :key="i"
              type="button"
              class="list-group-item list-group-item-action text-break"
              @click="useSuggestion(s)"
            >
              {{ partText(s) }}
            </button>
          </div>
          <button
            v-if="!showAllSuggestions && matching.length > SUGGESTIONS_SHOWN"
            type="button"
            class="btn btn-link px-0"
            @click="showAllSuggestions = true"
          >
            More ({{ matching.length - SUGGESTIONS_SHOWN }})
          </button>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label" for="part-number">Part number <span class="text-secondary">(optional)</span></label>
        <input
          id="part-number"
          v-model="form.part_number"
          class="form-control"
          :class="{ 'is-invalid': fieldError('part_number') }"
          type="text"
          autocomplete="off"
          :maxlength="NUMBER_MAX"
        />
        <div class="form-text">What is on the part, the drawing or the quote. Leave empty if there is none.</div>
        <div v-if="fieldError('part_number')" class="invalid-feedback d-block">{{ fieldError("part_number") }}</div>
      </div>
      <fieldset v-if="hasNumber" class="mb-3">
        <legend class="form-label fs-6 mb-2">Where does the number come from?</legend>
        <div class="d-grid gap-2">
          <button
            v-for="choice in PART_KIND_CHOICES"
            :key="choice.value"
            type="button"
            class="btn text-start"
            :class="form.number_kind === choice.value ? 'btn-primary' : 'btn-outline-secondary'"
            :aria-pressed="form.number_kind === choice.value"
            @click="form.number_kind = choice.value"
          >
            {{ choice.label }}
          </button>
        </div>
        <div v-if="fieldError('number_kind')" class="invalid-feedback d-block">{{ fieldError("number_kind") }}</div>
      </fieldset>
      <div class="mb-3">
        <label class="form-label" for="part-maker">
          Maker<span v-if="!makerRequired" class="text-secondary"> (optional)</span>
        </label>
        <input
          id="part-maker"
          v-model="form.maker"
          class="form-control"
          :class="{ 'is-invalid': fieldError('maker') }"
          type="text"
          autocomplete="off"
          :maxlength="MAKER_MAX"
          placeholder="e.g. SKF"
        />
        <div v-if="fieldError('maker')" class="invalid-feedback d-block">{{ fieldError("maker") }}</div>
      </div>
      <div class="mb-3">
        <label class="form-label" for="part-quantity">Quantity</label>
        <div class="d-flex gap-2">
          <input
            id="part-quantity"
            v-model="form.quantity"
            class="form-control"
            :class="{ 'is-invalid': fieldError('quantity') }"
            type="text"
            inputmode="decimal"
            autocomplete="off"
          />
          <select v-model="form.qty_unit" class="form-select unit-select" :class="{ 'is-invalid': fieldError('qty_unit') }" aria-label="Unit">
            <option v-for="u in PART_UNITS" :key="u" :value="u">{{ u }}</option>
          </select>
        </div>
        <div v-if="fieldError('quantity')" class="invalid-feedback d-block">{{ fieldError("quantity") }}</div>
        <div v-if="fieldError('qty_unit')" class="invalid-feedback d-block">{{ fieldError("qty_unit") }}</div>
      </div>
      <div class="mb-3">
        <label class="form-label" for="part-node">Fitted to</label>
        <select id="part-node" v-model="form.node_id" class="form-select" :class="{ 'is-invalid': fieldError('node_id') }">
          <option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.label }}</option>
        </select>
        <div v-if="fieldError('node_id')" class="invalid-feedback d-block">{{ fieldError("node_id") }}</div>
      </div>
    </FormModal>
  </div>
</template>

<style scoped>
/* Columns read top to bottom, then the next column; a line never splits across two */
.part-columns {
  display: block;
  column-width: 22rem;
  column-gap: 0;
}
.part-columns .part-line {
  break-inside: avoid;
}
.unit-select {
  width: auto;
  flex: 0 0 6rem;
}
</style>
