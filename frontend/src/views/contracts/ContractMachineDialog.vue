<script setup>
/**
 * Add machine and Edit price on a contract (docs/steps/S081-contract-equipment/1-brief.md § 5.7): one FormModal
 * through useFormModal. Add machine: the Site first (the adder's sites; S087 A1), the picker over that site's
 * machines inside the adder's units, and the price for a reader of prices (the managers); Edit price: the
 * price alone. One machine per save (B14). The API answers
 * with the contract's detail, which goes to the page as it is (no second fetch).
 *
 * The parent keys this dialog by the contract's id, so the path below never names another contract.
 */
import { computed, ref } from "vue";
import EquipmentPicker from "../../components/EquipmentPicker.vue";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ensureMyUnits, myUnits, unitSites } from "../../stores/equipment";
import { ensureSites, ensureUnits, sites, units } from "../../stores/masters";
import { lineBody } from "../../utils/contractLabels";

const props = defineProps({
  contract: { type: Object, required: true },
  canReadCost: { type: Boolean, default: false },
});
const emit = defineEmits(["saved"]);

const siteId = ref(null); // the site the search is limited to; a filter of the screen, not sent with the line
const siteError = ref("");
// Empty until the lists are loaded (openAdd loads them before the dialog opens)
const siteChoices = computed(() => (myUnits.value ? unitSites(units.value, sites.value, myUnits.value) : []));
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

async function openAdd() {
  picked.value = null;
  pickerKey.value += 1;
  siteError.value = "";
  try {
    await Promise.all([ensureSites(), ensureUnits(), ensureMyUnits()]);
  } catch (err) {
    siteError.value = err.message;
  }
  // One site: it is chosen already (S087 A1)
  siteId.value = siteChoices.value.length === 1 ? siteChoices.value[0].id : null;
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
      <div class="mb-3">
        <label class="form-label" for="line-site">Site</label>
        <select id="line-site" v-model="siteId" class="form-select form-select-lg" @change="changeMachine">
          <option :value="null" disabled>Choose a site</option>
          <option v-for="s in siteChoices" :key="s.id" :value="s.id">{{ s.code }}</option>
        </select>
        <div v-if="siteError" class="alert alert-danger py-2 mt-2 mb-0">{{ siteError }}</div>
        <div v-else-if="siteChoices.length === 0" class="form-text">You have no unit at any site.</div>
        <div v-else-if="siteId === null" class="form-text" data-testid="site-hint">Choose a site first.</div>
      </div>
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
        :site-id="siteId"
        :disabled="siteId === null"
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
      <div class="form-text">As in the quote, before GST. Only the managers see it.</div>
    </div>
  </FormModal>
</template>
