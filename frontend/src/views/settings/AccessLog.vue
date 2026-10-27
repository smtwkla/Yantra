<script setup>
/**
 * Access log card on the Settings page (docs/steps/S013-network-gate-access-log/1-brief.md § 5.4).
 * For access_log:view: who reached the API, from which address, and the refusals. One row per
 * sighting (a login session seen from a new address, or a refusal), not per request.
 * Read-only: nothing here changes the log (ISO 27001 A.8.15). Filters are local state.
 */
import { onMounted, ref, watch } from "vue";
import { apiGet } from "../../api";
import PagerBar from "../../components/PagerBar.vue";
import { useDebounced } from "../../composables/useDebounced";
import { formatDateTime } from "../../utils/datetime";
import { displayRoleLabel } from "../../utils/siteRoles";

const PAGE_SIZE = 50; // sent explicitly, so the pager and the request agree if the API default changes

const OUTCOME_LABELS = {
  ok: { text: "Allowed", badge: "text-bg-success" },
  auth_failed: { text: "Login failed", badge: "text-bg-warning" },
  denied_network: { text: "Refused: network", badge: "text-bg-danger" },
  denied_perm: { text: "Refused: permission", badge: "text-bg-secondary" },
};

// A refusal by permission logs the key it needed (auth_utils._log_denied); a business refusal its
// own text, shown as it is (S064 UX-26)
const PERMISSION_KEY = /^[a-z_]+:[a-z_]+$/;
const detailText = (detail) => (PERMISSION_KEY.test(detail) ? `Needed: ${detail}` : detail);

const result = ref(null); // {items, total, page, per_page}
const loading = ref(false);
const loadError = ref("");
const pageNumber = ref(1);
const userText = ref("");
const dateFrom = ref(""); // YYYY-MM-DD from <input type="date">, accepted by the API
const dateTo = ref("");
const externalOnly = ref(false);
const refusalsOnly = ref(false);
let loadSeq = 0;

function listPath() {
  const params = new URLSearchParams({ page: String(pageNumber.value), per_page: String(PAGE_SIZE) });
  if (userText.value.trim()) params.set("user", userText.value.trim());
  if (dateFrom.value) params.set("from", dateFrom.value);
  if (dateTo.value) params.set("to", dateTo.value);
  if (externalOnly.value) params.set("external", "1");
  if (refusalsOnly.value) params.set("denied", "1");
  return `/api/settings/access-log?${params}`;
}

async function load() {
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const loaded = await apiGet(listPath());
    if (seq === loadSeq) result.value = loaded;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

function restart() {
  pageNumber.value = 1;
  load();
}

const { schedule: scheduleSearch } = useDebounced(restart);
watch(userText, scheduleSearch);
watch([dateFrom, dateTo, externalOnly, refusalsOnly], restart);

function goToPage(page) {
  pageNumber.value = page;
  load();
}

const outcome = (item) => OUTCOME_LABELS[item.outcome] ?? { text: item.outcome, badge: "text-bg-light" };

onMounted(load);
</script>

<template>
  <div class="card mt-3">
    <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
      <span>
        <i class="fa-solid fa-list-check me-2"></i>Access log
        <span v-if="result" class="text-secondary small">({{ result.total }})</span>
      </span>
      <button class="btn btn-sm btn-outline-secondary" :disabled="loading" title="Refresh" @click="load">
        <i class="fa-solid fa-rotate" :class="{ 'fa-spin': loading }"></i>
      </button>
    </div>
    <div class="card-body">
      <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
        <input
          v-model="userText"
          type="search"
          class="form-control form-control-sm log-user"
          placeholder="User…"
          aria-label="User"
        />
        <input v-model="dateFrom" type="date" class="form-control form-control-sm log-date" aria-label="From" />
        <span class="small text-secondary">to</span>
        <input v-model="dateTo" type="date" class="form-control form-control-sm log-date" aria-label="To" />
        <div class="form-check form-check-inline mb-0 ms-1">
          <input id="log-external" v-model="externalOnly" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="log-external">External only</label>
        </div>
        <div class="form-check form-check-inline mb-0">
          <input id="log-denied" v-model="refusalsOnly" class="form-check-input" type="checkbox" />
          <label class="form-check-label small" for="log-denied">Refusals only</label>
        </div>
      </div>
      <div class="form-text mt-0 mb-2">
        One line each time a login session is seen from a new address, and once per refusal. Kept for 365 days.
      </div>

      <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center mb-0">
        <span>The access log could not be loaded: {{ loadError }}</span>
        <button class="btn btn-sm btn-outline-danger" @click="load()">Retry</button>
      </div>
      <div v-else-if="!result" class="text-secondary">Loading…</div>
      <template v-else>
        <div v-if="result.total === 0" class="text-secondary">No entries match.</div>
        <div v-else-if="result.items.length === 0" class="text-secondary">No entries on this page.</div>
        <div v-else class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead>
              <tr>
                <th>When</th>
                <th>User</th>
                <th>Address</th>
                <th>Outcome</th>
                <th>Request</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in result.items" :key="item.id">
                <td class="text-nowrap">{{ formatDateTime(item.ts) }}</td>
                <td>
                  <span v-if="item.username">{{ item.username }}</span>
                  <span v-else class="text-secondary">—</span>
                  <div v-if="item.role" class="small text-secondary">{{ displayRoleLabel(item.role) }}</div>
                </td>
                <td class="text-nowrap">
                  {{ item.client_ip || "unknown" }}
                  <div class="small" :class="item.is_internal ? 'text-secondary' : 'text-warning-emphasis'">
                    {{ item.is_internal ? "plant network" : "external" }}
                  </div>
                </td>
                <td>
                  <span class="badge" :class="outcome(item).badge">{{ outcome(item).text }}</span>
                  <div v-if="item.detail" class="small text-secondary text-break">{{ detailText(item.detail) }}</div>
                </td>
                <td class="text-break">
                  <span class="small">{{ item.method }} {{ item.path }}</span>
                  <div v-if="item.user_agent" class="small text-secondary log-agent" :title="item.user_agent">
                    {{ item.user_agent }}
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <PagerBar :page="result.page" :total="result.total" :per-page="result.per_page" @page="goToPage" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.log-user {
  width: 12rem;
  max-width: 100%;
}
.log-date {
  width: auto;
}
.log-agent {
  max-width: 22rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
