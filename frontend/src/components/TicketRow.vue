<script setup>
/**
 * One ticket as a row of a list, a link to the ticket page (the Tickets list, S017, and the Me
 * page's two ticket tabs, S031). `now` is the list's clock, for the age.
 */
import IntensityBadge from "./IntensityBadge.vue";
import { ageText, firstName, overdueBadge, planText, problemText, stateLabel, ticketRowClass } from "../utils/ticketLabels";

defineProps({
  ticket: { type: Object, required: true },
  now: { type: Date, required: true },
});
</script>

<template>
  <router-link
    :to="`/tickets/${ticket.id}`"
    class="list-group-item list-group-item-action"
    :class="ticketRowClass(ticket)"
  >
    <div class="d-flex flex-wrap align-items-center gap-2">
      <IntensityBadge :intensity="ticket.intensity" />
      <span class="fw-semibold">{{ ticket.serial }}</span>
      <span v-if="ticket.overdue" class="badge text-bg-danger">{{ overdueBadge(ticket.planned_date) }}</span>
      <span class="ms-auto small text-secondary" :title="ticket.is_breakdown ? 'Stopped for' : 'Reported'">
        <i class="fa-regular fa-clock me-1"></i>{{ ageText(ticket.occurred_at, now) }}
      </span>
    </div>
    <div class="mt-1 ticket-text">
      {{ ticket.machine.code }} — {{ ticket.machine.name }}<span v-if="ticket.component" class="text-secondary"> · {{ ticket.component.code }}</span>
    </div>
    <div class="ticket-text">{{ problemText(ticket) }}</div>
    <div class="small text-secondary">
      {{ ticket.unit.site_code }}.{{ ticket.unit.code }} · {{ stateLabel(ticket) }}<template v-if="ticket.planned_date"> · {{ planText(ticket.planned_date, ticket.waiting_reason) }}</template><template v-if="ticket.not_a_fault"> · Not a fault</template>
      <template v-if="ticket.assignees.length"> · <i class="fa-solid fa-user"></i> {{ ticket.assignees.map((a) => firstName(a.name)).join(", ") }}</template>
    </div>
  </router-link>
</template>

<style scoped>
.ticket-text {
  overflow-wrap: anywhere;
}
</style>
