<script setup>
/** StatusBadge — an equipment status as a coloured badge (labels and colours: utils/equipmentLabels.js). */
import { STATUS_BADGE_CLASS, STATUS_LABELS } from "../utils/equipmentLabels";

defineProps({ status: { type: String, required: true } });
</script>

<template>
  <span class="badge" :class="STATUS_BADGE_CLASS[status]">{{ STATUS_LABELS[status] ?? status }}</span>
</template>
