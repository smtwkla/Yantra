<script setup>
/** LifecycleBadge — an equipment lifecycle as a coloured badge (labels and colours: utils/equipmentLabels.js). */
import { LIFECYCLE_BADGE_CLASS, LIFECYCLE_LABELS } from "../utils/equipmentLabels";

defineProps({ lifecycle: { type: String, required: true } });
</script>

<template>
  <span class="badge" :class="LIFECYCLE_BADGE_CLASS[lifecycle]">{{ LIFECYCLE_LABELS[lifecycle] ?? lifecycle }}</span>
</template>
