<script setup>
/**
 * Add machine and Edit price on a contract (docs/steps/S081-contract-equipment/1-brief.md § 5.7): one FormModal
 * through useFormModal. Add machine: the picker, kept to the contract's site, and the price for a reader of
 * prices (the managers of the site); Edit price: the price alone. One machine per save (B14). The API answers
 * with the contract's detail, which goes to the page as it is (no second fetch).
 *
 * The parent keys this dialog by the contract's id, so the path below never names another contract.
 */
import { computed, ref } from "vue";
import EquipmentPicker from "../../components/EquipmentPicker.vue";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { lineBody } from "../../utils/contractLabels";

const props = defineProps({
  contract: { type: Object, required: true },
  canReadCost: { type: Boolean, default: false },
});
const emit = defineEmits(["saved"]);

const picked = ref(null); // the picker's list item: {id, code, name, full_path}
const pickerKey = ref(0); // a new picker (empty search) on every open

const { modal, form, editingId, editingLabel, saving, dirty, fieldError, modalError, openCreate, openEdit, save } =
  useFormModal({
    path: `/api/contracts/${props.contract.id}/equipment`,
    blank: () => ({ equipment_id: null, price: "" }),
    fromRecord: (line) => ({ equipment_id: line.equipment_id, price: line.price ?? "" }),
    toBody: (f) => lineBody(f, { creating: editingId.value === null, canReadCost: props.canReadCost }),
    afterSave: (detail) => emit("saved", detail),
    label: (line) => line.code,
  });

const creating = computed(() => editingId.value === null);
const title = computed(() => (creating.value ? "Add machine" : `Edit price — ${editingLabel.value}`));
const saveDisabledReason = computed(() => (creating.value && !form.value.equipment_id ? "Choose a machine" : ""));

function pick(id, item) {
  picked.value = item;
  form.value.equipment_id = id;
}

function changeMachine() {
  picked.value = null;
  form.value.equipment_id = null;
  pickerKey.value += 1;
}

function openAdd() {
  picked.value = null;
  pickerKey.value += 1;
  openCreate();
}

function openEditPrice(line) {
  picked.value = null;
  openEdit({ ...line, id: line.equipment_id });
}

defineExpose({ openAdd, openEditPrice });
</script>

<template>
  <FormModal
    ref="modal"
    :title="title"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    :save-label="creating ? 'Add machine' : 'Save price'"
    :save-disabled-reason="saveDisabledReason"
    @save="save"
  >
    <template v-if="creating">
      <div v-if="picked" class="mb-3" data-testid="picked-machine">
        <div class="form-label">Machine</div>
        <div class="d-flex align-items-start gap-2">
          <div class="flex-grow-1">
            <span class="fw-semibold">{{ picked.code }}</span> — {{ picked.name }}
            <div class="small text-secondary">{{ picked.full_path }}</div>
          </div>
          <button type="button" class="btn btn-sm btn-outline-secondary" @click="changeMachine">Change</button>
        </div>
      </div>
      <EquipmentPicker
        v-else
        :key="pickerKey"
        class="mb-3"
        :site-id="contract.site_id"
        :empty-text="`No machine of ${contract.site_code} matches.`"
        @pick="pick"
      />
      <div v-if="fieldError('equipment_id')" class="invalid-feedback d-block mb-3">{{ fieldError("equipment_id") }}</div>
    </template>
    <div v-if="canReadCost">
      <label class="form-label" for="line-price">Price (₹, before GST)</label>
      <input
        id="line-price"
        v-model="form.price"
        class="form-control"
        :class="{ 'is-invalid': fieldError('price') }"
        inputmode="decimal"
        autocomplete="off"
        :autofocus="!creating"
      />
      <div v-if="fieldError('price')" class="invalid-feedback d-block">{{ fieldError("price") }}</div>
      <div class="form-text">As in the quote, before GST. Only the managers of {{ contract.site_code }} see it.</div>
    </div>
  </FormModal>
</template>
