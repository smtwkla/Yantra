<script setup>
/**
 * This machine's own property values (S044 § 1.3): one PropertyInput per active property of the
 * item's class. Opened from the equipment page's Properties card. Titled "This machine's values —
 * <code>" so it is not taken for the model's dialog, which changes every machine of the model.
 *
 * Each input starts at the item's own value, or empty; under it the model's value ("Model: 7.5
 * kW", "Model: no value"; nothing on an item without a model). Typing sets the own value,
 * emptying clears it, and the row falls back to the model's. Save sends every row, as the model
 * dialog does; the backend keeps only the real changes.
 *
 * open(node) fetches the rows first and opens the dialog with them as its seed; a failed fetch
 * rejects and the dialog stays closed (the card shows the message). The form is keyed
 * "values.<property_id>", the `field` a refusal names, so the message shows under its input.
 */
import { computed, ref } from "vue";
import { apiGet, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import PropertyInput from "../../components/PropertyInput.vue";
import { useFormModal } from "../../composables/useFormModal";

const emit = defineEmits(["saved"]);

const items = ref([]);
const path = (nodeId) => `/api/equipment/${nodeId}/properties`;
const key = (item) => `values.${item.property_id}`;

const { modal, form, editingId, editingLabel, saving, dirty, fieldError, modalError, openEdit, send } = useFormModal({
  path: "",
  blank: () => ({}),
  fromRecord: (record) => Object.fromEntries(record.items.map((item) => [key(item), item.value ?? ""])),
  afterSave: (result) => emit("saved", result),
});

const title = computed(() => `This machine's values — ${editingLabel.value}`);

function modelHint(item) {
  if (!item.has_model) return "";
  return `Model: ${item.model_display ?? "no value"}`;
}

// node: {id, code}
async function open(node) {
  const answer = await apiGet(path(node.id));
  items.value = answer.items;
  openEdit({ id: node.id, code: node.code, items: answer.items });
}

function save() {
  const values = Object.fromEntries(items.value.map((item) => [String(item.property_id), form.value[key(item)]]));
  return send(() => apiPut(path(editingId.value), { values }));
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    :title="title"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :close-only="items.length === 0"
    save-label="Save values"
    @save="save"
  >
    <p v-if="items.length === 0" class="mb-0">The class has no properties now. Reload the page.</p>
    <template v-else>
      <PropertyInput
        v-for="item in items"
        :key="item.property_id"
        v-model="form[key(item)]"
        :property="item"
        :error="fieldError(key(item))"
        :hint="modelHint(item)"
      />
    </template>
  </FormModal>
</template>
