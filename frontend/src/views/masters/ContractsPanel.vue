<script setup>
/**
 * Contracts — the register of vendor contracts (docs/steps/S080-contract-register; R02.1; ISO 55001 § 8.3,
 * ISO 9001 § 8.4).  One record per contract, company-wide (S087): the vendor (Masters › Vendors), type, period,
 * what is covered, PM visits, response time; its sites are its machines' sites (the Sites column, and the Site
 * filter lists the contracts with a machine at that site).  The status comes from the dates (the API sends it).
 * The call-out number and the cost note come only to the readers who may see them (the API leaves them out
 * otherwise), and the dialog sends them only with the list's flags.  Never deleted: a contract entered by mistake
 * is deactivated.  S081: each title opens the contract page (its machines and prices), and the managers see the
 * contract's cost before GST, the sum of its machines' prices (a column shown to readers of prices).  S085: the
 * dialog's fields live in ContractFields.vue, shared with the renewal on the contract page.
 */
import { computed, onMounted, ref, watch } from "vue";
import { apiGet } from "../../api";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import ContractFields from "../contracts/ContractFields.vue";
import { ensureVendors, vendors } from "../../stores/masters";
import {
  CONTRACT_TYPES,
  EMPTY_CONTRACT_FORM,
  STATUS_FILTERS,
  contractBody,
  contractForm,
  contractTypeLabel,
  formatRupees,
  siteCodesText,
  statusBadgeClass,
} from "../../utils/contractLabels";
import { formatDate } from "../../utils/datetime";
import { useMasterForm } from "./useMasterForm";

const DEFAULT_STATUS = "not_ended";

const items = ref(null);
const total = ref(0);
const sites = ref([]);
// The reader's flags, company-wide (S087): Add contract, and the gated fields of the dialog
const flags = ref({ can_add: false, can_read_callout: false, can_read_cost: false });
const loadError = ref("");
const siteFilter = ref("");
const typeFilter = ref("");
const statusFilter = ref(DEFAULT_STATUS);
const vendorFilter = ref("");
const showInactive = ref(false);

const canAdd = computed(() => flags.value.can_add);
const showCost = computed(() => flags.value.can_read_cost);
const filtersAtDefault = computed(
  () => !siteFilter.value && !typeFilter.value && !vendorFilter.value && statusFilter.value === DEFAULT_STATUS
);

function vendorName(v) {
  return v.active ? v.name : `${v.name} (inactive)`;
}

/** Type, vendor and the machines' sites, the small line under the title on a phone (as VendorsPanel's details);
 * the sites left out when the contract has no machine. */
function phoneLine(c) {
  const sitesPart = c.site_codes?.length ? siteCodesText(c.site_codes) : "";
  return [contractTypeLabel(c.contract_type), c.vendor_active ? c.vendor_name : `${c.vendor_name} (inactive)`, sitesPart]
    .filter(Boolean)
    .join(" · ");
}

// Filters can change faster than the answers come back: only the latest request's answer is shown (S080 CR1-03)
let latestRequest = 0;

async function reload() {
  const request = ++latestRequest;
  loadError.value = "";
  const query = new URLSearchParams({ status: statusFilter.value });
  if (siteFilter.value) query.set("site_id", siteFilter.value);
  if (typeFilter.value) query.set("contract_type", typeFilter.value);
  if (vendorFilter.value) query.set("vendor_id", vendorFilter.value);
  if (showInactive.value) query.set("include_inactive", "1");
  try {
    // The vendors too: a save drops the shared masters cache (useMasterForm), and both lists need them
    // (fresh when the tab opens, so a vendor deactivated meanwhile is marked)
    const [answer] = await Promise.all([apiGet(`/api/contracts?${query}`), ensureVendors({ refresh: items.value === null })]);
    if (request !== latestRequest) return;
    items.value = answer.items;
    total.value = answer.total;
    sites.value = answer.sites;
    flags.value = {
      can_add: Boolean(answer.can_add),
      can_read_callout: Boolean(answer.can_read_callout),
      can_read_cost: Boolean(answer.can_read_cost),
    };
  } catch (err) {
    if (request === latestRequest) loadError.value = err.message;
  }
}

watch([siteFilter, typeFilter, statusFilter, vendorFilter, showInactive], reload);

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} = useMasterForm({
  path: "/api/contracts",
  blank: () => ({ ...EMPTY_CONTRACT_FORM, contract_type: "amc" }),
  fromRecord: contractForm,
  toBody: (f) => contractBody(f, flags.value),
  label: (c) => c.title,
  reload,
});

// On edit, the contract's vendor: ContractFields lists it first when it is inactive, so the contract still saves
const storedVendor = computed(() =>
  editingId.value !== null ? ((vendors.value ?? []).find((v) => v.id === form.value.vendor_id) ?? null) : null
);

onMounted(reload);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
      <span><i class="fa-solid fa-file-signature me-2"></i>Contracts</span>
      <div class="d-flex align-items-center gap-3">
        <div class="form-check form-switch mb-0">
          <input id="contracts-inactive" v-model="showInactive" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="contracts-inactive">Show inactive</label>
        </div>
        <button v-if="canAdd" class="btn btn-sm btn-primary" @click="openCreate()">
          <i class="fa-solid fa-plus me-1"></i>Add contract
        </button>
      </div>
    </div>
    <div class="card-body">
      <div class="d-flex flex-wrap gap-2 mb-3">
        <select v-model="siteFilter" class="form-select form-select-sm w-auto" aria-label="Site">
          <option value="">All sites</option>
          <option v-for="s in sites" :key="s.id" :value="s.id">{{ s.active ? s.code : `${s.code} (inactive)` }}</option>
        </select>
        <select v-model="typeFilter" class="form-select form-select-sm w-auto" aria-label="Type">
          <option value="">All types</option>
          <option v-for="t in CONTRACT_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>
        <select v-model="statusFilter" class="form-select form-select-sm w-auto" aria-label="Status">
          <option v-for="s in STATUS_FILTERS" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <select v-model="vendorFilter" class="form-select form-select-sm w-auto" aria-label="Vendor">
          <option value="">All vendors</option>
          <option v-for="v in vendors ?? []" :key="v.id" :value="v.id">{{ vendorName(v) }}</option>
        </select>
      </div>

      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="items === null && !loadError" class="text-secondary">Loading…</div>
      <template v-else-if="items !== null && items.length === 0">
        <p v-if="filtersAtDefault" class="text-secondary mb-0">
          No contracts in force or starting later.<template v-if="canAdd"> Add one with <em>Add contract</em>.</template>
        </p>
        <p v-else class="text-secondary mb-0">No contracts match these filters.</p>
      </template>
      <template v-else-if="items !== null">
        <div class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead>
              <tr>
                <th class="d-none d-md-table-cell">Type</th>
                <th>Contract</th>
                <th class="d-none d-md-table-cell">Vendor</th>
                <th class="d-none d-md-table-cell">Sites</th>
                <th class="d-none d-md-table-cell">From</th>
                <th class="d-none d-md-table-cell">To</th>
                <th v-if="showCost" class="d-none d-md-table-cell text-end">Cost before GST</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in items" :key="c.id" :class="{ 'text-secondary': !c.active }">
                <td class="d-none d-md-table-cell">{{ contractTypeLabel(c.contract_type) }}</td>
                <td>
                  <router-link :to="`/contracts/${c.id}`" class="fw-semibold d-block">{{ c.title }}</router-link>
                  <div v-if="c.contract_number" class="small text-secondary d-none d-md-block">{{ c.contract_number }}</div>
                  <div class="small text-secondary d-md-none">{{ phoneLine(c) }}</div>
                </td>
                <td class="d-none d-md-table-cell">
                  {{ c.vendor_name }}<span v-if="!c.vendor_active" class="text-secondary"> (inactive)</span>
                </td>
                <td class="d-none d-md-table-cell">{{ siteCodesText(c.site_codes) }}</td>
                <td class="d-none d-md-table-cell text-nowrap">{{ formatDate(c.from_date) }}</td>
                <td class="d-none d-md-table-cell text-nowrap">{{ formatDate(c.to_date) }}</td>
                <td v-if="showCost" class="d-none d-md-table-cell text-end text-nowrap">
                  {{ c.price_total === undefined || c.price_total === null ? "—" : formatRupees(c.price_total) }}
                </td>
                <td>
                  <span class="badge" :class="statusBadgeClass(c.status.kind)">{{ c.status.label }}</span>
                  <span v-if="!c.active" class="badge text-bg-light ms-1">Inactive</span>
                  <div class="small text-secondary d-md-none text-nowrap">To {{ formatDate(c.to_date) }}</div>
                </td>
                <td class="text-end text-nowrap">
                  <button v-if="c.can_edit" class="btn btn-sm btn-outline-secondary" title="Edit" aria-label="Edit" @click="openEdit(c)">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <template v-if="items !== null && !loadError">
        <div v-if="items.length" class="form-text mt-2">
          {{ total === 1 ? "1 contract." : `${total} contracts.` }}
          <template v-if="total > items.length"> {{ items.length }} of {{ total }} shown. Narrow the filters.</template>
        </div>
        <div v-if="statusFilter === DEFAULT_STATUS" class="form-text">Ended contracts: choose Ended in Status.</div>
      </template>
    </div>
  </div>

  <FormModal ref="modal" :title="editingId === null ? 'Add contract' : 'Edit contract'" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
    <template v-if="editingId !== null" #footer-left>
      <ActiveToggle
        :active="editingActive"
        :label="editingLabel"
        :confirming="confirmingDeactivate"
        :disabled="saving"
        @ask="confirmingDeactivate = true"
        @cancel="confirmingDeactivate = false"
        @change="changeActive"
      />
    </template>
    <ContractFields
      v-model:form="form"
      :field-error="fieldError"
      :mode="editingId === null ? 'create' : 'edit'"
      :vendors="vendors ?? []"
      :stored-vendor="storedVendor"
      :can-read-callout="flags.can_read_callout"
      :can-read-cost="flags.can_read_cost"
    />
  </FormModal>
</template>
