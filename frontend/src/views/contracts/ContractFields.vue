<script setup>
/**
 * The contract dialog's fields (S080 § 5.7, items 1–13), one copy for add and edit in Masters › Contracts and for
 * the renewal on the contract page (docs/steps/S085-contract-renewal/1-brief.md § 5.7, E7). The parent owns the
 * form (useFormModal) and passes it in as ``v-model:form``; the fields write into it. The call-out number and the
 * cost note show only with their flags, so a field the reader may not see is never in the dialog.
 *
 * Modes: "create", "edit" and "renew". A contract has no site (S087): its sites are its machines' sites.
 * The vendors offered are the active ones, with ``storedVendor`` first when it is inactive, so the contract still
 * saves; in renew mode a line under the field says so.
 */
import { computed } from "vue";
import { CONTRACT_TYPES } from "../../utils/contractLabels";

const form = defineModel("form", { type: Object, required: true });
const props = defineProps({
  fieldError: { type: Function, required: true },
  mode: { type: String, required: true, validator: (value) => ["create", "edit", "renew"].includes(value) },
  vendors: { type: Array, default: () => [] },
  storedVendor: { type: Object, default: null }, // {id, name, active}
  canReadCallout: { type: Boolean, default: false },
  canReadCost: { type: Boolean, default: false },
  idPrefix: { type: String, default: "contract" },
});

const id = (name) => `${props.idPrefix}-${name}`;

function vendorName(v) {
  return v.active ? v.name : `${v.name} (inactive)`;
}

const vendorOptions = computed(() => {
  const active = props.vendors.filter((v) => v.active);
  const stored = props.storedVendor;
  return stored && !stored.active ? [stored, ...active.filter((v) => v.id !== stored.id)] : active;
});

// Renew: the old contract's vendor is inactive and still chosen (S085 § 5.7; S079's text)
const inactiveVendorLine = computed(() => {
  const stored = props.storedVendor;
  if (props.mode !== "renew" || !stored || stored.active || form.value.vendor_id !== stored.id) return "";
  return `Vendor ${stored.name} is inactive. Choose another vendor or reactivate it.`;
});
</script>

<template>
  <div class="row g-3">
    <div class="col-12 col-md-6">
      <label class="form-label" :for="id('type')">Type</label>
      <select :id="id('type')" v-model="form.contract_type" class="form-select" :class="{ 'is-invalid': fieldError('contract_type') }">
        <option v-for="t in CONTRACT_TYPES" :key="t.value" :value="t.value">{{ t.label }} — {{ t.help }}</option>
      </select>
      <div v-if="fieldError('contract_type')" class="invalid-feedback d-block">{{ fieldError("contract_type") }}</div>
    </div>
    <div class="col-12">
      <label class="form-label" :for="id('vendor')">Vendor</label>
      <select :id="id('vendor')" v-model="form.vendor_id" class="form-select" :class="{ 'is-invalid': fieldError('vendor_id') }">
        <option :value="null" disabled>Choose a vendor</option>
        <option v-for="v in vendorOptions" :key="v.id" :value="v.id">{{ vendorName(v) }}</option>
      </select>
      <div v-if="fieldError('vendor_id')" class="invalid-feedback d-block">{{ fieldError("vendor_id") }}</div>
      <!-- The save's refusal says the same; then only the refusal shows -->
      <div v-if="inactiveVendorLine && !fieldError('vendor_id')" class="form-text text-warning-emphasis">{{ inactiveVendorLine }}</div>
      <div class="form-text">Choose a vendor from Vendors.</div>
    </div>
    <div class="col-12">
      <label class="form-label" :for="id('title')">Title</label>
      <input :id="id('title')" v-model="form.title" class="form-control" :class="{ 'is-invalid': fieldError('title') }" maxlength="100" />
      <div v-if="fieldError('title')" class="invalid-feedback d-block">{{ fieldError("title") }}</div>
      <div v-if="mode === 'renew'" class="form-text">Change the years in the title, e.g. Atlas Copco AMC 2027–28.</div>
      <div v-else class="form-text">e.g. Atlas Copco AMC 2026–27</div>
    </div>
    <div class="col-12">
      <label class="form-label" :for="id('number')">Vendor's contract number (optional)</label>
      <input :id="id('number')" v-model="form.contract_number" class="form-control" :class="{ 'is-invalid': fieldError('contract_number') }" maxlength="60" />
      <div v-if="fieldError('contract_number')" class="invalid-feedback d-block">{{ fieldError("contract_number") }}</div>
    </div>
    <div class="col-6">
      <label class="form-label" :for="id('from')">From</label>
      <input :id="id('from')" v-model="form.from_date" type="date" class="form-control" :class="{ 'is-invalid': fieldError('from_date') }" />
      <div v-if="fieldError('from_date')" class="invalid-feedback d-block">{{ fieldError("from_date") }}</div>
    </div>
    <div class="col-6">
      <label class="form-label" :for="id('to')">To</label>
      <input :id="id('to')" v-model="form.to_date" type="date" class="form-control" :class="{ 'is-invalid': fieldError('to_date') }" />
      <div v-if="fieldError('to_date')" class="invalid-feedback d-block">{{ fieldError("to_date") }}</div>
    </div>
    <div class="col-6">
      <label class="form-label" :for="id('visits')">PM visits per year</label>
      <input :id="id('visits')" v-model="form.pm_visits_per_year" type="number" inputmode="numeric" min="0" max="52" class="form-control" :class="{ 'is-invalid': fieldError('pm_visits_per_year') }" />
      <div v-if="fieldError('pm_visits_per_year')" class="invalid-feedback d-block">{{ fieldError("pm_visits_per_year") }}</div>
    </div>
    <div class="col-6">
      <label class="form-label" :for="id('response')">Response time (hours)</label>
      <input :id="id('response')" v-model="form.response_hours" type="number" inputmode="numeric" min="1" max="720" class="form-control" :class="{ 'is-invalid': fieldError('response_hours') }" />
      <div v-if="fieldError('response_hours')" class="invalid-feedback d-block">{{ fieldError("response_hours") }}</div>
    </div>
    <fieldset class="col-12">
      <legend class="form-label fs-6 mb-1">Covered by the contract</legend>
      <div class="form-check">
        <input :id="id('labour')" v-model="form.covers_labour" class="form-check-input" type="checkbox" />
        <label class="form-check-label" :for="id('labour')">Labour</label>
      </div>
      <div class="form-check">
        <input :id="id('parts')" v-model="form.covers_parts" class="form-check-input" type="checkbox" />
        <label class="form-check-label" :for="id('parts')">Spare parts</label>
      </div>
      <div class="form-check">
        <input :id="id('consumables')" v-model="form.covers_consumables" class="form-check-input" type="checkbox" />
        <label class="form-check-label" :for="id('consumables')">Consumables (oil, filters)</label>
      </div>
      <div class="form-check">
        <input :id="id('calls')" v-model="form.covers_breakdown_calls" class="form-check-input" type="checkbox" />
        <label class="form-check-label" :for="id('calls')">Breakdown calls</label>
      </div>
      <div v-for="field in ['covers_labour', 'covers_parts', 'covers_consumables', 'covers_breakdown_calls']" :key="field">
        <div v-if="fieldError(field)" class="invalid-feedback d-block">{{ fieldError(field) }}</div>
      </div>
    </fieldset>
    <div v-if="form.covers_breakdown_calls" class="col-12 col-md-6">
      <label class="form-label" :for="id('calls-per-year')">Calls per year</label>
      <input :id="id('calls-per-year')" v-model="form.breakdown_calls_per_year" type="number" inputmode="numeric" min="1" max="365" class="form-control" :class="{ 'is-invalid': fieldError('breakdown_calls_per_year') }" />
      <div v-if="fieldError('breakdown_calls_per_year')" class="invalid-feedback d-block">{{ fieldError("breakdown_calls_per_year") }}</div>
      <div class="form-text">Leave empty when the calls have no limit.</div>
    </div>
    <div v-else-if="fieldError('breakdown_calls_per_year')" class="col-12">
      <div class="invalid-feedback d-block">{{ fieldError("breakdown_calls_per_year") }}</div>
    </div>
    <div class="col-12">
      <label class="form-label" :for="id('covered')">Covered</label>
      <textarea :id="id('covered')" v-model="form.covered_text" rows="2" class="form-control" :class="{ 'is-invalid': fieldError('covered_text') }" maxlength="1000"></textarea>
      <div v-if="fieldError('covered_text')" class="invalid-feedback d-block">{{ fieldError("covered_text") }}</div>
    </div>
    <div class="col-12">
      <label class="form-label" :for="id('not-covered')">Not covered</label>
      <textarea :id="id('not-covered')" v-model="form.not_covered_text" rows="2" class="form-control" :class="{ 'is-invalid': fieldError('not_covered_text') }" maxlength="1000"></textarea>
      <div v-if="fieldError('not_covered_text')" class="invalid-feedback d-block">{{ fieldError("not_covered_text") }}</div>
    </div>
    <div class="col-12">
      <div class="form-check">
        <input :id="id('only-vendor')" v-model="form.only_vendor_repairs" class="form-check-input" type="checkbox" />
        <label class="form-check-label" :for="id('only-vendor')">Only the vendor may repair</label>
      </div>
      <div v-if="fieldError('only_vendor_repairs')" class="invalid-feedback d-block">{{ fieldError("only_vendor_repairs") }}</div>
      <div class="form-text">
        Tick when the contract is void if anyone else repairs the machine. The machine's page will then warn: Do not repair.
      </div>
    </div>
    <div v-if="canReadCallout" class="col-12">
      <label class="form-label" :for="id('callout')">Call-out number</label>
      <input :id="id('callout')" v-model="form.callout_number" type="tel" inputmode="tel" class="form-control" :class="{ 'is-invalid': fieldError('callout_number') }" maxlength="20" />
      <div v-if="fieldError('callout_number')" class="invalid-feedback d-block">{{ fieldError("callout_number") }}</div>
      <div class="form-text">The vendor's breakdown line. Engineers and managers see it.</div>
    </div>
    <div v-if="canReadCost" class="col-12">
      <div class="small fw-semibold text-secondary mb-1">Managers only</div>
      <label class="form-label" :for="id('cost')">Cost note</label>
      <input :id="id('cost')" v-model="form.cost_note" class="form-control" :class="{ 'is-invalid': fieldError('cost_note') }" maxlength="255" />
      <div v-if="fieldError('cost_note')" class="invalid-feedback d-block">{{ fieldError("cost_note") }}</div>
      <div v-if="mode === 'renew'" class="form-text">Enter this period's cost note. Last period's note stays on the old contract.</div>
      <div v-else class="form-text">Only the managers see this note.</div>
    </div>
    <div class="col-12">
      <label class="form-label" :for="id('notes')">Notes</label>
      <textarea :id="id('notes')" v-model="form.notes" rows="2" class="form-control" :class="{ 'is-invalid': fieldError('notes') }" maxlength="1000"></textarea>
      <div v-if="fieldError('notes')" class="invalid-feedback d-block">{{ fieldError("notes") }}</div>
      <div class="form-text">Do not enter prices here: every reader of the contract sees the notes.</div>
    </div>
  </div>
</template>
