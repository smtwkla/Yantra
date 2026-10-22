<script setup>
/**
 * Labour on a ticket (docs/steps/S018-work-tickets/1-brief.md § 1 Labour): rows of person,
 * trade worked, date and time spent — the man-hours per discipline of ISO 14224 (Table 8).
 *
 * A new row defaults to the user's own person when he may be named at the ticket's site (his
 * person is in the picker's list, the server's own check, BR4-03), today, and that person's
 * only trade. The trade is required when the person holds one; any active trade may be
 * chosen, the person's own first. Time is hours and minutes; zero is refused here. Remove
 * asks inline first (BR3-02). Rows are added, changed and removed by ticket:work holders
 * until the ticket closes; the API checks everything again.
 */
import { computed, ref } from "vue";
import { apiDelete, apiPost, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { formatDateTime } from "../../utils/datetime";
import { ensureTrades, trades } from "../../stores/masters";
import { minutesText, toLocalDateValue } from "../../utils/ticketLabels";
import PersonPicker from "./PersonPicker.vue";

const props = defineProps({
  ticket: { type: Object, required: true },
  people: { type: Array, default: () => [] },
  ownPersonId: { type: Number, default: null },
  canEdit: { type: Boolean, default: false },
});
const emit = defineEmits(["saved"]);

const MINUTES_PER_DAY = 24 * 60;
const SHOWN_FIELDS = ["person_id", "trade_id", "work_date", "minutes"];

const confirmingRemoveId = ref(null);
const removing = ref(false);
const removeError = ref("");
const tradesError = ref("");

const { modal, form, editingId, saving, dirty, error, fieldError, openCreate, openEdit, send } = useFormModal({
  path: null,
  blank: (seed) => ({ person_id: null, trade_id: "", work_date: "", hours: "", minutes: "", ...seed }),
  fromRecord: (row) => ({
    person_id: row.person.id, trade_id: row.trade?.id ?? "", work_date: row.work_date,
    hours: Math.floor(row.minutes / 60), minutes: row.minutes % 60,
  }),
  afterSave: (result) => emit("saved", result),
});

const person = computed(() => props.people.find((p) => p.id === form.value.person_id) ?? null);
const personTrades = computed(() => person.value?.trades ?? []);
const otherTrades = computed(() => {
  const own = new Set(personTrades.value.map((t) => t.id));
  return (trades.value ?? []).filter((t) => t.active && !own.has(t.id));
});
const totalMinutes = computed(() => (Number(form.value.hours) || 0) * 60 + (Number(form.value.minutes) || 0));
const assigneeIds = computed(() => props.ticket.assignees.map((a) => a.id));
const topError = computed(() => (error.value && !SHOWN_FIELDS.includes(error.value.field) ? error.value.message : ""));
const totalMinutesBooked = computed(() => props.ticket.labour.reduce((sum, row) => sum + row.minutes, 0));

function onlyTradeOf(personId) {
  const held = props.people.find((p) => p.id === personId)?.trades ?? [];
  return held.length === 1 ? held[0].id : "";
}

function pickPerson(personId) {
  form.value.person_id = personId;
  form.value.trade_id = onlyTradeOf(personId);
}

async function loadTrades() {
  tradesError.value = "";
  try {
    await ensureTrades();
  } catch (err) {
    tradesError.value = `The trade list could not be loaded: ${err.message}`;
  }
}

function openAdd() {
  const own = props.people.some((p) => p.id === props.ownPersonId) ? props.ownPersonId : null;
  openCreate({ person_id: own, trade_id: onlyTradeOf(own), work_date: toLocalDateValue(new Date()), hours: "", minutes: "" });
  loadTrades();
}

function openChange(row) {
  openEdit(row);
  loadTrades();
}

function save() {
  const f = form.value;
  if (!f.person_id) {
    error.value = { field: "person_id", message: "Who did the work? Pick a name" };
    return;
  }
  if (personTrades.value.length && !f.trade_id) {
    error.value = { field: "trade_id", message: "Choose the trade worked" };
    return;
  }
  if (totalMinutes.value < 1 || totalMinutes.value > MINUTES_PER_DAY) {
    error.value = { field: "minutes", message: "Time spent must be between 1 minute and 24 hours" };
    return;
  }
  const body = { person_id: f.person_id, trade_id: f.trade_id ? Number(f.trade_id) : null, work_date: f.work_date,
    minutes: totalMinutes.value };
  const base = `/api/tickets/${props.ticket.id}/labour`;
  return send(() => (editingId.value === null ? apiPost(base, body) : apiPut(`${base}/${editingId.value}`, body)));
}

async function remove(row) {
  removing.value = true;
  removeError.value = "";
  try {
    const result = await apiDelete(`/api/tickets/${props.ticket.id}/labour/${row.id}`);
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
      <span>Labour<span v-if="ticket.labour.length" class="text-secondary"> · {{ minutesText(totalMinutesBooked, { days: false }) }}</span></span>
      <button v-if="canEdit" class="btn btn-outline-primary" @click="openAdd">
        <i class="fa-solid fa-plus me-1"></i>Add labour
      </button>
    </div>
    <div v-if="removeError" class="alert alert-danger py-2 m-2">{{ removeError }}</div>
    <div v-if="!ticket.labour.length" class="card-body text-secondary">No labour yet.</div>
    <ul v-else class="list-group list-group-flush">
      <li v-for="row in ticket.labour" :key="row.id" class="list-group-item">
        <div class="d-flex flex-wrap align-items-center gap-2">
          <div class="flex-grow-1 text-break">
            <span class="fw-semibold">{{ row.person.name }}</span>
            <span v-if="row.trade" class="text-secondary"> · {{ row.trade.name }}</span>
            <div class="small text-secondary">{{ formatDateTime(row.work_date) }} · {{ minutesText(row.minutes, { days: false }) }}</div>
          </div>
          <template v-if="canEdit && confirmingRemoveId !== row.id">
            <button class="btn btn-outline-primary" title="Change" @click="openChange(row)">
              <i class="fa-solid fa-pen"></i>
            </button>
            <button class="btn btn-outline-danger" title="Remove" @click="confirmingRemoveId = row.id">
              <i class="fa-solid fa-trash"></i>
            </button>
          </template>
        </div>
        <div v-if="canEdit && confirmingRemoveId === row.id" class="d-flex flex-wrap align-items-center justify-content-end gap-3 mt-2">
          <span>Remove?</span>
          <button class="btn btn-danger" :disabled="removing" @click="remove(row)">Yes</button>
          <button class="btn btn-outline-secondary" @click="confirmingRemoveId = null">No</button>
        </div>
      </li>
    </ul>

    <FormModal
      ref="modal"
      :title="editingId === null ? 'Add labour' : 'Change labour'"
      :saving="saving"
      :dirty="dirty"
      :error="topError || tradesError"
      @save="save"
    >
      <div class="mb-3">
        <label class="form-label" for="labour-person-filter">Who worked?</label>
        <PersonPicker
          :model-value="form.person_id"
          :people="people"
          :own-person-id="ownPersonId"
          :assignee-ids="assigneeIds"
          :invalid="Boolean(fieldError('person_id'))"
          id-prefix="labour-person"
          @update:model-value="pickPerson"
        />
        <div v-if="fieldError('person_id')" class="invalid-feedback d-block">{{ fieldError("person_id") }}</div>
      </div>
      <div class="mb-3">
        <label class="form-label" for="labour-trade">
          Trade worked<span v-if="!personTrades.length" class="text-secondary"> (optional)</span>
        </label>
        <select id="labour-trade" v-model="form.trade_id" class="form-select" :class="{ 'is-invalid': fieldError('trade_id') }">
          <option value="">—</option>
          <optgroup v-if="personTrades.length" label="Their trades">
            <option v-for="t in personTrades" :key="t.id" :value="t.id">{{ t.name }}</option>
          </optgroup>
          <optgroup v-if="otherTrades.length" label="Other trades">
            <option v-for="t in otherTrades" :key="t.id" :value="t.id">{{ t.name }}</option>
          </optgroup>
        </select>
        <div v-if="fieldError('trade_id')" class="invalid-feedback d-block">{{ fieldError("trade_id") }}</div>
      </div>
      <div class="mb-3">
        <label class="form-label" for="labour-date">Date</label>
        <input id="labour-date" v-model="form.work_date" class="form-control" :class="{ 'is-invalid': fieldError('work_date') }" type="date" />
        <div v-if="fieldError('work_date')" class="invalid-feedback d-block">{{ fieldError("work_date") }}</div>
      </div>
      <div class="mb-3">
        <label class="form-label" for="labour-hours">Time spent</label>
        <div class="d-flex gap-2 align-items-center">
          <input id="labour-hours" v-model="form.hours" class="form-control" :class="{ 'is-invalid': fieldError('minutes') }" type="number" min="0" max="24" inputmode="numeric" aria-label="Hours" />
          <span>h</span>
          <input v-model="form.minutes" class="form-control" :class="{ 'is-invalid': fieldError('minutes') }" type="number" min="0" max="59" inputmode="numeric" aria-label="Minutes" />
          <span>min</span>
        </div>
        <div v-if="fieldError('minutes')" class="invalid-feedback d-block">{{ fieldError("minutes") }}</div>
      </div>
    </FormModal>
  </div>
</template>
