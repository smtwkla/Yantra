<script setup>
/**
 * Failure codes (S016) — the three ISO 14224 pick-lists tickets use, behind one switch so
 * Masters keeps a single section: failure modes (what is seen, the operator's symptom),
 * failure causes (why it failed) and maintenance actions (what was done).
 */
import { ref } from "vue";
import FailureCausesPanel from "./FailureCausesPanel.vue";
import FailureModesPanel from "./FailureModesPanel.vue";
import MaintenanceActionsPanel from "./MaintenanceActionsPanel.vue";

const lists = [
  { key: "modes", label: "Modes", panel: FailureModesPanel },
  { key: "causes", label: "Causes", panel: FailureCausesPanel },
  { key: "actions", label: "Actions", panel: MaintenanceActionsPanel },
];
const chosen = ref("modes");
</script>

<template>
  <div class="btn-group mb-3" role="group" aria-label="Failure code list">
    <button
      v-for="l in lists"
      :key="l.key"
      type="button"
      class="btn btn-sm"
      :class="chosen === l.key ? 'btn-primary' : 'btn-outline-primary'"
      :aria-pressed="chosen === l.key"
      @click="chosen = l.key"
    >
      {{ l.label }}
    </button>
  </div>
  <component :is="lists.find((l) => l.key === chosen).panel" :key="chosen" />
</template>
