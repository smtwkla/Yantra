<script setup>
/**
 * Settings — system status. Database card: reachability, server and schema version.
 */
import { computed, onMounted, ref } from "vue";
import { apiGet } from "../api";
import { formatDateTime } from "../utils/datetime";

const status = ref(null);
const loading = ref(false);
const loadError = ref("");

async function loadStatus() {
  loading.value = true;
  loadError.value = "";
  try {
    status.value = await apiGet("/api/settings/db-status");
  } catch (err) {
    loadError.value = err.message;
  } finally {
    loading.value = false;
  }
}

const schemaUpToDate = computed(
  () => status.value && status.value.schema_version === status.value.schema_latest,
);

onMounted(loadStatus);
</script>

<template>
  <div class="py-3">
    <div class="card db-card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span><i class="fa-solid fa-database me-2"></i>Database</span>
        <button class="btn btn-sm btn-outline-secondary" :disabled="loading" title="Refresh" @click="loadStatus">
          <i class="fa-solid fa-rotate" :class="{ 'fa-spin': loading }"></i>
        </button>
      </div>
      <div class="card-body">
        <div v-if="loadError" class="alert alert-danger mb-0">{{ loadError }}</div>
        <div v-else-if="!status" class="text-secondary">Checking…</div>
        <template v-else>
          <div class="mb-3">
            <span v-if="status.reachable && !status.error" class="badge text-bg-success">Connected</span>
            <span v-else-if="status.reachable" class="badge text-bg-warning">Connected — schema not ready</span>
            <span v-else class="badge text-bg-danger">Not reachable</span>
          </div>
          <dl class="row mb-0">
            <dt class="col-sm-4">Server</dt>
            <dd class="col-sm-8">{{ status.host }}:{{ status.port }}</dd>
            <dt class="col-sm-4">Database</dt>
            <dd class="col-sm-8">{{ status.database }}</dd>
            <template v-if="status.reachable">
              <dt class="col-sm-4">MariaDB version</dt>
              <dd class="col-sm-8">{{ status.server_version }}</dd>
              <dt class="col-sm-4">Schema version</dt>
              <dd class="col-sm-8">
                <template v-if="status.schema_version !== null">
                  v{{ status.schema_version }} — {{ status.schema_description }}
                  <small class="text-secondary">({{ formatDateTime(status.schema_applied_at) }})</small>
                  <span v-if="!schemaUpToDate" class="badge text-bg-warning ms-1">latest is v{{ status.schema_latest }}</span>
                </template>
                <span v-else class="text-secondary">none applied</span>
              </dd>
            </template>
          </dl>
          <div v-if="status.error" class="alert alert-warning mt-3 mb-0 small">{{ status.error }}</div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.db-card {
  max-width: 640px;
}
</style>
