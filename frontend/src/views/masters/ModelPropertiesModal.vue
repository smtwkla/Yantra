<script setup>
/**
 * The values of a model's properties (S043 § 7.3): one PropertyInput per active property of the
 * model's class. Opened from Masters › Models and from the equipment page's Properties card,
 * whose items all take these values.
 *
 * open(model) fetches the stored values first and opens the dialog with them as its seed, so an
 * untouched Cancel closes without the leave guard (BR2-03); a failed fetch rejects and the dialog
 * stays closed. The form is keyed "values.<property_id>", the `field` a refusal names, so the
 * message shows under its input (BR1-07); the request builds {values: {...}} from it.
 */
import { computed, ref } from "vue";
import { apiGet, apiPut } from "../../api";
import FormModal from "../../components/FormModal.vue";
import PropertyInput from "../../components/PropertyInput.vue";
import { useFormModal } from "../../composables/useFormModal";

const emit = defineEmits(["saved"]);

const items = ref([]);
const classCode = ref("");
const path = (modelId) => `/api/masters/equipment-models/${modelId}/properties`;
const key = (item) => `values.${item.property_id}`;

const { modal, form, editingId, editingLabel, saving, dirty, fieldError, modalError, openEdit, send } = useFormModal({
  path: "",
  blank: () => ({}),
  fromRecord: (record) => Object.fromEntries(record.items.map((item) => [key(item), item.value ?? ""])),
  label: (record) => record.label,
  afterSave: (result) => emit("saved", result),
});

const title = computed(() => `Properties of ${editingLabel.value}`);

// model: {id, label, class_code}
async function open(model) {
  const answer = await apiGet(path(model.id));
  items.value = answer.items;
  classCode.value = model.class_code;
  openEdit({ id: model.id, label: model.label, items: answer.items });
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
    <p v-if="items.length === 0" class="mb-0">The class {{ classCode }} has no properties yet. Add them in Masters › Classes.</p>
    <template v-else>
      <PropertyInput
        v-for="item in items"
        :key="item.property_id"
        v-model="form[key(item)]"
        :property="item"
        :error="fieldError(key(item))"
      />
    </template>
  </FormModal>
</template>
