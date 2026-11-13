<script setup>
/**
 * *Attach PM template* (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.10): a select of the active templates,
 * each with its trigger in words; once one is picked, the meters it would use on this machine (as the plan page
 * shows them), or why it does not apply here. A template that does not apply may be attached (D13): it makes no job
 * until the meter is added. One tap after the pick. Refusals beside the select.
 *
 * Call contract (repo self-check (13)): `blank()` takes no seed; `open()` loads the active templates and opens the
 * dialog blank. The save posts `{equipment_id, template_id}`; FormModal's `closed` event hands the new plan to the
 * card after the fade (the S077 rule) as `saved(plan)`. The preview comes from the server
 * (`GET /api/pm/plans/attach-preview`), so the resolution rule has one home (§ 9 item 3).
 */
import { computed, ref, watch } from "vue";
import { apiGet, apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { meterUseText } from "../../utils/pmLabels";

const props = defineProps({
  node: { type: Object, required: true },
});
const emit = defineEmits(["saved"]);

const templates = ref([]);
const loadError = ref("");
const preview = ref(null); // {meters, applies, missing} of the picked template
const previewError = ref("");
let saved = null;
let previewSeq = 0;

const toBody = (form) => ({ equipment_id: props.node.id, template_id: form.template_id || null });

const { modal, form, saving, dirty, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: () => ({ template_id: "" }),
  toBody,
  afterSave: (plan) => {
    saved = plan;
  },
  label: () => props.node.code,
});

const chosen = computed(() => templates.value.find((t) => t.id === Number(form.value.template_id)) ?? null);

watch(() => form.value.template_id, async (id) => {
  const seq = ++previewSeq;
  preview.value = null;
  previewError.value = "";
  if (!id) return;
  try {
    const answer = await apiGet(`/api/pm/plans/attach-preview?equipment_id=${props.node.id}&template_id=${id}`);
    if (seq === previewSeq) preview.value = answer;
  } catch (err) {
    if (seq === previewSeq) previewError.value = err.message;
  }
});

async function open() {
  loadError.value = "";
  preview.value = null;
  openCreate();
  try {
    templates.value = (await apiGet("/api/pm/templates")).items;
  } catch (err) {
    loadError.value = err.message;
  }
}

function save() {
  return send(() => apiPost("/api/pm/plans", toBody(form.value)));
}

function onClosed() {
  if (saved) emit("saved", saved);
  saved = null;
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    title="Attach PM template"
    :saving="saving"
    :dirty="dirty"
    :error="modalError || loadError"
    save-label="Attach template"
    @save="save"
    @closed="onClosed"
  >
    <p class="small text-secondary">{{ node.code }} — {{ node.name }}</p>
    <div class="mb-3">
      <label class="form-label" for="pm-attach-template">PM template</label>
      <select id="pm-attach-template" v-model="form.template_id" class="form-select" :class="{ 'is-invalid': fieldError('template_id') }">
        <option value="">Choose a template…</option>
        <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }} — {{ t.trigger_text }}</option>
      </select>
      <div v-if="templates.length === 0 && !loadError" class="form-text">
        No active PM templates. Add one in Masters › PM templates.
      </div>
      <div v-if="fieldError('template_id')" class="invalid-feedback d-block">{{ fieldError("template_id") }}</div>
    </div>
    <div v-if="chosen" class="small" data-testid="pm-attach-preview">
      <div v-if="previewError" class="text-danger">{{ previewError }}</div>
      <template v-else-if="preview">
        <div v-if="!preview.applies" class="alert alert-warning py-2 mb-0">
          Does not apply here: {{ preview.missing }}. You can attach it; it makes no job until the meter is added.
        </div>
        <template v-else>
          <div class="text-secondary mb-1">{{ chosen.trigger_text }} · {{ chosen.item_count }} items</div>
          <div v-if="preview.meters.length === 0">Uses no meter.</div>
          <div v-for="m in preview.meters" :key="m.meter_type.id">Uses {{ meterUseText(m) }}</div>
        </template>
      </template>
      <div v-else class="text-secondary">Loading…</div>
    </div>
  </FormModal>
</template>
