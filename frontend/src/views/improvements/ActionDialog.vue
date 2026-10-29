<script setup>
/**
 * Add countermeasure / Change countermeasure (docs/steps/S071-countermeasure-screens/1-brief.md
 * § 5.3): one dialog on one useFormModal. The kind's plain sentence shows under the select; the
 * owners are the people of the improvement's site (GET /api/improvements/owners); the due date
 * starts two weeks ahead. The API judges every rule; the 30-countermeasures refusal has no
 * field and shows at the top.
 */
import { computed, ref } from "vue";
import { apiGet, apiPost, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ACTION_KINDS, ACTION_TEXT_MAX, defaultDueDate } from "../../utils/improvementLabels";

const props = defineProps({
  improvement: { type: Object, required: true },
});
const emit = defineEmits(["saved"]);

const owners = ref([]); // [{id, name}] of the improvement's site
const loadError = ref("");
const openedOwner = ref(null); // the owner the change opened with: {id, name, left}; "left" comes from the detail, not from the list
let loadSeq = 0;

const { modal, form, editingId, saving, dirty, fieldError, modalError, openCreate, openEdit, send } = useFormModal({
  path: null,
  // useFormModal calls blank() with no seed at set-up (self-check 13): defaultDueDate(undefined) is ""
  blank: (seed = {}) => ({ kind: "", text: "", owner_id: "", due_date: defaultDueDate(seed.today) }),
  fromRecord: (action) => ({ kind: action.kind, text: action.text, owner_id: action.owner.id, due_date: action.due_date }),
  afterSave: (result) => emit("saved", result),
});

const isEdit = computed(() => editingId.value !== null);
const kindSentence = computed(() => ACTION_KINDS.find((k) => k.key === form.value.kind)?.sentence ?? "");
// An owner who has left the site stays chosen on a change, so an edit of the text alone keeps them
const ownerChoices = computed(() => {
  const choices = owners.value.map((o) => ({ id: o.id, name: o.name }));
  const kept = openedOwner.value;
  if (isEdit.value && kept && !choices.some((o) => o.id === kept.id)) choices.push({ id: kept.id, name: kept.left ? `${kept.name} (not at this site now)` : kept.name });
  return choices;
});
const minDate = computed(() => (props.improvement.problem_at ?? "").slice(0, 10));

async function loadOwners() {
  const seq = ++loadSeq;
  loadError.value = "";
  owners.value = [];
  try {
    const result = await apiGet(`/api/improvements/owners?improvement_id=${props.improvement.id}`);
    if (seq === loadSeq) owners.value = result.items;
  } catch (err) {
    if (seq === loadSeq) loadError.value = `The people could not be loaded: ${err.message}`;
  }
}

function openAdd() {
  openedOwner.value = null;
  openCreate({ today: new Date() });
  loadOwners();
}

function openChange(action) {
  openedOwner.value = { id: action.owner.id, name: action.owner.name, left: !action.owner.active || !action.owner.may_own };
  openEdit(action);
  loadOwners();
}

function save() {
  const f = form.value;
  const base = `/api/improvements/${props.improvement.id}/actions`;
  const body = { kind: f.kind, text: f.text, owner_id: f.owner_id ? Number(f.owner_id) : null, due_date: f.due_date };
  if (isEdit.value) return send(() => apiPut(`${base}/${editingId.value}`, body));
  return send(() => apiPost(base, body));
}

defineExpose({ openAdd, openChange });
</script>

<template>
  <FormModal
    ref="modal"
    :title="isEdit ? 'Change countermeasure' : 'Add countermeasure'"
    :saving="saving"
    :dirty="dirty"
    :error="modalError || loadError"
    :save-label="isEdit ? 'Save countermeasure' : 'Add countermeasure'"
    @save="save"
  >
    <div class="mb-3">
      <label class="form-label" for="action-kind">Kind</label>
      <select id="action-kind" v-model="form.kind" class="form-select" :class="{ 'is-invalid': fieldError('kind') }" autofocus>
        <option value="">Choose the kind</option>
        <option v-for="k in ACTION_KINDS" :key="k.key" :value="k.key">{{ k.label }}</option>
      </select>
      <div v-if="fieldError('kind')" class="invalid-feedback d-block">{{ fieldError("kind") }}</div>
      <div v-if="kindSentence" class="form-text" data-testid="kind-sentence">{{ kindSentence }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="action-text">What will be done</label>
      <textarea
        id="action-text"
        v-model="form.text"
        class="form-control"
        :class="{ 'is-invalid': fieldError('text') }"
        rows="3"
        :maxlength="ACTION_TEXT_MAX"
      ></textarea>
      <div v-if="fieldError('text')" class="invalid-feedback d-block">{{ fieldError("text") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="action-owner">Owner</label>
      <select id="action-owner" v-model="form.owner_id" class="form-select" :class="{ 'is-invalid': fieldError('owner_id') }">
        <option value="">Choose the owner</option>
        <option v-for="o in ownerChoices" :key="o.id" :value="o.id">{{ o.name }}</option>
      </select>
      <div v-if="fieldError('owner_id')" class="invalid-feedback d-block">{{ fieldError("owner_id") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="action-due">Due date</label>
      <input
        id="action-due"
        v-model="form.due_date"
        class="form-control"
        :class="{ 'is-invalid': fieldError('due_date') }"
        type="date"
        :min="minDate || undefined"
      />
      <div v-if="fieldError('due_date')" class="invalid-feedback d-block">{{ fieldError("due_date") }}</div>
      <div class="form-text">By when it should be done</div>
    </div>
  </FormModal>
</template>
