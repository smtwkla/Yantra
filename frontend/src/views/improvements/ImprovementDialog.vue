<script setup>
/**
 * Start improvement / Edit improvement (docs/steps/S068-improvement-screens/1-brief.md § 5.2):
 * one dialog on one useFormModal. Start is seeded from the ticket (title, problem) and, when the
 * user may lead, with the user as lead. The API judges every rule; a refusal for a field the
 * form does not render (ticket_id) shows at the top.
 */
import { computed, ref } from "vue";
import { apiGet } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { userPersonId } from "../../stores/auth";
import { defaultProblem, defaultTitle, PROBLEM_MAX, TITLE_MAX } from "../../utils/improvementLabels";

const emit = defineEmits(["saved"]);

const leads = ref([]); // [{id, name}] by name
const leadsError = ref("");
const loadingLeads = ref(false); // the Start button shows it until the dialog opens
const currentLead = ref(null); // an edit: {id, name}, kept in the select even when not a lead now

const { modal, form, editingId, saving, dirty, error, fieldError, openCreate, openEdit, save } = useFormModal({
  path: "/api/improvements",
  blank: (seed) => ({
    ticket_id: seed?.ticket.id ?? null,
    title: seed ? defaultTitle(seed.ticket) : "",
    problem: seed ? defaultProblem(seed.ticket) : "",
    lead_id: seed?.leadId ?? "",
  }),
  fromRecord: (improvement) => ({ title: improvement.title, problem: improvement.problem, lead_id: improvement.lead.id }),
  toBody: (f) => ({ ...f, lead_id: f.lead_id === "" ? null : f.lead_id }),
  label: (improvement) => improvement.serial,
  afterSave: (result) => emit("saved", result),
});

const isEdit = computed(() => editingId.value !== null);
// ticket_id is in the form but has no field of its own, so its refusals (not back in service, already
// analysed, ...) show at the top with every other refusal that no field shows
const RENDERED_FIELDS = ["title", "problem", "lead_id"];
const refusalAtTop = computed(() => (error.value && !RENDERED_FIELDS.includes(error.value.field) ? error.value.message : ""));
const topError = computed(() => refusalAtTop.value || leadsError.value);
// The current lead who is no lead now stays in the list, last, so a change of text keeps them.
// While the list failed to load nobody knows whether they are a lead, so they show by name only.
const leadChoices = computed(() => {
  const choices = leads.value.map((p) => ({ id: p.id, name: p.name }));
  const lead = currentLead.value;
  if (isEdit.value && lead && !choices.some((p) => p.id === lead.id)) {
    choices.push({ id: lead.id, name: leadsError.value ? lead.name : `${lead.name} (not a lead now)` });
  }
  return choices;
});

async function loadLeads(query) {
  leadsError.value = "";
  try {
    leads.value = (await apiGet(`/api/improvements/leads?${query}`)).items;
  } catch (err) {
    leads.value = [];
    leadsError.value = `The list of leads could not be loaded: ${err.message}`;
  }
}

async function openStart(ticket) {
  currentLead.value = null;
  loadingLeads.value = true;
  try {
    await loadLeads(`ticket_id=${ticket.id}`);
  } finally {
    loadingLeads.value = false;
  }
  const own = leads.value.find((p) => p.id === userPersonId.value);
  openCreate({ ticket, leadId: own ? own.id : "" });
}

async function openChange(improvement) {
  currentLead.value = improvement.lead;
  await loadLeads(`improvement_id=${improvement.id}`);
  openEdit(improvement);
}

defineExpose({ openStart, openChange, loadingLeads });
</script>

<template>
  <FormModal
    ref="modal"
    :title="isEdit ? 'Edit improvement' : 'Start improvement'"
    :saving="saving"
    :dirty="dirty"
    :error="topError"
    :save-label="isEdit ? 'Save improvement' : 'Start improvement'"
    @save="save"
  >
    <div class="mb-3">
      <label class="form-label" for="improvement-title">Title</label>
      <input
        id="improvement-title"
        v-model="form.title"
        class="form-control"
        :class="{ 'is-invalid': fieldError('title') }"
        type="text"
        :maxlength="TITLE_MAX"
        aria-describedby="improvement-title-help"
      />
      <div v-if="fieldError('title')" class="invalid-feedback d-block">{{ fieldError("title") }}</div>
      <div id="improvement-title-help" class="form-text">The machine and what went wrong, in one line</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="improvement-problem">Problem</label>
      <textarea
        id="improvement-problem"
        v-model="form.problem"
        class="form-control"
        :class="{ 'is-invalid': fieldError('problem') }"
        rows="5"
        :maxlength="PROBLEM_MAX"
        aria-describedby="improvement-problem-help"
      ></textarea>
      <div v-if="fieldError('problem')" class="invalid-feedback d-block">{{ fieldError("problem") }}</div>
      <div id="improvement-problem-help" class="form-text">What happened, as you saw it. The cause comes later.</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="improvement-lead">Lead</label>
      <select id="improvement-lead" v-model="form.lead_id" class="form-select" :class="{ 'is-invalid': fieldError('lead_id') }">
        <option value="">Choose a lead</option>
        <option v-for="p in leadChoices" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <div v-if="fieldError('lead_id')" class="invalid-feedback d-block">{{ fieldError("lead_id") }}</div>
    </div>
  </FormModal>
</template>
