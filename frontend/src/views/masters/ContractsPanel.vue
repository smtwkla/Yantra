<script setup>
/**
 * Contracts — the register of vendor contracts (docs/steps/S080-contract-register; R02.1; ISO 55001 § 8.3,
 * ISO 9001 § 8.4).  One record per contract at one site: the vendor (Masters › Vendors), type, period, what is
 * covered, PM visits, response time.  The status comes from the dates (the API sends it).  The call-out number
 * and the cost note come only to the readers who may see them (the API leaves them out otherwise), and the
 * dialog sends them only for the chosen site's flags.  Never deleted: a contract entered by mistake is
 * deactivated.  S081: each title opens the contract page (its machines and prices), and the managers see the
 * contract's cost before GST, the sum of its machines' prices (a column shown when some site lets the user read
 * it; the API leaves the total out elsewhere).
 */
import { computed, onMounted, ref, watch } from "vue";
import { apiGet } from "../../api";
import ActiveToggle from "../../components/ActiveToggle.vue";
import FormModal from "../../components/FormModal.vue";
import { ensureVendors, vendors } from "../../stores/masters";
import {
  CONTRACT_TYPES,
  STATUS_FILTERS,
  contractBody,
  contractTypeLabel,
  formatRupees,
  statusBadgeClass,
} from "../../utils/contractLabels";
import { formatDate } from "../../utils/datetime";
import { useMasterForm } from "./useMasterForm";

const DEFAULT_STATUS = "not_ended";

const items = ref(null);
const total = ref(0);
const sites = ref([]);
const loadError = ref("");
const siteFilter = ref("");
const typeFilter = ref("");
const statusFilter = ref(DEFAULT_STATUS);
const vendorFilter = ref("");
const showInactive = ref(false);

const addableSites = computed(() => sites.value.filter((s) => s.can_add));
const canAdd = computed(() => addableSites.value.length > 0);
const showCost = computed(() => sites.value.some((s) => s.can_read_cost));
const filtersAtDefault = computed(
  () => !siteFilter.value && !typeFilter.value && !vendorFilter.value && statusFilter.value === DEFAULT_STATUS
);

function vendorName(v) {
  return v.active ? v.name : `${v.name} (inactive)`;
}

/** Type, vendor and site code, the small line under the title on a phone (as VendorsPanel's details). */
function phoneLine(c) {
  return [contractTypeLabel(c.contract_type), c.vendor_active ? c.vendor_name : `${c.vendor_name} (inactive)`, c.site_code]
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
  } catch (err) {
    if (request === latestRequest) loadError.value = err.message;
  }
}

watch([siteFilter, typeFilter, statusFilter, vendorFilter, showInactive], reload);

const EMPTY = {
  vendor_id: null, title: "", contract_number: "", from_date: "", to_date: "", covers_labour: false,
  covers_parts: false, covers_consumables: false, covers_breakdown_calls: false, breakdown_calls_per_year: "",
  covered_text: "", not_covered_text: "", pm_visits_per_year: "", response_hours: "", only_vendor_repairs: false,
  callout_number: "", cost_note: "", notes: "",
};

const {
  modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
  fieldError, modalError, openCreate, openEdit, save, changeActive,
} = useMasterForm({
  path: "/api/contracts",
  // No seed: the one site the user may add at is preselected, else none
  blank: () => ({
    ...EMPTY,
    site_id: addableSites.value.length === 1 ? addableSites.value[0].id : null,
    contract_type: "amc",
  }),
  fromRecord: (c) => {
    const record = { site_id: c.site_id, contract_type: c.contract_type };
    for (const field of Object.keys(EMPTY)) {
      const value = c[field];
      record[field] = typeof EMPTY[field] === "boolean" ? Boolean(value) : (value ?? "");
    }
    record.vendor_id = c.vendor_id;
    return record;
  },
  toBody: (f) => contractBody(f, chosenSite.value),
  label: (c) => c.title,
  reload,
});

// The site the dialog is about: its flags decide the call-out number and cost note fields
const chosenSite = computed(() => sites.value.find((s) => s.id === form.value.site_id) ?? null);

// The vendors offered: the active ones; on edit, a stored inactive vendor first, so the contract still saves
const vendorOptions = computed(() => {
  const all = vendors.value ?? [];
  const active = all.filter((v) => v.active);
  const stored = editingId.value !== null ? all.find((v) => v.id === form.value.vendor_id && !v.active) : null;
  return stored ? [stored, ...active] : active;
});

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
          <option v-for="s in sites" :key="s.id" :value="s.id">{{ s.code }}</option>
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
                <th class="d-none d-md-table-cell">Site</th>
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
                <td class="d-none d-md-table-cell">{{ c.site_code }}</td>
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
    <div class="row g-3">
      <div class="col-12 col-md-6">
        <label class="form-label" for="contract-site">Site</label>
        <select v-if="editingId === null" id="contract-site" v-model="form.site_id" class="form-select" :class="{ 'is-invalid': fieldError('site_id') }">
          <option :value="null" disabled>Choose a site</option>
          <option v-for="s in addableSites" :key="s.id" :value="s.id">{{ s.code }} — {{ s.name }}</option>
        </select>
        <div v-else id="contract-site" class="form-control-plaintext">{{ chosenSite?.code }}</div>
        <div v-if="fieldError('site_id')" class="invalid-feedback d-block">{{ fieldError("site_id") }}</div>
      </div>
      <div class="col-12 col-md-6">
        <label class="form-label" for="contract-type">Type</label>
        <select id="contract-type" v-model="form.contract_type" class="form-select" :class="{ 'is-invalid': fieldError('contract_type') }">
          <option v-for="t in CONTRACT_TYPES" :key="t.value" :value="t.value">{{ t.label }} — {{ t.help }}</option>
        </select>
        <div v-if="fieldError('contract_type')" class="invalid-feedback d-block">{{ fieldError("contract_type") }}</div>
      </div>
      <div class="col-12">
        <label class="form-label" for="contract-vendor">Vendor</label>
        <select id="contract-vendor" v-model="form.vendor_id" class="form-select" :class="{ 'is-invalid': fieldError('vendor_id') }">
          <option :value="null" disabled>Choose a vendor</option>
          <option v-for="v in vendorOptions" :key="v.id" :value="v.id">{{ vendorName(v) }}</option>
        </select>
        <div v-if="fieldError('vendor_id')" class="invalid-feedback d-block">{{ fieldError("vendor_id") }}</div>
        <div class="form-text">Choose a vendor from Vendors.</div>
      </div>
      <div class="col-12">
        <label class="form-label" for="contract-title">Title</label>
        <input id="contract-title" v-model="form.title" class="form-control" :class="{ 'is-invalid': fieldError('title') }" maxlength="100" />
        <div v-if="fieldError('title')" class="invalid-feedback d-block">{{ fieldError("title") }}</div>
        <div class="form-text">e.g. Atlas Copco AMC 2026–27</div>
      </div>
      <div class="col-12">
        <label class="form-label" for="contract-number">Vendor's contract number (optional)</label>
        <input id="contract-number" v-model="form.contract_number" class="form-control" :class="{ 'is-invalid': fieldError('contract_number') }" maxlength="60" />
        <div v-if="fieldError('contract_number')" class="invalid-feedback d-block">{{ fieldError("contract_number") }}</div>
      </div>
      <div class="col-6">
        <label class="form-label" for="contract-from">From</label>
        <input id="contract-from" v-model="form.from_date" type="date" class="form-control" :class="{ 'is-invalid': fieldError('from_date') }" />
        <div v-if="fieldError('from_date')" class="invalid-feedback d-block">{{ fieldError("from_date") }}</div>
      </div>
      <div class="col-6">
        <label class="form-label" for="contract-to">To</label>
        <input id="contract-to" v-model="form.to_date" type="date" class="form-control" :class="{ 'is-invalid': fieldError('to_date') }" />
        <div v-if="fieldError('to_date')" class="invalid-feedback d-block">{{ fieldError("to_date") }}</div>
      </div>
      <div class="col-6">
        <label class="form-label" for="contract-visits">PM visits per year</label>
        <input id="contract-visits" v-model="form.pm_visits_per_year" type="number" inputmode="numeric" min="0" max="52" class="form-control" :class="{ 'is-invalid': fieldError('pm_visits_per_year') }" />
        <div v-if="fieldError('pm_visits_per_year')" class="invalid-feedback d-block">{{ fieldError("pm_visits_per_year") }}</div>
      </div>
      <div class="col-6">
        <label class="form-label" for="contract-response">Response time (hours)</label>
        <input id="contract-response" v-model="form.response_hours" type="number" inputmode="numeric" min="1" max="720" class="form-control" :class="{ 'is-invalid': fieldError('response_hours') }" />
        <div v-if="fieldError('response_hours')" class="invalid-feedback d-block">{{ fieldError("response_hours") }}</div>
      </div>
      <fieldset class="col-12">
        <legend class="form-label fs-6 mb-1">Covered by the contract</legend>
        <div class="form-check">
          <input id="contract-labour" v-model="form.covers_labour" class="form-check-input" type="checkbox" />
          <label class="form-check-label" for="contract-labour">Labour</label>
        </div>
        <div class="form-check">
          <input id="contract-parts" v-model="form.covers_parts" class="form-check-input" type="checkbox" />
          <label class="form-check-label" for="contract-parts">Spare parts</label>
        </div>
        <div class="form-check">
          <input id="contract-consumables" v-model="form.covers_consumables" class="form-check-input" type="checkbox" />
          <label class="form-check-label" for="contract-consumables">Consumables (oil, filters)</label>
        </div>
        <div class="form-check">
          <input id="contract-calls" v-model="form.covers_breakdown_calls" class="form-check-input" type="checkbox" />
          <label class="form-check-label" for="contract-calls">Breakdown calls</label>
        </div>
        <div v-for="field in ['covers_labour', 'covers_parts', 'covers_consumables', 'covers_breakdown_calls']" :key="field">
          <div v-if="fieldError(field)" class="invalid-feedback d-block">{{ fieldError(field) }}</div>
        </div>
      </fieldset>
      <div v-if="form.covers_breakdown_calls" class="col-12 col-md-6">
        <label class="form-label" for="contract-calls-per-year">Calls per year</label>
        <input id="contract-calls-per-year" v-model="form.breakdown_calls_per_year" type="number" inputmode="numeric" min="1" max="365" class="form-control" :class="{ 'is-invalid': fieldError('breakdown_calls_per_year') }" />
        <div v-if="fieldError('breakdown_calls_per_year')" class="invalid-feedback d-block">{{ fieldError("breakdown_calls_per_year") }}</div>
        <div class="form-text">Leave empty when the calls have no limit.</div>
      </div>
      <div v-else-if="fieldError('breakdown_calls_per_year')" class="col-12">
        <div class="invalid-feedback d-block">{{ fieldError("breakdown_calls_per_year") }}</div>
      </div>
      <div class="col-12 col-md-6">
        <label class="form-label" for="contract-covered">Covered</label>
        <textarea id="contract-covered" v-model="form.covered_text" rows="2" class="form-control" :class="{ 'is-invalid': fieldError('covered_text') }" maxlength="1000"></textarea>
        <div v-if="fieldError('covered_text')" class="invalid-feedback d-block">{{ fieldError("covered_text") }}</div>
      </div>
      <div class="col-12 col-md-6">
        <label class="form-label" for="contract-not-covered">Not covered</label>
        <textarea id="contract-not-covered" v-model="form.not_covered_text" rows="2" class="form-control" :class="{ 'is-invalid': fieldError('not_covered_text') }" maxlength="1000"></textarea>
        <div v-if="fieldError('not_covered_text')" class="invalid-feedback d-block">{{ fieldError("not_covered_text") }}</div>
      </div>
      <div class="col-12">
        <div class="form-check">
          <input id="contract-only-vendor" v-model="form.only_vendor_repairs" class="form-check-input" type="checkbox" />
          <label class="form-check-label" for="contract-only-vendor">Only the vendor may repair</label>
        </div>
        <div v-if="fieldError('only_vendor_repairs')" class="invalid-feedback d-block">{{ fieldError("only_vendor_repairs") }}</div>
        <div class="form-text">
          Tick when the contract is void if anyone else repairs the machine. The machine's page will then warn: Do not repair.
        </div>
      </div>
      <div v-if="chosenSite?.can_read_callout" class="col-12">
        <label class="form-label" for="contract-callout">Call-out number</label>
        <input id="contract-callout" v-model="form.callout_number" type="tel" inputmode="tel" class="form-control" :class="{ 'is-invalid': fieldError('callout_number') }" maxlength="20" />
        <div v-if="fieldError('callout_number')" class="invalid-feedback d-block">{{ fieldError("callout_number") }}</div>
        <div class="form-text">The vendor's breakdown line. Engineers and managers see it.</div>
      </div>
      <div v-if="chosenSite?.can_read_cost" class="col-12">
        <div class="small fw-semibold text-secondary mb-1">Managers only</div>
        <label class="form-label" for="contract-cost">Cost note</label>
        <input id="contract-cost" v-model="form.cost_note" class="form-control" :class="{ 'is-invalid': fieldError('cost_note') }" maxlength="255" />
        <div v-if="fieldError('cost_note')" class="invalid-feedback d-block">{{ fieldError("cost_note") }}</div>
        <div class="form-text">Only the managers of this site see this note.</div>
      </div>
      <div class="col-12">
        <label class="form-label" for="contract-notes">Notes</label>
        <textarea id="contract-notes" v-model="form.notes" rows="2" class="form-control" :class="{ 'is-invalid': fieldError('notes') }" maxlength="1000"></textarea>
        <div v-if="fieldError('notes')" class="invalid-feedback d-block">{{ fieldError("notes") }}</div>
        <div class="form-text">Do not enter prices here: every reader of the contract sees the notes.</div>
      </div>
    </div>
  </FormModal>
</template>
