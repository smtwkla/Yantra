<script setup>
/**
 * Me (docs/steps/S031-me-page/1-brief.md): three tabs, all read-only.
 *   Open work     — the open tickets assigned to me (GET /api/tickets?assigned=me&state=open);
 *   Raised by me  — the tickets I raised or that name me the reporter (?raised=me&state=…);
 *   My activity   — every timeline line I recorded (GET /api/tickets/activity).
 * The tab, the state and the page live in the URL query, as the Tickets filters do, so Back
 * returns to the same tab. The default tab is left out of the URL (defaultMeTab).
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import IntensityBadge from "../components/IntensityBadge.vue";
import PagerBar from "../components/PagerBar.vue";
import TicketRow from "../components/TicketRow.vue";
import { userPermissions, userPersonId, userRoles } from "../stores/auth";
import { ensureMyUnits, noUnits } from "../stores/equipment";
import { formatDateTime } from "../utils/datetime";
import { NO_UNITS_TEXT } from "../utils/messages";
import { activityDetail, defaultMeTab, EVENT_LABELS, isBackdated } from "../utils/ticketLabels";

const PAGE_SIZE = 50; // the API default
const TABS = [
  ["open", "Open work"],
  ["raised", "Raised by me"],
  ["activity", "My activity"],
];
const RAISED_STATES = [
  ["all", "All"],
  ["open", "Open"],
  ["closed", "Closed"],
];
const DEFAULT_RAISED_STATE = "all";

const route = useRoute();
const router = useRouter();

const page = ref(null); // {items, total, page, per_page}
const loading = ref(true);
const loadError = ref("");
const now = ref(new Date());
let loadSeq = 0;

const query = computed(() => route.query);
const defaultTab = computed(() => defaultMeTab(userPermissions.value));
const tab = computed(() => (TABS.some(([key]) => key === query.value.tab) ? query.value.tab : defaultTab.value));
const raisedState = computed(() =>
  RAISED_STATES.some(([key]) => key === query.value.state) ? query.value.state : DEFAULT_RAISED_STATE);
const pageNumber = computed(() => Math.max(1, Number.parseInt(query.value.page, 10) || 1));
const isItAdmin = computed(() => userRoles.value.includes("it_admin"));

/** Replace the query with the tab and what belongs to it; defaults are left out of the URL. */
function go({ tabKey = tab.value, state = null, pageNo = 1 }) {
  const next = {};
  if (tabKey !== defaultTab.value) next.tab = tabKey;
  if (tabKey === "raised" && state && state !== DEFAULT_RAISED_STATE) next.state = state;
  if (pageNo > 1) next.page = pageNo;
  router.replace({ query: next });
}

// A new tab drops state and page (in go)
function chooseTab(key) {
  if (key === tab.value) return;
  go({ tabKey: key });
}

// Another tab's rows have another shape: drop them whatever changed the tab (a tap on the
// tab, or a nav tap on Me that returns to the default tab)
watch(tab, () => {
  page.value = null;
});
const chooseState = (value) => go({ state: value });
const choosePage = (value) => go({ state: raisedState.value, pageNo: value });

const stateModel = computed({ get: () => raisedState.value, set: chooseState });

function listUrl() {
  const params = new URLSearchParams({ page: String(pageNumber.value), per_page: String(PAGE_SIZE) });
  if (tab.value === "activity") return `/api/tickets/activity?${params}`;
  if (tab.value === "open") {
    params.set("assigned", "me");
    params.set("state", "open");
  } else {
    params.set("raised", "me");
    params.set("state", raisedState.value);
  }
  return `/api/tickets?${params}`;
}

async function load() {
  if (route.name !== "me") return; // the route is changing to another page
  // A typed /me by a user without ticket:read shows for a moment before App.vue redirects: no call
  if (!userPermissions.value.includes("ticket:read")) return;
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const [result] = await Promise.all([apiGet(listUrl()), ensureMyUnits()]);
    if (seq !== loadSeq) return;
    page.value = result;
    now.value = new Date();
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

onMounted(load);
watch(() => route.fullPath, load);

const countText = computed(() => {
  if (!page.value) return "";
  const n = page.value.total;
  if (tab.value === "open") return `${n} open ${n === 1 ? "ticket" : "tickets"} assigned to you`;
  if (tab.value === "raised") return `${n} ${n === 1 ? "ticket" : "tickets"}`;
  return ""; // My activity: the brief gives no count
});

const notInTeam = computed(() => tab.value === "open" && !userPersonId.value);

const emptyText = computed(() => {
  if (tab.value === "open") return "No open tickets are assigned to you.";
  if (tab.value === "activity") return "No activity yet. What you record on tickets shows here.";
  return raisedState.value === "all" ? "No tickets raised by you or for you." : "No tickets match this filter.";
});
</script>

<template>
  <div class="py-3">
    <ul class="nav nav-tabs nav-fill mb-3">
      <li v-for="[key, text] in TABS" :key="key" class="nav-item">
        <button
          type="button"
          class="nav-link w-100 px-1"
          :class="{ active: tab === key }"
          :aria-current="tab === key ? 'page' : undefined"
          @click="chooseTab(key)"
        >{{ text }}</button>
      </li>
    </ul>

    <div v-if="tab === 'raised'" class="mb-3">
      <select v-model="stateModel" class="form-select w-auto" aria-label="State">
        <option v-for="[value, text] in RAISED_STATES" :key="value" :value="value">{{ text }}</option>
      </select>
    </div>

    <div v-if="loading && page" class="text-secondary small mb-1">Loading…</div>
    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger" @click="load">Retry</button>
    </div>
    <div v-else-if="loading && !page" class="text-secondary">Loading…</div>
    <div v-else-if="noUnits" class="text-secondary">{{ NO_UNITS_TEXT }}</div>
    <template v-else-if="page">
      <div v-if="page.total > 0 && countText" class="text-secondary small mb-2">{{ countText }}</div>
      <div v-if="page.total === 0 && notInTeam" class="text-secondary">
        <template v-if="isItAdmin">You are not in Team. Add yourself in Masters › Team to be assigned tickets.</template>
        <template v-else>You are not in Team. Ask IT admin to add you.</template>
      </div>
      <div v-else-if="page.total === 0" class="text-secondary">{{ emptyText }}</div>
      <div v-else-if="page.items.length === 0" class="text-secondary">Nothing on this page.</div>
      <div v-else-if="tab === 'activity'" class="list-group">
        <router-link
          v-for="item in page.items"
          :key="item.id"
          :to="`/tickets/${item.ticket.id}`"
          class="list-group-item list-group-item-action"
        >
          <div class="d-flex flex-wrap align-items-center gap-2">
            <span class="small text-secondary">{{ formatDateTime(item.created_at) }}</span>
            <span class="fw-semibold">{{ EVENT_LABELS[item.event] ?? item.event }}</span>
            <span>{{ item.ticket.serial }}</span>
            <IntensityBadge :intensity="item.ticket.intensity" />
            <span v-if="isBackdated(item)" class="small text-secondary">· happened {{ formatDateTime(item.occurred_at) }}</span>
          </div>
          <div class="mt-1 activity-text">{{ item.ticket.machine.code }} — {{ item.ticket.machine.name }}</div>
          <div v-if="activityDetail(item)" class="small text-secondary activity-text">{{ activityDetail(item) }}</div>
        </router-link>
      </div>
      <div v-else class="list-group">
        <TicketRow v-for="t in page.items" :key="t.id" :ticket="t" :now="now" />
      </div>
    </template>
    <PagerBar
      v-if="page && !loadError && !noUnits"
      :page="pageNumber"
      :total="page.total"
      :per-page="PAGE_SIZE"
      @page="choosePage"
    />
  </div>
</template>

<style scoped>
.activity-text {
  overflow-wrap: anywhere;
}
</style>
