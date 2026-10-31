<script setup>
/**
 * The Under contract card on the equipment page (docs/steps/S082-under-contract-card/1-brief.md § 5.3):
 * each vendor contract in force on the node or on the machine it belongs to, and those ended in the last
 * 90 days, so the technician who scans the QR label knows a vendor looks after it and whether they may
 * open it ("Do not repair", D9).
 *
 * It loads its own list (`GET /api/contracts/for-equipment/<node_id>`), as LessonsCard loads the
 * lessons, and only for a holder of contract:read_basic. With no contract it shows nothing, except to
 * a contract:edit holder, who sees "No contract on this machine." The contract keys are company-wide
 * (S087), so both checks read the user's permissions, not the node's site's. The call-out number comes only to contract:read holders (the backend leaves it out for
 * others); the rules of the text are in utils/contractLabels.js.
 */
import { computed, ref, watch } from "vue";
import { apiGet } from "../../api";
import { userPermissions } from "../../stores/auth";
import {
  DO_NOT_REPAIR, callLine, cardHeadline, coverageLines, isEnded, responseText, showsDoNotRepair, statusBadgeClass, telHref,
  viaText,
} from "../../utils/contractLabels";

const props = defineProps({
  node: { type: Object, required: true },
});

const items = ref(null); // null while loading or not asked
const loadError = ref("");
let loadSeq = 0;

const canRead = computed(() => userPermissions.value.includes("contract:read_basic"));
const canEdit = computed(() => userPermissions.value.includes("contract:edit"));

const visible = computed(() => {
  if (!canRead.value) return false;
  if (loadError.value) return true;
  return Boolean(items.value) && (items.value.length > 0 || canEdit.value);
});

// Each item with its texts worked out once
const rows = computed(() => (items.value ?? []).map((item) => {
  const response = responseText(item.response_hours);
  return {
    item,
    ended: isEnded(item),
    warning: showsDoNotRepair(item),
    headline: cardHeadline(item),
    via: item.via ? viaText(item.via) : null,
    response,
    coverage: coverageLines(item),
    call: callLine(item),
  };
}));

async function load() {
  const seq = ++loadSeq;
  loadError.value = "";
  items.value = null;
  if (!canRead.value) return;
  try {
    const loaded = await apiGet(`/api/contracts/for-equipment/${props.node.id}`);
    if (seq === loadSeq) items.value = loaded.items;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  }
}

// Vue Router reuses the page when only :id changes
watch(() => props.node.id, load, { immediate: true });
</script>

<template>
  <div v-if="visible" class="card mb-3 order-0" data-testid="contract-card">
    <div class="card-header">Under contract</div>
    <div v-if="loadError" class="card-body text-danger">Contracts could not be loaded: {{ loadError }}</div>
    <div v-else-if="rows.length === 0" class="card-body text-secondary">No contract on this machine.</div>
    <div v-else class="list-group list-group-flush">
      <div
        v-for="r in rows"
        :key="r.item.contract_id"
        class="list-group-item contract-text"
        :class="{ 'text-secondary': r.ended }"
        :data-contract="r.item.contract_id"
      >
        <div v-if="r.warning" class="alert alert-warning d-flex align-items-start gap-2 mb-2 py-2" role="alert">
          <i class="fa-solid fa-triangle-exclamation mt-1"></i>
          <span class="fw-semibold">{{ DO_NOT_REPAIR }}</span>
        </div>
        <div class="fw-bold">
          {{ r.headline }}
          <span v-if="r.item.status.kind === 'ending'" class="badge ms-1" :class="statusBadgeClass('ending')">
            {{ r.item.status.label }}
          </span>
        </div>
        <div v-if="r.via" class="small">{{ r.via }}</div>
        <div v-if="r.response">Response time: {{ r.response }}</div>
        <div v-for="line in r.coverage" :key="line">{{ line }}</div>
        <div v-if="r.call">
          {{ r.call.text }}
          <a v-if="r.call.number" :href="telHref(r.call.number)" class="d-inline-block tap-target">{{ r.call.number }}</a>
        </div>
        <router-link :to="`/contracts/${r.item.contract_id}`" class="d-inline-block mt-1 tap-target">Open contract</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.contract-text {
  overflow-wrap: anywhere;
}
</style>
