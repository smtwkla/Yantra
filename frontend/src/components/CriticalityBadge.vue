<script setup>
/** CriticalityBadge — the A/B/C grade as a badge; `inherited` marks a grade a part takes from its equipment. */
import { CRITICALITY_BADGE_CLASS, CRITICALITY_LABELS } from "../utils/equipmentLabels";

defineProps({
  grade: { type: String, required: true },
  inherited: { type: Boolean, default: false },
});
</script>

<template>
  <span class="badge" :class="CRITICALITY_BADGE_CLASS[grade]">
    {{ CRITICALITY_LABELS[grade] ?? grade }}<span v-if="inherited" class="fw-normal"> · inherited</span>
  </span>
</template>
