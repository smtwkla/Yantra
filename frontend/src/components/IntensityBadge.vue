<script setup>
/** IntensityBadge — a ticket's intensity: critical red "Breakdown", degraded amber "Defect", initial grey "Defect · initial" (S017). */
import { INTENSITY_BADGE_CLASS, INTENSITY_LABELS } from "../utils/ticketLabels";

defineProps({ intensity: { type: String, required: true } });
</script>

<template>
  <span class="badge" :class="INTENSITY_BADGE_CLASS[intensity]">{{ INTENSITY_LABELS[intensity] ?? intensity }}</span>
</template>
