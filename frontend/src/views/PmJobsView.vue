<script setup>
/**
 * The PM list (docs/steps/S097-pm-jobs-due/1-brief.md § 5.9; R03.3): the open PM jobs at the user's units,
 * on two tabs, *Due* (Due and Overdue, the overdue first) and *Upcoming* (Upcoming and Not yet due). The
 * standing is the server's, judged live from the job's due point and the meter's latest reading, so a reading
 * typed at 10:00 turns a job Due at once. The filters *Unit* and *Assigned to me* (a user with a Team record)
 * live in the URL query, as on the tickets list, so Back returns to the same list. No pager on Due and Upcoming:
 * one open job per active plan bounds the list.
 *
 * S098 § 5.9: a row (PmJobRow) opens the job page; a started job shows *In progress* and sits first on *Due*;
 * a third tab *Done* lists the done jobs, newest first, with the house pager.
 *
 * S099 § 5.7: a tab *To verify (n)* between *Upcoming* and *Done* lists the jobs waiting for an engineer's
 * verification, the oldest done first, paged as *Done*; *Done* lists only the finished jobs (verified, or final).
 *
 * S101 § 5.5: *Done* lists the skipped jobs too, by their skip time, and its count line says them apart
 * ("10 done · 2 skipped", `total_skipped`).
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import PagerBar from "../components/PagerBar.vue";
import PmJobRow from "../components/PmJobRow.vue";
import { userPersonId } from "../stores/auth";
import { ensureMyUnits, filterableUnits, myUnits, noUnits } from "../stores/equipment";
import { ensureUnits, units } from "../stores/masters";
import { NO_UNITS_TEXT } from "../utils/messages";
import { PAGED_TABS, PM_TABS, countText, jobsQuery } from "../utils/pmLabels";

const TAB_LABELS = { due: "Due", upcoming: "Upcoming", to_verify: "To verify", done: "Done" };

const route = useRoute();
const router = useRouter();

const answer = ref(null); // {items, counts} (+ total, page, per_page on Done)
const loading = ref(true);
const loadError = ref("");
let loadSeq = 0;

const query = computed(() => route.query);
const tab = computed(() => (PM_TABS.includes(query.value.tab) ? query.value.tab : "due"));
const pageNumber = computed(() => Math.max(1, Number.parseInt(query.value.page, 10) || 1));
const hasFilters = computed(() => Boolean(query.value.unit_id || query.value.assigned));

/** The query with ``changes`` merged; the default tab and empty values are left out of the URL. */
function merged(changes) {
  const next = { ...query.value, ...changes };
  for (const key of Object.keys(next)) {
    if (next[key] === null || next[key] === undefined || next[key] === "") delete next[key];
  }
  if (next.tab === "due") delete next.tab;
  if (!PAGED_TABS.includes(next.tab) || Number(next.page) <= 1) delete next.page;
  return next;
}

// A new filter or tab starts at page 1
const update = (changes) => router.replace({ query: merged({ page: null, ...changes }) });
const tabLink = (key) => ({ query: merged({ tab: key, page: null }) });
const choosePage = (value) => router.replace({ query: merged({ page: value }) });

const unitChoices = computed(() => (myUnits.value ? filterableUnits(units.value, myUnits.value) : []));
// v-model on a select re-syncs when its options arrive later (a plain :value would not)
const unitModel = computed({ get: () => query.value.unit_id ?? "", set: (value) => update({ unit_id: value }) });
const assignedToMe = computed({
  get: () => query.value.assigned === "me",
  set: (value) => update({ assigned: value ? "me" : null }),
});

// "To verify (3)" with the jobs waiting (counts.to_verify, on every tab), "To verify" at 0
const tabs = computed(() => PM_TABS.map((key) => {
  const waiting = key === "to_verify" ? answer.value?.counts?.to_verify : 0;
  return [key, waiting ? `${TAB_LABELS[key]} (${waiting})` : TAB_LABELS[key]];
}));
const counts = computed(() => (answer.value
  ? countText(tab.value, answer.value.counts, answer.value.total, answer.value.total_skipped) : ""));
const EMPTY_TEXTS = {
  due: "No PM jobs are due.", upcoming: "No PM jobs are coming up.",
  to_verify: "No PM jobs are waiting for verification.", done: "No PM jobs are done or skipped yet.",
};
const emptyText = computed(() => (hasFilters.value ? "No PM jobs match these filters." : EMPTY_TEXTS[tab.value]));

async function load() {
  if (route.name !== "pm") return; // the route is changing to another page
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const params = jobsQuery({ ...query.value, tab: tab.value });
    const [result] = await Promise.all([apiGet(`/api/pm/jobs${params ? `?${params}` : ""}`), ensureUnits(),
      ensureMyUnits()]);
    if (seq === loadSeq) answer.value = result;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

onMounted(load);
watch(() => route.fullPath, load);
</script>

<template>
  <div class="py-3">
    <ul class="nav nav-tabs nav-fill mb-3">
      <li v-for="[key, text] in tabs" :key="key" class="nav-item">
        <router-link
          :to="tabLink(key)"
          replace
          class="nav-link px-1"
          :class="{ active: tab === key }"
          :aria-current="tab === key ? 'page' : undefined"
        >{{ text }}</router-link>
      </li>
    </ul>
    <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
      <select v-model="unitModel" class="form-select w-auto mw-100" aria-label="Unit">
        <option value="">All my units</option>
        <option v-for="u in unitChoices" :key="u.id" :value="u.id">{{ u.full_code }}</option>
      </select>
      <div v-if="userPersonId" class="form-check mb-0">
        <input id="pm-assigned-me" v-model="assignedToMe" class="form-check-input" type="checkbox" />
        <label class="form-check-label" for="pm-assigned-me">Assigned to me</label>
      </div>
    </div>

    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center gap-2">
      <span>PM jobs could not be loaded: {{ loadError }}</span>
      <button type="button" class="btn btn-outline-danger" @click="load">Retry</button>
    </div>
    <div v-else-if="loading && !answer" class="text-secondary">Loading…</div>
    <div v-else-if="noUnits" class="text-secondary">{{ NO_UNITS_TEXT }}</div>
    <template v-else-if="answer">
      <div v-if="loading" class="text-secondary small mb-1">Loading…</div>
      <div v-if="counts" class="text-secondary small mb-2" data-testid="pm-counts">{{ counts }}</div>
      <div v-if="answer.items.length === 0" class="text-secondary">{{ emptyText }}</div>
      <div v-else class="list-group">
        <PmJobRow v-for="job in answer.items" :key="job.id" :job="job" />
      </div>
      <PagerBar
        v-if="PAGED_TABS.includes(tab) && answer.per_page"
        :page="pageNumber"
        :total="answer.total ?? 0"
        :per-page="answer.per_page"
        @page="choosePage"
      />
    </template>
  </div>
</template>
