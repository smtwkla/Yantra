<script setup>
/**
 * The Breakdown calls card on the contract page (docs/steps/S086-contract-breakdown-calls/1-brief.md § 5.3, § 5.4):
 * every ticket on a covered machine or its parts, in the contract's period, that a Team record of the vendor is
 * assigned to or logs labour on, with its downtime and the wait on the vendor (EN 13306 logistic delay), a total
 * line and, when the contract agrees a number of calls, how many are used (ISO 9001 § 8.4: the plant keeps evidence
 * of how an outside provider performs).
 *
 * It loads its own list (`GET /api/contracts/<id>/calls`), as the Under contract card loads its own, and only for a
 * holder of ticket:read: others see no card. The rows are only the tickets the reader could open, so every serial
 * opens; "N of M calls used" comes only when the reader sees the whole site (the API's `complete`). The warning
 * says when no Team record of the vendor is linked, or none can be assigned at the site.
 */
import { computed, ref, watch } from "vue";
import { apiGet } from "../../api";
import IntensityBadge from "../../components/IntensityBadge.vue";
import { userPermissions } from "../../stores/auth";
import { callFiguresLine, callsTotalLine, callsUsedLine, vendorWarningText } from "../../utils/contractLabels";
import { formatDateTime } from "../../utils/datetime";
import { stateLabel } from "../../utils/ticketLabels";

const props = defineProps({
  contract: { type: Object, required: true },
});

const answer = ref(null); // null while loading
const loadError = ref("");
let loadSeq = 0;

const canRead = computed(() => userPermissions.value.includes("ticket:read"));

const warning = computed(() => answer.value
  && vendorWarningText(answer.value.warning, answer.value.vendor_name, answer.value.site_code));
const usedLine = computed(() => answer.value && callsUsedLine(answer.value.used));

// Each call with its texts worked out once
const rows = computed(() => (answer.value?.calls ?? []).map((call) => ({
  call,
  node: call.component
    ? `${call.machine.code} — ${call.machine.name} › ${call.component.code} — ${call.component.name}`
    : `${call.machine.code} — ${call.machine.name}`,
  figures: callFiguresLine(call),
  people: call.vendor_people.map((p) => p.name).join(", "),
})));

async function load() {
  const seq = ++loadSeq;
  loadError.value = "";
  answer.value = null;
  if (!canRead.value) return;
  try {
    const loaded = await apiGet(`/api/contracts/${props.contract.id}/calls`);
    if (seq === loadSeq) answer.value = loaded;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  }
}

// Again when the page shows another contract, or a machine is added or removed (the calls follow the lines)
watch([() => props.contract.id, () => props.contract.machine_count], load, { immediate: true });
</script>

<template>
  <div v-if="canRead" class="card mb-3" data-testid="breakdown-calls">
    <div class="card-header">
      <i class="fa-solid fa-screwdriver-wrench me-2" aria-hidden="true"></i>Breakdown calls
      <span v-if="answer" class="badge text-bg-secondary ms-1">{{ answer.calls.length }}</span>
    </div>
    <div v-if="loadError" class="card-body text-danger">Breakdown calls could not be loaded: {{ loadError }}</div>
    <div v-else-if="!answer" class="card-body text-secondary">Loading…</div>
    <template v-else>
      <div v-if="warning" class="alert alert-warning d-flex align-items-start gap-2 m-2 mb-0 py-2" role="alert">
        <i class="fa-solid fa-triangle-exclamation mt-1" aria-hidden="true"></i>
        <span>{{ warning }}</span>
      </div>
      <div v-if="rows.length === 0" class="card-body text-secondary">
        <template v-if="answer.complete">
          No breakdown calls on this contract yet. A call is a ticket that a Team record of {{ answer.vendor_name }} is
          assigned to or logs labour on.
        </template>
        <template v-else>No calls on machines of your units. Only those are listed here.</template>
      </div>
      <template v-else>
        <ul class="list-group list-group-flush">
          <li v-for="r in rows" :key="r.call.id" class="list-group-item call-text" data-testid="breakdown-call">
            <div class="d-flex flex-wrap align-items-center gap-2">
              <router-link :to="`/tickets/${r.call.id}`" class="fw-semibold">{{ r.call.serial }}</router-link>
              <IntensityBadge :intensity="r.call.intensity" />
              <span class="badge" :class="r.call.overdue ? 'text-bg-danger' : 'text-bg-light border'">{{ stateLabel(r.call) }}</span>
              <span v-if="r.call.not_a_fault" class="badge text-bg-info">Not a fault</span>
            </div>
            <div>{{ r.node }}</div>
            <div class="small">
              Happened {{ formatDateTime(r.call.occurred_at) }}<template v-if="r.call.back_in_service_at">
                · back in service {{ formatDateTime(r.call.back_in_service_at) }}</template><template
                v-else-if="r.call.is_breakdown && !r.call.not_a_fault && r.call.state !== 'closed'"> · not back in service yet</template>
            </div>
            <div v-if="r.figures" class="small">{{ r.figures }}</div>
            <div v-if="r.people" class="small text-secondary">By: {{ r.people }}</div>
          </li>
        </ul>
        <div class="card-footer">
          <div class="fw-semibold" data-testid="calls-total">{{ callsTotalLine(answer.total) }}</div>
          <div v-if="!answer.complete" class="small text-secondary">Only the calls on machines of your units are listed.</div>
          <div v-else-if="usedLine" class="small" :class="answer.used.over ? 'text-danger' : 'text-secondary'" data-testid="calls-used">
            {{ usedLine }}
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.call-text {
  overflow-wrap: anywhere;
}
</style>
