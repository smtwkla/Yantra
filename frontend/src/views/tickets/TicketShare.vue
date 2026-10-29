<script setup>
/**
 * S066: the ticket page's Share / Copy link button (brief § 1). A component of its own, keyed by
 * the ticket's id in the page, so a move to another ticket (Repeat of, Came back as) starts it fresh.
 */
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useShareLink } from "../../composables/useShareLink";
import { ticketShareText } from "../../utils/ticketLabels";

const props = defineProps({ ticket: { type: Object, required: true } });

const router = useRouter();
const { mode, share, copied, manualUrl } = useShareLink();
const box = ref(null);

// Resolved through the router, so it stays right if the app ever gets a base path
const ticketUrl = () => new URL(
  router.resolve({ name: "ticket-detail", params: { id: props.ticket.id } }).href,
  window.location.origin,
).href;

// No await before the call: Safari allows the share and the copy only inside the tap (brief § 4.5)
function onTap() {
  share({ title: props.ticket.serial, text: ticketShareText(props.ticket), url: ticketUrl() });
}

watch(manualUrl, (url) => { if (url) box.value?.select(); }, { flush: "post" });
</script>

<template>
  <!-- Two roots in the page's wrapping title row: the button stays at the right, the box wraps to its own line (CR1-04) -->
  <div class="d-flex align-items-center gap-2 ms-auto">
    <button type="button" class="btn btn-outline-secondary" data-testid="ticket-share" @click="onTap">
      <i class="fa-solid me-2" :class="mode === 'share' ? 'fa-share-nodes' : 'fa-link'"></i>{{ mode === "share" ? "Share" : "Copy link" }}
    </button>
    <span v-if="copied" role="status" class="text-success">Link copied</span>
  </div>
  <div v-if="manualUrl" class="w-100">
    <label for="ticket-share-link" class="form-label small mb-1">Copy this link</label>
    <input id="ticket-share-link" ref="box" class="form-control" readonly :value="manualUrl" data-testid="ticket-share-link" />
  </div>
</template>
