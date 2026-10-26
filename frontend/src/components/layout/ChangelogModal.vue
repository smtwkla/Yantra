<script setup>
/**
 * What changed in Yantra — the CHANGELOG.md text, built into the bundle (S048).
 *
 * Read-only, so a plain Bootstrap modal as PhotoViewer is, not FormModal. The parent calls
 * open() / close() through a template ref. The root is teleported to <body>: the sidebar is a
 * fixed element with its own stacking context, so a modal inside it would sit under
 * Bootstrap's backdrop.
 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Modal } from "bootstrap";
import { parseChangelog } from "../../utils/changelog";

const runningVersion = typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "?";
const versions = parseChangelog(typeof __APP_CHANGELOG__ !== "undefined" ? __APP_CHANGELOG__ : "");
const hasRunning = computed(() => versions.some((v) => v.version === runningVersion));

const el = ref(null);
let modal = null;

function open() {
  modal.show();
}

function close() {
  if (!modal) return Promise.resolve();
  return new Promise((resolve) => {
    el.value.addEventListener("hidden.bs.modal", () => resolve(), { once: true });
    modal.hide();
  });
}

onMounted(() => {
  modal = Modal.getOrCreateInstance(el.value);
});
onBeforeUnmount(() => {
  modal?.dispose();
});

defineExpose({ open, close });
</script>

<template>
  <Teleport to="body">
    <div ref="el" class="modal fade" tabindex="-1" aria-labelledby="changelog-title">
      <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 id="changelog-title" class="modal-title">What changed in Yantra</h5>
          </div>
          <div class="modal-body">
            <p v-if="!versions.length" class="mb-0">No changes are recorded yet.</p>
            <template v-else>
              <p v-if="!hasRunning" class="alert alert-warning py-2">No entry for v{{ runningVersion }} yet.</p>
              <section v-for="(entry, n) in versions" :key="`${n}-${entry.version}`" class="mb-3">
                <h6 class="d-flex align-items-center gap-2">
                  <span>v{{ entry.version }}<template v-if="entry.date"> — {{ entry.date }}</template></span>
                  <span v-if="entry.version === runningVersion" class="badge text-bg-primary">This version</span>
                </h6>
                <ul v-if="entry.items.length" class="mb-0">
                  <li v-for="(item, i) in entry.items" :key="i">{{ item }}</li>
                </ul>
                <p v-else class="text-secondary mb-0">No notes were written for this version.</p>
              </section>
            </template>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
