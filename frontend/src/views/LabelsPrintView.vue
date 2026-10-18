<script setup>
/**
 * QR label sheets (docs/steps/S014-qr-labels/1-brief.md § 3): A4, 3 × 5 labels of 52 mm, thin
 * grey cut lines, printed by the browser at 100 %. Opened in a new tab from the equipment list
 * or page with the ids in the query, so it survives a reload.
 *
 * The QR SVG comes from the backend and is inserted with v-html. That is safe here: it is path
 * data only, built from a validated address setting and a validated code — no database text is
 * in it. The code, site and name are ordinary text bindings.
 */
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { apiPost } from "../api";
import { chunkSheets, parseLabelQuery } from "../utils/labelSheets";

const route = useRoute();

const labels = ref(null);
const loading = ref(false);
const loadError = ref("");
const request = computed(() => parseLabelQuery(route.query));
const sheets = computed(() => chunkSheets(labels.value ?? []));

async function load() {
  if (!request.value) return;
  loading.value = true;
  loadError.value = "";
  try {
    const result = await apiPost("/api/equipment/labels", {
      ids: request.value.ids,
      with_parts: request.value.withParts,
    });
    labels.value = result.labels;
  } catch (err) {
    labels.value = null;
    loadError.value = err.message; // 400 (too many, bad list) and 404 carry the server's message
  } finally {
    loading.value = false;
  }
}

// A4 with no page margin, only while this page is open: a global @page rule in the bundle would
// also take the margins off every other page the user prints
let pageStyle = null;
onMounted(() => {
  pageStyle = document.createElement("style");
  pageStyle.textContent = "@page { size: A4; margin: 0; }";
  document.head.appendChild(pageStyle);
  load();
});
onUnmounted(() => pageStyle?.remove());

function print() {
  window.print();
}
</script>

<template>
  <div class="labels-page">
    <div class="no-print mb-3">
      <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
        <span v-if="labels" class="text-secondary">
          {{ labels.length }} {{ labels.length === 1 ? "label" : "labels" }} on {{ sheets.length }}
          {{ sheets.length === 1 ? "sheet" : "sheets" }}
        </span>
        <button v-if="labels && labels.length" class="btn btn-sm btn-primary ms-auto" @click="print">
          <i class="fa-solid fa-print me-1"></i>Print
        </button>
      </div>
      <div class="alert alert-info small mb-0">
        Print at <strong>100 %</strong> (“Actual size”), not “Fit to page”, on plain A4; turn off headers and
        footers. Checked in Chrome and Edge. Measure one square with a ruler: it should be 52 mm.
      </div>
    </div>

    <div v-if="!request" class="alert alert-warning no-print">This link names no equipment to print.</div>
    <div v-else-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center no-print">
      <span>{{ loadError }}</span>
      <button class="btn btn-sm btn-outline-danger" @click="load">Retry</button>
    </div>
    <div v-else-if="loading" class="text-secondary no-print">Loading…</div>

    <div v-else-if="labels" class="sheets">
      <div v-for="(sheet, s) in sheets" :key="s" class="sheet">
        <div v-for="label in sheet" :key="label.id" class="label">
          <div class="qr" v-html="label.qr_svg"></div>
          <div class="label-line">
            <span class="label-code">{{ label.code }}</span>
            <span class="label-site">{{ label.site_code }}</span>
          </div>
          <div class="label-name">{{ label.name }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.labels-page {
  padding-top: 1rem;
}

.sheets {
  overflow-x: auto;
}

/* One A4 page: the 3 × 5 grid of 52 mm centred, 27 mm at the sides, 18.5 mm top and bottom */
.sheet {
  width: 210mm;
  height: 297mm;
  padding: 18.5mm 27mm;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: repeat(3, 52mm);
  grid-auto-rows: 52mm;
  align-content: start;
  overflow: hidden;
  background: #fff;
  break-after: page;
  margin-bottom: 1rem;
  box-shadow: 0 0 0.5rem rgba(0, 0, 0, 0.2);
}

.sheet:last-child {
  break-after: auto;
}

/* The grey border is inside the 52 mm box (border-box), so the pitch stays 52 mm: it is the cut line */
.label {
  width: 52mm;
  height: 52mm;
  box-sizing: border-box;
  border: 0.2mm solid #bbb;
  padding: 1.5mm 2mm 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
  color: #000;
}

/* The QR with its own 4-module white margin (quiet zone) */
.qr {
  width: 38mm;
  height: 38mm;
  flex: none;
}

.qr :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}

.label-line {
  width: 100%;
  display: flex;
  align-items: baseline;
  gap: 1.5mm;
  margin-top: 0.8mm;
  line-height: 1.15;
}

/* Never cut: sized so 12 characters fit on the line */
.label-code {
  flex: none;
  font-weight: 700;
  font-size: 4.2mm;
  white-space: nowrap;
}

/* Takes the space left and is cut when long (site codes may be 20 characters) */
.label-site {
  flex: 1 1 auto;
  min-width: 0;
  text-align: right;
  font-size: 2.6mm;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.label-name {
  width: 100%;
  font-size: 2.6mm;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media print {
  .labels-page {
    padding: 0;
  }

  .sheets {
    overflow: visible;
  }

  .sheet {
    margin: 0;
    box-shadow: none;
  }
}
</style>
