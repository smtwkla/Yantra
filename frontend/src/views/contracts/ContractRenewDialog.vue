<script setup>
/**
 * Renew contract (docs/steps/S085-contract-renewal/1-brief.md § 5.7; R02.4): the contract dialog's fields, filled
 * from this contract, the dates the day after it ends for the same length (the API's ``renewal``), the cost note
 * empty. The notice says which machines are copied and which are not; prices start empty and documents stay here.
 * Saving posts to the renew route, which makes the new contract; once the dialog has faded out, ``renewed`` hands
 * its detail to the page, which opens it (FormModal's ``closed``, the S077 pattern), so the route never changes
 * under an open backdrop.
 *
 * The parent shows this dialog only when ``can_renew`` and keys it by the contract's id, so the path below never
 * names another contract.
 */
import { computed, ref } from "vue";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ensureVendors, vendors } from "../../stores/masters";
import { EMPTY_CONTRACT_FORM, contractBody, renewalForm, renewalNotice } from "../../utils/contractLabels";
import ContractFields from "./ContractFields.vue";

const props = defineProps({
  contract: { type: Object, required: true },
});
const emit = defineEmits(["renewed"]);

const flags = computed(() => ({
  can_read_callout: props.contract.can_read_callout,
  can_read_cost: props.contract.can_read_cost,
}));

// useFormModal calls blank() once with no seed at set-up; the page opens the dialog with the contract as the seed
const blank = (seed) => (seed ? renewalForm(seed) : { ...EMPTY_CONTRACT_FORM, contract_type: "amc" });

const renewedDetail = ref(null); // the new contract, handed to the page once the dialog has faded out

const { modal, form, saving, dirty, fieldError, modalError, openCreate, save } = useFormModal({
  path: `/api/contracts/${props.contract.id}/renew`,
  blank,
  fromRecord: blank,
  toBody: (f) => contractBody(f, flags.value),
  afterSave: (detail) => {
    renewedDetail.value = detail;
  },
  label: (c) => c.title,
});

const storedVendor = computed(() => ({
  id: props.contract.vendor_id,
  name: props.contract.vendor_name,
  active: Boolean(props.contract.vendor_active),
}));
const loadError = ref("");
const topError = computed(() => modalError.value || loadError.value);
const notice = computed(() => renewalNotice(props.contract.renewal, props.contract.can_read_cost));

async function open() {
  renewedDetail.value = null;
  loadError.value = "";
  openCreate(props.contract);
  try {
    await ensureVendors();
  } catch (err) {
    loadError.value = "The list of vendors could not be loaded. Close the dialog and try again.";
  }
}

function onClosed() {
  if (!renewedDetail.value) return;
  const detail = renewedDetail.value;
  renewedDetail.value = null;
  emit("renewed", detail);
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    :title="`Renew contract — ${contract.title}`"
    save-label="Renew contract"
    :saving="saving"
    :dirty="dirty"
    :error="topError"
    @save="save"
    @closed="onClosed"
  >
    <div class="alert alert-info py-2" data-testid="renewal-notice">{{ notice }}</div>
    <ContractFields
      v-model:form="form"
      :field-error="fieldError"
      mode="renew"
      :vendors="vendors ?? []"
      :stored-vendor="storedVendor"
      :can-read-callout="Boolean(contract.can_read_callout)"
      :can-read-cost="Boolean(contract.can_read_cost)"
      id-prefix="renew"
    />
  </FormModal>
</template>
