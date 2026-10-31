<script setup>
/**
 * The contract line on the ticket page (docs/steps/S086-contract-breakdown-calls/1-brief.md § 5.6): on an open ticket
 * whose machine or part is under a contract in force, "Under AMC with Atlas Copco until 31-03-2027 · response 24 hours
 * · breakdown calls included", the headline a link to the contract, and S082's "Do not repair" warning when only the
 * vendor may repair (D9). ISO 55001 § 8.3: work given to an outside firm stays the plant's, so the engineer who
 * assigns the work sees the vendor, and the technician sees the warning before *Start*.
 *
 * It reads S082's card route (`GET /api/contracts/for-equipment/<node_id>`, the same contracts and keys as the
 * machine's card) once per ticket while the ticket is open and the ticket's site permissions hold
 * contract:read_basic; it keeps the items not ended. With nothing to show, or on any error, it draws nothing: the
 * ticket page works without it.
 */
import { computed, ref, watch } from "vue";
import { apiGet } from "../../api";
import { DO_NOT_REPAIR, isEnded, showsDoNotRepair, ticketContractLine } from "../../utils/contractLabels";

const props = defineProps({
  ticket: { type: Object, required: true },
});

const items = ref([]);
let loadSeq = 0;

const isOpen = computed(() => props.ticket.state !== "closed");
const canRead = computed(() => (props.ticket.permissions ?? []).includes("contract:read_basic"));
const nodeId = computed(() => props.ticket.component?.id ?? props.ticket.machine.id);

const rows = computed(() => items.value.map((item) => ({
  item,
  line: ticketContractLine(item),
  warning: showsDoNotRepair(item),
})));

async function load() {
  const seq = ++loadSeq;
  items.value = [];
  if (!isOpen.value || !canRead.value) return;
  try {
    const loaded = await apiGet(`/api/contracts/for-equipment/${nodeId.value}`);
    if (seq === loadSeq) items.value = loaded.items.filter((item) => !isEnded(item));
  } catch {
    // § 5.6: no line on an error (a 404 when the machine now stands outside the reader's units); the page works on
  }
}

// Once per ticket, and when it opens or closes; not after every write that replaces the page's copy
watch([() => props.ticket.id, isOpen, nodeId], load, { immediate: true });
</script>

<template>
  <div v-if="rows.length" class="mb-3" data-testid="ticket-contract">
    <div v-for="r in rows" :key="r.item.contract_id" class="small contract-line" :data-contract="r.item.contract_id">
      <div>
        <i class="fa-solid fa-file-signature me-1 text-secondary" aria-hidden="true"></i>
        <router-link :to="`/contracts/${r.item.contract_id}`">{{ r.line.headline }}</router-link>{{ r.line.details }}
      </div>
      <div v-if="r.warning" class="alert alert-warning d-flex align-items-start gap-2 mt-1 mb-0 py-2" role="alert">
        <i class="fa-solid fa-triangle-exclamation mt-1" aria-hidden="true"></i>
        <span class="fw-semibold">{{ DO_NOT_REPAIR }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.contract-line {
  overflow-wrap: anywhere;
}
.contract-line + .contract-line {
  margin-top: 0.5rem;
}
</style>
