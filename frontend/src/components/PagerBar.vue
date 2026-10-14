<script setup>
/**
 * PagerBar — Prev / "Page n of m (total)" / Next. Hidden when there is nothing to page.
 * A page past the end (an old bookmark) offers Prev only, back to the last page.
 */
import { computed } from "vue";

const props = defineProps({
  page: { type: Number, required: true },
  total: { type: Number, required: true },
  perPage: { type: Number, required: true },
});
const emit = defineEmits(["page"]);

const pages = computed(() => Math.ceil(props.total / props.perPage));
</script>

<template>
  <div v-if="total > 0" class="d-flex justify-content-end align-items-center gap-3 mt-3">
    <button class="btn btn-sm btn-outline-secondary" :disabled="page <= 1" @click="emit('page', Math.min(page - 1, pages))">
      <i class="fa-solid fa-chevron-left me-1"></i>Prev
    </button>
    <span class="small">Page {{ page }} of {{ pages }} ({{ total }})</span>
    <button class="btn btn-sm btn-outline-secondary" :disabled="page >= pages" @click="emit('page', page + 1)">
      Next<i class="fa-solid fa-chevron-right ms-1"></i>
    </button>
  </div>
</template>
