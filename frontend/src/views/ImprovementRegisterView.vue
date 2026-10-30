<script setup>
/**
 * Improvement register, the print page for the management review
 * (docs/steps/S076-improvement-register/1-brief.md § 5.8; ISO 9001 § 9.3, § 10.3): one site and
 * one period on A4 portrait. Opened in a new tab from the Improvements list. The site and the
 * period live in the link (router.replace), so a reload, Back and a shared link keep them; after
 * the first load the link carries both ends of the period.
 */
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import { formatDate, formatDateTime } from "../utils/datetime";
import { actionKindLabel, improvementStateLabel } from "../utils/improvementLabels";
import { actionsText, AGE_BAND_LABELS, monthPeriod, periodText, workedShareText } from "../utils/improvementRegister";
import { NO_UNITS_TEXT } from "../utils/messages";

const BAND_KEYS = Object.keys(AGE_BAND_LABELS);

const route = useRoute();
const router = useRouter();

const result = ref(null); // the last register that loaded; a 400 leaves it as it is
const loading = ref(false);
const loadError = ref(""); // 503 or no connection: shown with Retry
const periodError = ref(""); // a 400 on the period: under the fields
const forbidden = ref(false);
const notAvailable = ref(false); // 404: the site is no longer one of the user's
let loadSeq = 0;
let writtenPath = null; // the address this page wrote itself, so its own change does not load again

const fromValue = ref("");
const toValue = ref("");
const siteValue = ref("");

function readQuery() {
  fromValue.value = route.query.from ?? "";
  toValue.value = route.query.to ?? "";
  siteValue.value = route.query.site_id ?? "";
}

function loadUrl() {
  const params = new URLSearchParams();
  for (const key of ["site_id", "from", "to"]) {
    if (route.query[key]) params.set(key, route.query[key]);
  }
  const text = params.toString();
  return `/api/improvements/register${text ? `?${text}` : ""}`;
}

function go(changes) {
  const query = { ...route.query, ...changes };
  for (const key of Object.keys(query)) {
    if (query[key] === "" || query[key] === null || query[key] === undefined) delete query[key];
  }
  router.replace({ query });
}

async function load() {
  if (route.name !== "improvement-register") return; // the route is changing to another page
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  periodError.value = "";
  forbidden.value = false;
  notAvailable.value = false;
  try {
    const data = await apiGet(loadUrl());
    if (seq !== loadSeq) return;
    result.value = data;
    // Write both ends of the period into the link (BR1-02), once, without loading again
    if (route.query.from !== data.period.from || route.query.to !== data.period.to) {
      const query = { ...route.query, from: data.period.from, to: data.period.to };
      writtenPath = router.resolve({ query }).fullPath;
      router.replace({ query });
    }
    // The fields show the period and site the register answered for (the link is only written above)
    fromValue.value = data.period.from;
    toValue.value = data.period.to;
    siteValue.value = data.site ? String(data.site.id) : "";
  } catch (err) {
    if (seq !== loadSeq) return;
    if (err.status === 400) {
      periodError.value = err.message; // the register on screen stays
    } else if (err.status === 403) {
      forbidden.value = true;
      result.value = null;
    } else if (err.status === 404) {
      notAvailable.value = true;
      result.value = null;
    } else {
      loadError.value = err.message;
      result.value = null;
    }
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

function applyDates() {
  go({ from: fromValue.value, to: toValue.value });
}

// The IST date from the clock, for a page that has no register yet (a refused period from a link);
// plain UTC arithmetic, so the browser's zone does not matter
const istToday = () => new Date(Date.now() + 5.5 * 3600 * 1000).toISOString().slice(0, 10);

function showMonth(monthsBack) {
  const period = monthPeriod(result.value?.today ?? istToday(), monthsBack);
  go(period);
}

function chooseSite() {
  go({ site_id: siteValue.value });
}

function showFirstSite() {
  go({ site_id: "" });
}

const showSites = computed(() => (result.value?.sites.length ?? 0) > 1);
const hasSite = computed(() => Boolean(result.value?.site));
const noUnits = computed(() => result.value !== null && !result.value.site);
const printedOn = computed(() => formatDateTime(result.value?.printed_at));
const machineText = (machine) => `${machine.code} ${machine.name}`;
const closedByText = (item) => (item.by_lead ? `${item.closed_by_name}, the lead` : item.closed_by_name);
const stateText = improvementStateLabel;
const bandRows = computed(() => result.value.open.by_state);
const improvementPath = (id) => `/tickets/improvements/${id}`;

// A4 portrait, only while this page is open (as the asset list): a global @page rule would also
// set the paper of every other page the user prints.
let pageStyle = null;
onMounted(() => {
  pageStyle = document.createElement("style");
  pageStyle.textContent = "@page { size: A4 portrait; margin: 12mm; }";
  document.head.appendChild(pageStyle);
  readQuery();
  load();
});
onUnmounted(() => pageStyle?.remove());
watch(
  () => route.fullPath,
  (path) => {
    if (path === writtenPath) {
      writtenPath = null;
      return;
    }
    readQuery();
    load();
  }
);

function print() {
  window.print();
}
</script>

<template>
  <div class="register-page">
    <div v-if="!forbidden && !noUnits" class="no-print mb-3">
      <div class="d-flex flex-wrap align-items-end gap-2 mb-2">
        <div v-if="showSites">
          <label class="form-label small mb-0" for="ir-site">Site</label>
          <select id="ir-site" v-model="siteValue" class="form-select form-select-sm" @change="chooseSite">
            <option v-for="s in result.sites" :key="s.id" :value="String(s.id)">{{ s.code }} — {{ s.name }}</option>
          </select>
        </div>
        <div>
          <label class="form-label small mb-0" for="ir-from">From</label>
          <input id="ir-from" v-model="fromValue" class="form-control form-control-sm" type="date" @change="applyDates" />
        </div>
        <div>
          <label class="form-label small mb-0" for="ir-to">To</label>
          <input id="ir-to" v-model="toValue" class="form-control form-control-sm" type="date" @change="applyDates" />
        </div>
        <button class="btn btn-sm btn-outline-primary" @click="showMonth(0)">Show this month</button>
        <button class="btn btn-sm btn-outline-primary" @click="showMonth(1)">Show last month</button>
        <button v-if="hasSite" class="btn btn-sm btn-primary ms-auto" @click="print">
          <i class="fa-solid fa-print me-1"></i>Print
        </button>
      </div>
      <div v-if="periodError" class="text-danger small mb-2" role="alert">{{ periodError }}</div>
      <div class="alert alert-info small mb-0">
        Print in <strong>portrait</strong>, at <strong>100 %</strong> (“Actual size”).
      </div>
    </div>

    <div v-if="forbidden" class="alert alert-warning no-print">You can't see the register.</div>
    <div v-else-if="notAvailable" class="alert alert-warning d-flex justify-content-between align-items-center no-print">
      <span>This site is not available.</span>
      <button class="btn btn-sm btn-outline-secondary" @click="showFirstSite">Show my first site</button>
    </div>
    <div v-else-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center no-print">
      <span>{{ loadError }}</span>
      <button class="btn btn-sm btn-outline-danger" @click="load">Retry</button>
    </div>
    <div v-else-if="loading && !result" class="text-secondary no-print">Loading…</div>
    <div v-else-if="noUnits" class="text-secondary no-print">{{ NO_UNITS_TEXT }}</div>

    <article v-else-if="result" class="sheet" :class="{ loading }">
      <header class="sheet-header">
        <h1>Improvement register</h1>
        <div class="header-line">{{ result.site.code }} — {{ result.site.name }}</div>
        <div class="header-line">{{ periodText(result.period) }}</div>
        <div v-if="result.units" class="header-line">Units: {{ result.units.join(", ") }}</div>
        <div class="header-line">Printed on {{ printedOn }} by {{ result.printed_by }}</div>
      </header>

      <section>
        <h2>Started in the period ({{ result.started.count }})</h2>
        <p v-if="result.started.count === 0" class="empty">No improvement was started in this period.</p>
        <div v-else class="table-scroll">
          <table class="register started">
            <colgroup>
              <col style="width: 24mm" /><col style="width: 18mm" /><col style="width: 34mm" /><col /><col style="width: 24mm" /><col style="width: 26mm" />
            </colgroup>
            <thead>
              <tr><th>Serial</th><th>Started</th><th>Machine</th><th>Title</th><th>Lead</th><th>State now</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in result.started.items" :key="item.id">
                <td class="serial"><router-link :to="improvementPath(item.id)">{{ item.serial }}</router-link></td>
                <td>{{ formatDate(item.started_at) }}</td>
                <td>{{ machineText(item.machine) }}</td>
                <td>
                  {{ item.title }}
                  <div v-if="item.follow_up_of" class="note">Follow-up of {{ item.follow_up_of.serial }}</div>
                </td>
                <td>{{ item.lead_name }}</td>
                <td>{{ stateText(item.state) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2>Open now ({{ result.open.count }})</h2>
        <div class="table-scroll">
          <table class="register counts">
            <thead>
              <tr>
                <th></th>
                <th v-for="band in BAND_KEYS" :key="band">{{ AGE_BAND_LABELS[band] }}</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in bandRows" :key="row.state">
                <th class="row-head">{{ stateText(row.state) }}</th>
                <td v-for="band in BAND_KEYS" :key="band" class="num">{{ row.bands[band] }}</td>
                <td class="num total">{{ row.total }}</td>
              </tr>
              <tr class="totals">
                <th class="row-head">Total</th>
                <td v-for="band in BAND_KEYS" :key="band" class="num">{{ result.open.band_totals[band] }}</td>
                <td class="num total">{{ result.open.count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="result.open.count === 0" class="empty">No open improvements.</p>
        <div v-else class="table-scroll">
          <table class="register open-list">
            <colgroup>
              <col style="width: 24mm" /><col style="width: 11mm" /><col style="width: 30mm" /><col /><col style="width: 22mm" /><col style="width: 22mm" /><col style="width: 24mm" />
            </colgroup>
            <thead>
              <tr><th>Serial</th><th>Age (days)</th><th>Machine</th><th>Title</th><th>Lead</th><th>State</th><th>Countermeasures</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in result.open.items" :key="item.id">
                <td class="serial"><router-link :to="improvementPath(item.id)">{{ item.serial }}</router-link></td>
                <td class="num">{{ item.age_days }}</td>
                <td>{{ machineText(item.machine) }}</td>
                <td>{{ item.title }}</td>
                <td>{{ item.lead_name }}</td>
                <td>{{ stateText(item.state) }}</td>
                <td>{{ actionsText(item) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2>Countermeasures overdue now ({{ result.overdue.count }})</h2>
        <p v-if="result.overdue.count === 0" class="empty">No countermeasure is overdue.</p>
        <div v-else class="table-scroll">
          <table class="register overdue">
            <colgroup>
              <col style="width: 30mm" /><col style="width: 20mm" /><col /><col style="width: 24mm" /><col style="width: 18mm" /><col style="width: 13mm" />
            </colgroup>
            <thead>
              <tr><th>Improvement</th><th>Kind</th><th>What will be done</th><th>Owner</th><th>Due</th><th>Days late</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in result.overdue.items" :key="item.id">
                <td>
                  <router-link :to="improvementPath(item.improvement.id)" class="serial">{{ item.improvement.serial }}</router-link>
                  <div class="note">{{ item.improvement.title }}</div>
                </td>
                <td>{{ actionKindLabel(item.kind) }}</td>
                <td>{{ item.text }}</td>
                <td>{{ item.owner_name }}</td>
                <td>{{ formatDate(item.due_date) }}</td>
                <td class="num">{{ item.overdue_days }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2>Closed in the period</h2>
        <p class="count-line">{{ workedShareText(result.closed) }}</p>
        <p v-if="result.closed.items.length === 0" class="empty">No improvement was closed in this period.</p>
        <div v-else class="table-scroll">
          <table class="register closed">
            <colgroup>
              <col style="width: 24mm" /><col style="width: 17mm" /><col style="width: 20mm" /><col style="width: 26mm" /><col style="width: 19mm" /><col style="width: 21mm" /><col /><col style="width: 24mm" />
            </colgroup>
            <thead>
              <tr><th>Serial</th><th>Closed</th><th>Machine</th><th>Title</th><th>Result</th><th>Closed by</th><th>Remark</th><th>Follow-up</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in result.closed.items" :key="item.id">
                <td class="serial"><router-link :to="improvementPath(item.id)">{{ item.serial }}</router-link></td>
                <td>{{ formatDate(item.closed_at) }}</td>
                <td>{{ machineText(item.machine) }}</td>
                <td>{{ item.title }}</td>
                <td>{{ stateText(item.state) }}</td>
                <td>{{ closedByText(item) }}</td>
                <td>{{ item.remark }}</td>
                <td class="serial">{{ item.follow_up?.serial ?? "" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <footer class="review-lines">
        <div class="line"><span>Reviewed by</span><span class="blank"></span></div>
        <div class="line"><span>Date</span><span class="blank"></span></div>
        <div class="line tall"><span>Decisions and actions</span><span class="blank"></span></div>
      </footer>
    </article>
  </div>
</template>

<style scoped>
.register-page {
  padding-top: 1rem;
}

.sheet.loading {
  opacity: 0.5;
}

.sheet {
  max-width: 186mm; /* A4 less the 12 mm margins */
  margin: 0 auto 2rem;
  font-size: 9pt;
  color: #000;
}

.sheet-header h1 {
  font-size: 14pt;
  margin: 0 0 1mm;
}

.header-line {
  font-size: 9pt;
  color: #444;
}

h2 {
  font-size: 11pt;
  margin: 6mm 0 2mm;
}

.empty,
.count-line {
  margin: 0 0 2mm;
}

.count-line {
  font-weight: 700;
}

.table-scroll {
  overflow-x: auto; /* a phone scrolls the table, never the page */
  margin-bottom: 2mm;
}

.register {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  min-width: 150mm;
}

.register.counts {
  min-width: 0;
}

.register th,
.register td {
  border: 0.2mm solid #888;
  padding: 0.8mm 1.2mm;
  vertical-align: top;
  overflow-wrap: anywhere;
}

.register th {
  background: #eee;
  text-align: left;
}

.register .row-head {
  background: #f6f6f6;
}

.register .num {
  text-align: right;
}

.register .total,
.register .totals {
  font-weight: 700;
}

.register .serial,
.register .serial a {
  font-weight: 700;
  white-space: nowrap;
}

.register tr {
  break-inside: avoid;
}

.note {
  font-size: 7.5pt;
  color: #555;
}

.register a {
  color: inherit;
}

.review-lines {
  margin-top: 10mm;
  display: grid;
  gap: 6mm;
  break-inside: avoid;
}

.line {
  display: flex;
  align-items: flex-end;
  gap: 3mm;
}

.line .blank {
  flex: 1;
  border-bottom: 0.3mm solid #000;
  min-height: 7mm;
}

.line.tall .blank {
  min-height: 24mm;
}

@media print {
  .register-page {
    padding: 0;
  }

  .sheet {
    max-width: none;
    margin: 0;
  }

  .table-scroll {
    overflow: visible;
  }

  .register {
    min-width: 0;
  }

  /* The link is plain text on paper */
  .register a {
    text-decoration: none;
  }

  /* Chrome and Edge repeat the header on each printed page */
  thead {
    display: table-header-group;
  }
}
</style>
