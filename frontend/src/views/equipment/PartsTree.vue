<script setup>
/**
 * PartsTree — the parts of an equipment page, two levels as the API returns them
 * (children, each with its own children). It renders its own children recursively.
 * Scrapped parts stay listed, greyed and struck through.
 */
import CriticalityBadge from "../../components/CriticalityBadge.vue";
import StatusBadge from "../../components/StatusBadge.vue";

defineProps({
  children: { type: Array, required: true },
  nested: { type: Boolean, default: false }, // inner levels have no "No parts yet"
});
</script>

<template>
  <p v-if="children.length === 0 && !nested" class="text-secondary mb-0">No parts yet.</p>
  <ul v-else class="list-unstyled mb-0" :class="{ 'ms-4 mt-1': nested }">
    <li v-for="part in children" :key="part.id" class="mb-1">
      <div class="part-row" :class="{ 'text-secondary text-decoration-line-through': part.status === 'scrapped' }">
        <router-link :to="`/equipment/${part.id}`" class="fw-semibold">{{ part.code }}</router-link>
        <span>{{ part.name }}</span>
        <StatusBadge :status="part.status" class="ms-auto" />
        <CriticalityBadge :grade="part.effective_criticality" :inherited="part.criticality === null" />
      </div>
      <PartsTree v-if="part.children?.length" :children="part.children" nested />
    </li>
  </ul>
</template>

<style scoped>
.part-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
</style>
