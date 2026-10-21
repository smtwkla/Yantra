<script setup>
/**
 * Edit a ticket while open (docs/steps/S018-work-tickets/1-brief.md § 1 Edit): the component
 * (a part under the ticket's machine, or none), the symptom and the description. Only the
 * fields that changed are sent; each change becomes a timeline line, old → new.
 *
 * The components come from the machine's equipment detail (`children`, two levels), the
 * scrapped ones left out (BR3-11); the symptoms from GET /api/tickets/modes?ticket_id=. The
 * description is needed with no symptom or with Other — the API's rule, shown beside the field.
 */
import { computed, ref } from "vue";
import { apiGet, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";

const props = defineProps({
  ticket: { type: Object, required: true },
  modes: { type: Array, default: () => [] },
});
const emit = defineEmits(["saved"]);

const DESCRIPTION_MAX = 1000;
const SHOWN_FIELDS = ["component_id", "failure_mode_id", "description"];

const components = ref([]);
const loadError = ref("");

const { modal, form, saving, dirty, error, fieldError, openCreate, send } = useFormModal({
  path: null,
  blank: (seed) => ({ component_id: "", failure_mode_id: "", description: "", ...seed }),
  afterSave: (result) => emit("saved", result),
});

const topError = computed(() => (error.value && !SHOWN_FIELDS.includes(error.value.field) ? error.value.message : ""));

function flatten(children, depth = 0) {
  return children.flatMap((child) => (child.status === "scrapped" ? [] : [
    { id: child.id, label: `${"— ".repeat(depth)}${child.code} ${child.name}` },
    ...flatten(child.children ?? [], depth + 1),
  ]));
}

async function open() {
  const t = props.ticket;
  loadError.value = "";
  openCreate({
    component_id: t.component?.id ?? "", failure_mode_id: t.failure_mode?.id ?? "", description: t.description ?? "",
  });
  let parts = [];
  try {
    parts = flatten((await apiGet(`/api/equipment/${t.machine.id}`)).children ?? []);
  } catch (err) {
    loadError.value = `The machine's parts could not be loaded: ${err.message}`;
  }
  // The ticket's own part stays a choice even when it is not listed (scrapped since), so an
  // untouched field never clears it
  if (t.component && !parts.some((p) => p.id === t.component.id)) {
    parts.unshift({ id: t.component.id, label: `${t.component.code} ${t.component.name}` });
  }
  components.value = parts;
}

function save() {
  const t = props.ticket;
  const f = form.value;
  const body = {};
  const componentId = f.component_id ? Number(f.component_id) : null;
  const modeId = f.failure_mode_id ? Number(f.failure_mode_id) : null;
  const description = f.description.trim() || null;
  if (componentId !== (t.component?.id ?? null)) body.component_id = componentId;
  if (modeId !== (t.failure_mode?.id ?? null)) body.failure_mode_id = modeId;
  if (description !== (t.description ?? null)) body.description = description;
  if (!Object.keys(body).length) {
    modal.value.close();
    return;
  }
  return send(() => apiPut(`/api/tickets/${t.id}`, body));
}

defineExpose({ open });
</script>

<template>
  <FormModal ref="modal" title="Edit ticket" :saving="saving" :dirty="dirty" :error="topError || loadError" @save="save">
    <div class="mb-3">
      <label class="form-label" for="edit-component">Part</label>
      <select id="edit-component" v-model="form.component_id" class="form-select" :class="{ 'is-invalid': fieldError('component_id') }">
        <option value="">— The machine itself —</option>
        <option v-for="c in components" :key="c.id" :value="c.id">{{ c.label }}</option>
      </select>
      <div v-if="fieldError('component_id')" class="invalid-feedback d-block">{{ fieldError("component_id") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="edit-mode">Symptom</label>
      <select id="edit-mode" v-model="form.failure_mode_id" class="form-select" :class="{ 'is-invalid': fieldError('failure_mode_id') }">
        <option value="">— Not sure —</option>
        <option v-for="m in modes" :key="m.id" :value="m.id">{{ m.label }}</option>
      </select>
      <div v-if="fieldError('failure_mode_id')" class="invalid-feedback d-block">{{ fieldError("failure_mode_id") }}</div>
    </div>
    <div class="mb-3">
      <label class="form-label" for="edit-description">Description</label>
      <textarea
        id="edit-description"
        v-model="form.description"
        class="form-control"
        :class="{ 'is-invalid': fieldError('description') }"
        rows="3"
        :maxlength="DESCRIPTION_MAX"
      ></textarea>
      <div v-if="fieldError('description')" class="invalid-feedback d-block">{{ fieldError("description") }}</div>
    </div>
  </FormModal>
</template>
