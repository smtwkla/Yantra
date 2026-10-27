<script setup>
/**
 * Printable asset list (docs/steps/S015-asset-list/1-brief.md): one A4 portrait section per
 * unit, a plain register or a checklist to fill by hand. Opened in a new tab from the equipment
 * list with the filters and the two switches in the query, so it survives a reload.
 */
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet } from "../api";
import {
  ensureEquipmentClasses, ensureEquipmentTypes, ensureProperties, equipmentClasses, equipmentTypes, properties,
} from "../stores/masters";
import { filtersLabel, parseAssetListQuery } from "../utils/assetList";
import { formatDateTime } from "../utils/datetime";
import { LIFECYCLE_LABELS } from "../utils/equipmentLabels";

const route = useRoute();
const router = useRouter();

const result = ref(null);
const loading = ref(false);
const loadError = ref("");
let loadSeq = 0;

const parsed = computed(() => parseAssetListQuery(route.query));
const filterLine = computed(() =>
  filtersLabel(parsed.value.params, {
    classes: equipmentClasses.value, types: equipmentTypes.value, properties: properties.value,
  })
);
const printedOn = computed(() => formatDateTime(result.value?.printed_at));
const hasUnits = computed(() => (result.value?.units.length ?? 0) > 0);

async function load() {
  if (route.name !== "asset-list") return; // the route is changing to another page
  const seq = ++loadSeq;
  loading.value = true;
  loadError.value = "";
  try {
    const params = new URLSearchParams(parsed.value.params);
    if (parsed.value.withParts) params.set("with_parts", "1");
    const [data] = await Promise.all([
      apiGet(`/api/equipment/asset-list?${params}`), ensureEquipmentClasses(), ensureEquipmentTypes(),
      // The header names the property filter's properties; a plain print asks for nothing more (S062)
      parsed.value.params.props ? ensureProperties() : null,
    ]);
    if (seq === loadSeq) result.value = data;
  } catch (err) {
    if (seq === loadSeq) {
      result.value = null;
      loadError.value = err.message; // 400 (too many rows, bad filter) carries the server's message
    }
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

// The switches live in the link, so a reload and Back keep them
function setSwitch(key, on) {
  router.replace({ query: { ...route.query, [key]: on ? "1" : undefined } });
}

const classType = (row) => (row.type_name ? `${row.class_code} · ${row.type_name}` : row.class_code);
const lifecycleText = (row) => LIFECYCLE_LABELS[row.lifecycle] ?? row.lifecycle;
const detailLine = (row) =>
  [classType(row), row.model_label, row.serial_no, row.year, row.effective_criticality, lifecycleText(row)]
    .filter((v) => v !== null && v !== undefined && v !== "")
    .join(" · ");
const countLine = (unit) =>
  parsed.value.withParts ? `${unit.machine_count} equipment, ${unit.part_count} parts` : `${unit.machine_count} equipment`;
const indent = (row) => ({ paddingLeft: `${row.depth * 4}mm` });

// A4 portrait, only while this page is open: a global @page rule in the bundle would also set the
// paper of every other page the user prints. The 12 mm margin leaves room for the browser's own
// header and footer.
let pageStyle = null;
onMounted(() => {
  pageStyle = document.createElement("style");
  pageStyle.textContent = "@page { size: A4 portrait; margin: 12mm; }";
  document.head.appendChild(pageStyle);
  load();
});
onUnmounted(() => pageStyle?.remove());
watch(() => route.fullPath, load);

function print() {
  window.print();
}
</script>

<template>
  <div class="asset-list-page">
    <div class="no-print mb-3">
      <div class="d-flex flex-wrap align-items-center gap-3 mb-2">
        <div class="form-check form-switch mb-0">
          <input id="al-parts" :checked="parsed.withParts" class="form-check-input" type="checkbox"
                 @change="setSwitch('parts', $event.target.checked)" />
          <label class="form-check-label" for="al-parts">Include parts</label>
        </div>
        <div class="form-check form-switch mb-0">
          <input id="al-check" :checked="parsed.checklist" class="form-check-input" type="checkbox"
                 @change="setSwitch('check', $event.target.checked)" />
          <label class="form-check-label" for="al-check">Checklist columns</label>
        </div>
        <button v-if="hasUnits" class="btn btn-sm btn-primary ms-auto" @click="print">
          <i class="fa-solid fa-print me-1"></i>Print
        </button>
      </div>
      <div class="alert alert-info small mb-0">
        Print in <strong>portrait</strong>, at <strong>100 %</strong> (“Actual size”), not “Fit to page”.
      </div>
    </div>

    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center no-print">
      <span>{{ loadError }}</span>
      <button class="btn btn-sm btn-outline-danger" @click="load">Retry</button>
    </div>
    <div v-else-if="loading && !result" class="text-secondary no-print">Loading…</div>
    <div v-else-if="result && !hasUnits" class="text-secondary no-print">Nothing to list for these filters</div>

    <div v-else-if="result" class="sheets" :class="{ loading }">
      <section v-for="unit in result.units" :key="`${unit.site_code}.${unit.unit_code}`" class="unit-section">
        <header class="unit-header">
          <h1>{{ unit.site_code }} {{ unit.site_name }}</h1>
          <h2>{{ unit.site_code }}.{{ unit.unit_code }} {{ unit.unit_name }}</h2>
          <div class="header-line">{{ filterLine }}</div>
          <div class="header-line">Printed on {{ printedOn }} by {{ result.printed_by }}</div>
        </header>

        <table v-if="!parsed.checklist" class="register">
          <colgroup>
            <col style="width: 6mm" /><col style="width: 21mm" /><col /><col style="width: 26mm" />
            <col style="width: 28mm" /><col style="width: 20mm" /><col style="width: 9mm" />
            <col style="width: 12mm" /><col style="width: 16mm" />
          </colgroup>
          <thead>
            <tr>
              <th>#</th><th>Code</th><th>Name</th><th>Class · Type</th><th>Model</th><th>Serial no.</th>
              <th>Year</th><th>Crit.</th><th>Lifecycle</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in unit.rows" :key="row.id" :class="{ part: row.depth > 0 }">
              <td>{{ row.number }}</td>
              <td class="code">{{ row.code }}</td>
              <td :style="indent(row)">{{ row.name }}</td>
              <td>{{ classType(row) }}</td>
              <td>{{ row.model_label ?? "—" }}</td>
              <td>{{ row.serial_no }}</td>
              <td>{{ row.year }}</td>
              <td>{{ row.effective_criticality }}</td>
              <td>{{ lifecycleText(row) }}</td>
            </tr>
          </tbody>
        </table>

        <table v-else class="register checklist">
          <colgroup>
            <col style="width: 7mm" /><col style="width: 22mm" /><col /><col style="width: 14mm" /><col style="width: 62mm" />
          </colgroup>
          <thead>
            <tr><th>#</th><th>Code</th><th>Name</th><th>Found</th><th>Remarks</th></tr>
          </thead>
          <tbody v-for="row in unit.rows" :key="row.id" class="item" :class="{ part: row.depth > 0 }">
            <tr>
              <td>{{ row.number }}</td>
              <td class="code">{{ row.code }}</td>
              <td :style="indent(row)">{{ row.name }}</td>
              <td class="found" rowspan="2"><span class="box"></span></td>
              <td class="remarks" rowspan="2"></td>
            </tr>
            <tr>
              <td colspan="3" class="detail" :style="indent(row)">{{ detailLine(row) }}</td>
            </tr>
          </tbody>
        </table>

        <div class="count-line">{{ countLine(unit) }}</div>

        <div v-if="parsed.checklist" class="signatures">
          <div>Checked by ____________________ Date ____________ Signature ____________________</div>
          <div>Verified by (accounts) ____________________ Date ____________ Signature ____________________</div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.asset-list-page {
  padding-top: 1rem;
}

.sheets.loading {
  opacity: 0.5;
}

.unit-section {
  max-width: 186mm; /* A4 less the 12 mm margins */
  margin: 0 auto 2rem;
  font-size: 9pt;
  color: #000;
}

.unit-header h1 {
  font-size: 13pt;
  margin: 0;
}

.unit-header h2 {
  font-size: 11pt;
  margin: 0 0 2mm;
}

.header-line {
  font-size: 9pt;
  color: #444;
}

.register {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  margin-top: 3mm;
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

.register .code {
  font-weight: 700;
  white-space: nowrap;
}

.register tr {
  break-inside: avoid;
}

/* Two lines per item: keep them together on a page */
.item {
  break-inside: avoid;
}

.part td {
  color: #222;
}

.detail {
  font-size: 7.5pt;
  color: #666;
}

.found {
  text-align: center;
  vertical-align: middle;
}

.box {
  display: inline-block;
  width: 4mm;
  height: 4mm;
  border: 0.3mm solid #000;
}

.remarks {
  min-width: 60mm;
}

.count-line {
  margin-top: 2mm;
  font-weight: 700;
}

.signatures {
  margin-top: 8mm;
  display: grid;
  gap: 6mm;
}

@media print {
  .asset-list-page {
    padding: 0;
  }

  .unit-section {
    max-width: none;
    margin: 0;
  }

  .unit-section + .unit-section {
    break-before: page;
  }

  /* Chrome and Edge repeat the header on each printed page */
  thead {
    display: table-header-group;
  }
}
</style>
