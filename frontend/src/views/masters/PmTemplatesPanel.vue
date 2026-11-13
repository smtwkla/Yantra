<script setup>
/**
 * Masters › PM templates (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.10, mock-up 09): the plant's PM
 * standards, written once and attached to machines (TPM: one standard, improved in one place). Each row: the name,
 * the trigger in words, the item count and the machines it is on (BR1-14: the linked plans); a row opens the
 * template page. *Add PM template* for holders of pm_plan:edit anywhere (`can_add`). Inactive templates sit folded
 * below, for every reader (history, not a secret). One request (BR1-19).
 */
import { onMounted, ref } from "vue";
import { apiGet } from "../../api";
import { templateRowText } from "../../utils/pmLabels";

const list = ref(null); // {items, inactive, can_add}
const loadError = ref("");
const showInactive = ref(false);

async function load() {
  loadError.value = "";
  try {
    list.value = await apiGet("/api/pm/templates");
  } catch (err) {
    loadError.value = err.message;
  }
}

onMounted(load);
</script>

<template>
  <div>
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
      <h5 class="mb-0">PM templates</h5>
      <router-link v-if="list?.can_add" to="/masters/pm-templates/new" class="btn btn-primary tap-target">
        <i class="fa-solid fa-plus me-1"></i>Add PM template
      </router-link>
    </div>
    <div v-if="loadError" class="alert alert-danger d-flex justify-content-between align-items-center">
      <span>{{ loadError }}</span>
      <button class="btn btn-outline-danger tap-target" @click="load">Retry</button>
    </div>
    <div v-else-if="!list" class="text-secondary">Loading…</div>
    <template v-else>
      <div v-if="list.items.length === 0" class="text-secondary mb-3" data-testid="pm-templates-empty">
        {{ list.can_add ? "No PM templates yet. Add one to start planned maintenance." : "No PM templates yet." }}
      </div>
      <div v-else class="list-group mb-3" data-testid="pm-templates">
        <router-link
          v-for="t in list.items"
          :key="t.id"
          :to="`/masters/pm-templates/${t.id}`"
          class="list-group-item list-group-item-action template-row"
          :data-template="t.name"
        >
          <span class="d-block fw-semibold">{{ t.name }}</span>
          <span class="d-block small text-secondary">{{ templateRowText(t) }}</span>
        </router-link>
      </div>
      <template v-if="list.inactive.length">
        <button type="button" class="btn btn-link p-0 tap-target mb-2" :aria-expanded="showInactive" @click="showInactive = !showInactive">
          Inactive templates ({{ list.inactive.length }})
        </button>
        <div v-if="showInactive" class="list-group" data-testid="pm-templates-inactive">
          <router-link
            v-for="t in list.inactive"
            :key="t.id"
            :to="`/masters/pm-templates/${t.id}`"
            class="list-group-item list-group-item-action template-row text-secondary"
            :data-template="t.name"
          >
            <span class="d-block fw-semibold">{{ t.name }} <span class="badge text-bg-secondary ms-1">Inactive</span></span>
            <span class="d-block small">{{ templateRowText(t) }}</span>
          </router-link>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.template-row {
  overflow-wrap: anywhere;
}
</style>
