<script setup>
/**
 * Add properties to a class (S043 § 7.2, U6): tick boxes of the active properties not yet on the
 * class, a search box over their names, one POST with the ticked ids. Opens empty (nothing
 * ticked) from the property list the panel already holds. useFormModal with send(request), as
 * the Team dialog (BR1-07); its form has one key, property_ids, so a refusal shows under the list.
 */
import { computed, ref } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { typeSummary } from "../../utils/propertyFormat";

const props = defineProps({
  // {id, code}
  cls: { type: Object, required: true },
  // Every property, inactive ones included (the masters cache)
  properties: { type: Array, required: true },
  // The ids already on the class
  linkedIds: { type: Array, required: true },
});
const emit = defineEmits(["saved"]);

const search = ref("");

const { modal, form, saving, dirty, fieldError, modalError, openCreate, send } = useFormModal({
  path: "",
  blank: () => ({ property_ids: [] }),
  fromRecord: () => ({ property_ids: [] }),
  afterSave: (result) => emit("saved", result),
});

// A property on every class (S061) needs no link, so the picker leaves it out
const available = computed(() =>
  props.properties.filter((p) => p.active && !p.all_classes && !props.linkedIds.includes(p.id))
);
const shown = computed(() => {
  const needle = search.value.trim().toLowerCase();
  return available.value.filter((p) => p.name.toLowerCase().includes(needle));
});
const hasNoOptions = (p) => p.data_type === "choice" && !(p.options ?? []).some((o) => o.active);

function open() {
  search.value = "";
  openCreate();
}

function save() {
  return send(() => apiPost(`/api/masters/equipment-classes/${props.cls.id}/properties`, form.value));
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    :title="`Add properties to ${cls.code}`"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :close-only="available.length === 0"
    save-label="Add properties"
    :save-disabled-reason="form.property_ids.length === 0 ? 'Tick at least one property' : ''"
    @save="save"
  >
    <p v-if="available.length === 0" class="mb-0">Every property is on this class. Make a new one in Properties.</p>
    <template v-else>
      <!-- The search filters as the user types, so Enter (a phone's Search key) does nothing: it
           would submit the form with only the boxes ticked so far (CR1-01) -->
      <input
        v-model="search"
        class="form-control mb-3"
        type="search"
        placeholder="Search by name"
        aria-label="Search properties"
        autocomplete="off"
        @keydown.enter.prevent
      />
      <div v-if="shown.length === 0" class="text-secondary">No property matches the search.</div>
      <div v-for="p in shown" :key="p.id" class="form-check">
        <input
          :id="`add-property-${p.id}`"
          v-model="form.property_ids"
          class="form-check-input"
          type="checkbox"
          :value="p.id"
          :disabled="hasNoOptions(p)"
        />
        <label class="form-check-label" :for="`add-property-${p.id}`">
          {{ p.name }}
          <span class="text-secondary small">{{ typeSummary(p) }}</span>
          <span v-if="hasNoOptions(p)" class="text-secondary small">(no options yet)</span>
        </label>
      </div>
      <div v-if="fieldError('property_ids')" class="invalid-feedback d-block">{{ fieldError("property_ids") }}</div>
    </template>
  </FormModal>
</template>
