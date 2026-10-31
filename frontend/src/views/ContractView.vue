<script setup>
/**
 * The contract page (docs/steps/S081-contract-equipment/1-brief.md § 5.7; R02.2): the terms, and the machines the
 * contract covers with their prices and the total. ISO 55001 § 8.3: work given to an outside firm stays the
 * plant's to control, so each machine shows which contract covers it, until when and at what price.
 *
 * Every field comes from the API as the reader may see it: the call-out number, the cost note, the prices and the
 * total are absent for a reader without their key, and the buttons follow the detail's flags, so none ends in a
 * refusal. Each write answers with the whole detail, which replaces the page's copy. A machine is removed after a
 * question in its row (as the Meters card). The terms are edited in Masters › Contracts (B9).
 *
 * The contract's documents and photos (docs/steps/S083-contract-documents/1-brief.md § 5.7): the shared Documents
 * and Photos cards after the machines, only for a reader with can_read_documents (contract:read_senior at the
 * site: a quote or a signed contract shows the price); their buttons follow can_edit_documents. Others see nothing
 * of them, as of the price.
 *
 * The renewal (docs/steps/S085-contract-renewal/1-brief.md § 5.7): *Renew contract* shows only when the detail's
 * can_renew; its dialog makes the next contract and the page then opens it. The chain lines link the contract this
 * one renews and its renewal; an inactive renewal tells an editor how to renew again.
 */
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiDelete, apiGet } from "../api";
import LifecycleBadge from "../components/LifecycleBadge.vue";
import DocumentsCards from "../components/documents/DocumentsCards.vue";
import {
  chainText,
  contractTypeLabel,
  coverageLines,
  formatRupees,
  overlapText,
  responseText,
  statusBadgeClass,
} from "../utils/contractLabels";
import { formatDate } from "../utils/datetime";
import ContractMachineDialog from "./contracts/ContractMachineDialog.vue";
import ContractRenewDialog from "./contracts/ContractRenewDialog.vue";

const route = useRoute();
const router = useRouter();

const contract = ref(null);
const loading = ref(true);
const notFound = ref(false);
const loadError = ref("");
const actionError = ref("");
const confirmingId = ref(null); // the machine whose Remove asks first
const removing = ref(false);
const dialog = ref(null);
const renewDialog = ref(null);
let loadSeq = 0;

async function load() {
  const id = route.params.id;
  if (id === undefined) return; // the route is changing to another page
  const seq = ++loadSeq;
  if (contract.value && String(contract.value.id) !== String(id)) contract.value = null;
  loading.value = true;
  notFound.value = false;
  loadError.value = "";
  confirmingId.value = null;
  try {
    const loaded = await apiGet(`/api/contracts/${id}`);
    if (seq === loadSeq) contract.value = loaded;
  } catch (err) {
    if (seq !== loadSeq) return;
    if (err.status === 404) {
      contract.value = null;
      notFound.value = true;
    } else {
      loadError.value = err.message;
    }
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

watch(() => route.params.id, load, { immediate: true });

const vendorText = computed(() => {
  const c = contract.value;
  return c.vendor_active ? c.vendor_name : `${c.vendor_name} (inactive)`;
});
const updatedText = computed(() => {
  const c = contract.value;
  return `${formatDate(c.updated_at ?? c.created_at)} · ${c.updated_by ?? c.created_by}`;
});
const canAdd = computed(() => contract.value.can_edit && Boolean(contract.value.active));
const canEditPrice = computed(() => contract.value.can_edit && contract.value.can_read_cost);
const docsPath = computed(() => `/api/contracts/${contract.value.id}/documents`);
const totalText = computed(() => {
  const c = contract.value;
  if (!c.priced_count) return "No prices entered yet.";
  return `Total: ${formatRupees(c.price_total)} before GST · ${c.priced_count} of ${c.machine_count} machines priced.`;
});

/** An optional value, or "—" when it is empty. */
function orDash(value) {
  return value === null || value === undefined || value === "" ? "—" : value;
}

function askRemove(line) {
  confirmingId.value = line.equipment_id;
  actionError.value = "";
}

async function remove(line) {
  removing.value = true;
  actionError.value = "";
  try {
    contract.value = await apiDelete(`/api/contracts/${contract.value.id}/equipment/${line.equipment_id}`);
    confirmingId.value = null;
  } catch (err) {
    actionError.value = err.message;
  } finally {
    removing.value = false;
  }
}

// The dialog answered with the whole detail
function onSaved(detail) {
  contract.value = detail;
  actionError.value = "";
}

// The renewal is saved and its dialog has faded out: open the new contract (the watch on the id loads it)
function onRenewed(detail) {
  router.push({ name: "contract", params: { id: detail.id } });
}
</script>

<template>
  <div class="py-3">
    <div v-if="loading && !contract" class="text-secondary">Loading…</div>
    <div v-else-if="notFound" class="alert alert-warning">
      Contract not found, or not at your sites.
      <router-link to="/equipment" class="alert-link ms-1">Open the equipment list</router-link>
    </div>
    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger tap-target" @click="load">Retry</button>
    </div>

    <template v-if="contract && !notFound">
      <h4 class="mb-1 text-break">{{ contract.title }}</h4>
      <div class="d-flex flex-wrap align-items-center gap-1 mb-1">
        <span class="badge text-bg-light border">{{ contractTypeLabel(contract.contract_type) }}</span>
        <span class="badge" :class="statusBadgeClass(contract.status.kind)">{{ contract.status.label }}</span>
        <span v-if="!contract.active" class="badge text-bg-secondary">Inactive</span>
        <button v-if="contract.can_renew" class="btn btn-outline-primary btn-sm ms-auto" @click="renewDialog.open()">
          <i class="fa-solid fa-rotate-right me-1" aria-hidden="true"></i>Renew contract
        </button>
      </div>
      <div class="text-secondary" :class="contract.renewal_of || contract.renewed_by ? 'mb-1' : 'mb-3'">
        {{ vendorText }} · {{ contract.site_code }}
      </div>
      <div v-if="contract.renewal_of || contract.renewed_by" class="small mb-3" data-testid="contract-chain">
        <div v-if="contract.renewal_of">
          Renews:
          <router-link :to="`/contracts/${contract.renewal_of.id}`">{{ contract.renewal_of.title }}</router-link>{{ chainText(contract.renewal_of) }}
        </div>
        <template v-if="contract.renewed_by">
          <div>
            Renewed by:
            <router-link :to="`/contracts/${contract.renewed_by.id}`">{{ contract.renewed_by.title }}</router-link>{{ chainText(contract.renewed_by) }}
          </div>
          <div v-if="!contract.renewed_by.active && contract.can_edit" class="form-text mt-0">
            To renew this contract again, set that renewal active in Masters › Contracts and change its terms.
          </div>
        </template>
      </div>

      <div class="card mb-3">
        <div class="card-header"><i class="fa-solid fa-file-signature me-2"></i>Terms</div>
        <div class="card-body">
          <dl class="row mb-0">
            <dt class="col-sm-4">Vendor</dt>
            <dd class="col-sm-8">{{ vendorText }}</dd>
            <dt class="col-sm-4">Vendor's contract number</dt>
            <dd class="col-sm-8">{{ orDash(contract.contract_number) }}</dd>
            <dt class="col-sm-4">Period</dt>
            <dd class="col-sm-8">{{ formatDate(contract.from_date) }} to {{ formatDate(contract.to_date) }}</dd>
            <dt class="col-sm-4">Covered</dt>
            <dd class="col-sm-8">
              <div v-for="line in coverageLines(contract)" :key="line">{{ line }}</div>
              <div v-if="contract.covered_text" class="contract-text">{{ contract.covered_text }}</div>
            </dd>
            <dt class="col-sm-4">Not covered</dt>
            <dd class="col-sm-8 contract-text">{{ orDash(contract.not_covered_text) }}</dd>
            <dt class="col-sm-4">PM visits per year</dt>
            <dd class="col-sm-8">{{ orDash(contract.pm_visits_per_year) }}</dd>
            <dt class="col-sm-4">Response time</dt>
            <dd class="col-sm-8">{{ orDash(responseText(contract.response_hours)) }}</dd>
            <dt class="col-sm-4">Only the vendor may repair</dt>
            <dd class="col-sm-8">{{ contract.only_vendor_repairs ? "Yes — the machines' pages warn: Do not repair." : "No" }}</dd>
            <template v-if="contract.can_read_callout">
              <dt class="col-sm-4">Call-out number</dt>
              <dd class="col-sm-8">{{ orDash(contract.callout_number) }}</dd>
            </template>
            <template v-if="contract.can_read_cost">
              <dt class="col-sm-4">Cost note</dt>
              <dd class="col-sm-8">{{ orDash(contract.cost_note) }}</dd>
            </template>
            <dt class="col-sm-4">Notes</dt>
            <dd class="col-sm-8 contract-text">{{ orDash(contract.notes) }}</dd>
            <dt class="col-sm-4">Updated</dt>
            <dd class="col-sm-8 mb-0">{{ updatedText }}</dd>
          </dl>
        </div>
      </div>

      <div class="card mb-3" data-testid="contract-machines">
        <div class="card-header d-flex justify-content-between align-items-center gap-2">
          <span><i class="fa-solid fa-gears me-2"></i>Machines covered ({{ contract.machine_count }})</span>
          <button v-if="canAdd" class="btn btn-sm btn-primary" @click="dialog.openAdd()">
            <i class="fa-solid fa-plus me-1"></i>Add machine
          </button>
        </div>
        <div v-if="actionError" class="alert alert-danger m-2 mb-0" role="alert">{{ actionError }}</div>
        <div v-if="contract.machines.length === 0" class="card-body text-secondary">
          No machines on this contract yet.<template v-if="canAdd"> Add the first one with <em>Add machine</em>.</template>
        </div>
        <ul v-else class="list-group list-group-flush">
          <li v-for="line in contract.machines" :key="line.equipment_id" class="list-group-item" data-testid="contract-machine">
            <div class="d-flex flex-wrap align-items-start gap-2">
              <div class="flex-grow-1 text-break">
                <router-link v-if="line.can_open" :to="`/equipment/${line.equipment_id}`" class="fw-semibold">
                  {{ line.code }} — {{ line.name }}
                </router-link>
                <span v-else class="fw-semibold">{{ line.code }} — {{ line.name }}</span>
                <div class="small text-secondary">{{ line.full_path }}</div>
              </div>
              <LifecycleBadge v-if="line.lifecycle !== 'in_service'" :lifecycle="line.lifecycle" />
            </div>
            <div v-if="!line.at_contract_site" class="small text-warning-emphasis">Now at {{ line.site_code }}.</div>
            <div v-for="o in line.overlaps" :key="`${o.contract_id}-${o.on_code}`" class="small text-warning-emphasis" data-testid="overlap">
              <i class="fa-solid fa-triangle-exclamation me-1" aria-hidden="true"></i>{{ overlapText(o) }}
            </div>
            <div class="d-flex flex-wrap align-items-center gap-2 mt-1">
              <span v-if="contract.can_read_cost" data-testid="line-price">
                {{ line.price === null ? "No price" : formatRupees(line.price) }}
              </span>
              <span v-if="contract.can_edit && confirmingId !== line.equipment_id" class="ms-auto d-flex flex-wrap gap-1">
                <button v-if="canEditPrice" class="btn btn-sm btn-outline-secondary" @click="dialog.openEditPrice(line)">Edit price</button>
                <button class="btn btn-sm btn-outline-danger" @click="askRemove(line)">Remove</button>
              </span>
            </div>
            <div v-if="confirmingId === line.equipment_id" class="d-flex flex-wrap align-items-center justify-content-end gap-2 mt-2">
              <span>Remove {{ line.code }} from this contract? Its history keeps the line.</span>
              <button class="btn btn-sm btn-danger" :disabled="removing" @click="remove(line)">Remove</button>
              <button class="btn btn-sm btn-outline-secondary" @click="confirmingId = null">Keep</button>
            </div>
          </li>
        </ul>
        <div v-if="contract.can_read_cost && contract.machines.length" class="card-footer fw-semibold" data-testid="contract-total">
          {{ totalText }}
        </div>
      </div>

      <!-- S083 § 5.7: the signed contract, its annexures and the quotes, for contract:read_senior holders only -->
      <template v-if="contract.can_read_documents">
        <p class="small text-secondary mb-2">Only the managers of {{ contract.site_code }} see these documents and photos.</p>
        <DocumentsCards :key="contract.id" :base-path="docsPath" :can-edit="contract.can_edit_documents" />
      </template>

      <ContractMachineDialog
        :key="contract.id"
        ref="dialog"
        :contract="contract"
        :can-read-cost="contract.can_read_cost"
        @saved="onSaved"
      />
      <ContractRenewDialog v-if="contract.can_renew" :key="contract.id" ref="renewDialog" :contract="contract" @renewed="onRenewed" />
    </template>
  </div>
</template>

<style scoped>
/* Shown as entered: the line breaks of Covered, Not covered and Notes kept */
.contract-text {
  white-space: pre-wrap;
}
</style>
