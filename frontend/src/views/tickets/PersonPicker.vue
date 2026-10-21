<script setup>
/**
 * The people picker of a ticket (docs/steps/S018-work-tickets/1-brief.md § 5.8): who did the
 * work on back in service, a labour row's person, an assignee. The people come from
 * GET /api/tickets/people?ticket_id=<id> (the ticket's site, with each person's role and
 * whether it may be assigned); the parent passes them.
 *
 * A site may have a hundred names, so the list is grouped and ordered (groupPeople): the
 * user's own person first, the ticket's assignees, the maintenance ladder, then everyone else
 * the field allows, with a type-to-filter box on top. The server checks every pick again.
 */
import { computed, ref } from "vue";
import { roleLabel } from "../../utils/siteRoles";
import { groupPeople } from "../../utils/ticketLabels";

const props = defineProps({
  people: { type: Array, required: true },
  modelValue: { type: Number, default: null },
  ownPersonId: { type: Number, default: null },
  assigneeIds: { type: Array, default: () => [] },
  excludeIds: { type: Array, default: () => [] },
  assignableOnly: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
  idPrefix: { type: String, required: true },
});
const emit = defineEmits(["update:modelValue"]);

const filter = ref("");

const groups = computed(() => groupPeople(props.people, {
  ownId: props.ownPersonId,
  assigneeIds: props.assigneeIds,
  excludeIds: props.excludeIds,
  assignableOnly: props.assignableOnly,
  filter: filter.value,
}));
const picked = computed(() => props.people.find((p) => p.id === props.modelValue) ?? null);
</script>

<template>
  <div>
    <div v-if="picked" class="d-flex align-items-center gap-2 mb-2">
      <i class="fa-solid fa-user text-secondary"></i>
      <span class="fw-semibold">{{ picked.name }}</span>
      <span class="text-secondary small">{{ roleLabel(picked.role) }}</span>
    </div>
    <input
      :id="`${idPrefix}-filter`"
      v-model="filter"
      class="form-control mb-2"
      :class="{ 'is-invalid': invalid }"
      type="search"
      placeholder="Type a name to filter"
      autocomplete="off"
    />
    <div class="picker-list border rounded">
      <div v-if="!groups.length" class="p-2 text-secondary small">Nobody found.</div>
      <template v-for="group in groups" :key="group.label">
        <div class="picker-heading small text-secondary px-2 pt-2">{{ group.label }}</div>
        <div class="list-group list-group-flush">
          <button
            v-for="person in group.people"
            :key="person.id"
            type="button"
            class="list-group-item list-group-item-action py-2"
            :class="{ active: person.id === modelValue }"
            :aria-pressed="person.id === modelValue"
            @click="emit('update:modelValue', person.id)"
          >
            {{ person.name }} <span class="small" :class="person.id === modelValue ? '' : 'text-secondary'">· {{ roleLabel(person.role) }}</span>
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.picker-list {
  max-height: 16rem;
  overflow-y: auto;
}
</style>
