<script setup>
/** TicketLight — the traffic-light bulb of an equipment row (S029): red down, amber open ticket,
 * green none, a grey dash where the user may not read tickets. Texts: utils/ticketLabels.js. */
import { TICKET_LIGHT_LABELS } from "../utils/ticketLabels";

// light: "down" | "open" | "none" | null (the API's `ticket_light`)
defineProps({ light: { type: String, default: null } });
const COLOURS = { down: "bg-danger", open: "bg-warning", none: "bg-success" };
</script>

<template>
  <span v-if="light === null" class="text-secondary" role="img" :title="TICKET_LIGHT_LABELS.hidden" :aria-label="TICKET_LIGHT_LABELS.hidden">&ndash;</span>
  <span
    v-else
    class="ticket-light d-inline-block rounded-circle align-middle"
    :class="COLOURS[light]"
    role="img"
    :title="TICKET_LIGHT_LABELS[light]"
    :aria-label="TICKET_LIGHT_LABELS[light]"
  ></span>
</template>

<style scoped>
.ticket-light {
  width: 0.9rem;
  height: 0.9rem;
}
</style>
