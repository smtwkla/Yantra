<script setup>
/**
 * *Use a meter from above* (docs/steps/S104-pm-templates-one-path/1-brief.md § 10 A1.6.7): a part (a component unit
 * or a component) with no meter of its own picks the meter of its parent or grandparent it runs with. Readings stay
 * on that node; the part's Meters card shows them, and a PM template finds the meter by its type (A1.6.2).
 *
 * Call contract (repo self-check (13)): `blank(seed)` returns `{ choice: seed ?? "" }`, a choice's key
 * "<equipment id>-<meter type id>"; `open(choices)` takes the choices the card loaded
 * (`GET /api/equipment/<id>/meter-links/choices`, the nearest node first) and opens the dialog with the one choice
 * picked when there is only one. The save posts `{meter_type_id, source_equipment_id}`; FormModal's `closed` event
 * hands the node's meters to the card after the fade (the S077 rule) as `saved(meters)`. Refusals of the two fields
 * show beside the list; any other at the top.
 */
import { computed, ref } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { linkChoiceText } from "../../utils/meterLabels";

const props = defineProps({
  node: { type: Object, required: true },
});
const emit = defineEmits(["saved"]);

const choices = ref([]);
let saved = null;

const keyOf = (choice) => `${choice.equipment.id}-${choice.meter_type.id}`;

const { modal, form, saving, dirty, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: (seed) => ({ choice: seed ?? "" }),
  afterSave: (meters) => {
    saved = meters;
  },
  label: () => props.node.code,
});

const picked = computed(() => choices.value.find((c) => keyOf(c) === form.value.choice) ?? null);
const listError = computed(() => fieldError("meter_type_id") || fieldError("source_equipment_id"));
const saveDisabledReason = computed(() => {
  if (!choices.value.length) return "No meter to use";
  return picked.value ? "" : "Pick a meter";
});

function open(loaded) {
  choices.value = loaded;
  openCreate(loaded.length === 1 ? keyOf(loaded[0]) : undefined);
}

function save() {
  const body = { meter_type_id: picked.value.meter_type.id, source_equipment_id: picked.value.equipment.id };
  return send(() => apiPost(`/api/equipment/${props.node.id}/meter-links`, body));
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
    title="Use a meter from above"
    :saving="saving"
    :dirty="dirty"
    :error="listError ? '' : modalError"
    :save-disabled-reason="saveDisabledReason"
    save-label="Use this meter"
    @save="save"
    @closed="onClosed"
  >
    <p class="small">
      <span class="fw-semibold">{{ node.code }} — {{ node.name }}.</span>
      Pick the meter this part runs with. Readings are logged on that node; this part shows them.
    </p>
    <p v-if="choices.length === 0" class="text-secondary" data-testid="meter-link-none">
      The nodes above have no meter this part can use. Add the meter on the machine first.
    </p>
    <fieldset v-else>
      <legend class="visually-hidden">Meter to use</legend>
      <div
        v-for="choice in choices"
        :key="keyOf(choice)"
        class="form-check link-choice d-flex align-items-center gap-2 border rounded px-3 mb-2"
        data-testid="meter-link-choice"
      >
        <input
          :id="`meter-link-${keyOf(choice)}`"
          v-model="form.choice"
          class="form-check-input mt-0"
          type="radio"
          name="meter-link"
          :value="keyOf(choice)"
          :class="{ 'is-invalid': listError }"
        />
        <label class="form-check-label flex-grow-1 py-2" :for="`meter-link-${keyOf(choice)}`">
          {{ linkChoiceText(choice) }}
        </label>
      </div>
      <div v-if="listError" class="invalid-feedback d-block">{{ listError }}</div>
    </fieldset>
  </FormModal>
</template>

<style scoped>
/* A glove on a floor screen (U3): each choice at least 44 px high */
.link-choice {
  min-height: 44px;
}
</style>
