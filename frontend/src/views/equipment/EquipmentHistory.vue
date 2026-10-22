<script setup>
/** EquipmentHistory — the events of a node, newest first (the API sorts them), in plain words. */
import { useShowMore } from "../../composables/useShowMore";
import { formatDateTime } from "../../utils/datetime";
import { describeEvent } from "../../utils/equipmentLabels";

const props = defineProps({ events: { type: Array, required: true } });
const { shown, canExpand, toggle, toggleLabel } = useShowMore(() => props.events);
</script>

<template>
  <p v-if="events.length === 0" class="text-secondary mb-0">No history yet.</p>
  <template v-else>
    <ul class="list-unstyled mb-0">
      <li v-for="e in shown" :key="e.id" class="mb-2">
        <div class="small text-secondary">{{ formatDateTime(e.created_at) }} · {{ e.created_by }}</div>
        <div>{{ describeEvent(e) }}</div>
      </li>
    </ul>
    <button v-if="canExpand" type="button" class="btn btn-link px-0" @click="toggle">{{ toggleLabel }}</button>
  </template>
</template>
