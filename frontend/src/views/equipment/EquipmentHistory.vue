<script setup>
/** EquipmentHistory — the events of a node, newest first (the API sorts them), in plain words. */
import { formatDateTime } from "../../utils/datetime";
import { describeEvent } from "../../utils/equipmentLabels";

defineProps({ events: { type: Array, required: true } });
</script>

<template>
  <p v-if="events.length === 0" class="text-secondary mb-0">No history yet.</p>
  <ul v-else class="list-unstyled mb-0">
    <li v-for="e in events" :key="e.id" class="mb-2">
      <div class="small text-secondary">{{ formatDateTime(e.created_at) }} · {{ e.created_by }}</div>
      <div>{{ describeEvent(e) }}</div>
    </li>
  </ul>
</template>
