<script setup>
/**
 * Settings — system status and app settings.
 * - Database card: reachability, server and schema version.
 * - Uploads card: the upload size limit (S006 § 5.7), editable with settings:edit,
 *   read-only with settings:read. The backend validates the range.
 */
import { computed, onMounted, ref } from "vue";
import { apiGet, apiPut } from "../api";
import { userPermissions } from "../stores/auth";
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

// ---------------------------------------------------------------------------
// Uploads — the upload size limit
// ---------------------------------------------------------------------------

const UPLOAD_MAX_MB_MIN = 1;
const UPLOAD_MAX_MB_MAX = 100;

const canEditSettings = computed(() => userPermissions.value.includes("settings:edit"));
const uploadMaxMb = ref(null);      // as stored
const uploadMaxMbInput = ref(null); // as typed
const appLoadError = ref("");
const appSaveError = ref("");
const appSaving = ref(false);
const appSaved = ref(false);

async function loadAppSettings() {
  appLoadError.value = "";
  try {
    const settings = await apiGet("/api/settings/app");
    uploadMaxMb.value = settings.upload_max_mb;
    uploadMaxMbInput.value = settings.upload_max_mb;
  } catch (err) {
    appLoadError.value = err.message;
  }
}

async function saveAppSettings() {
  appSaving.value = true;
  appSaveError.value = "";
  appSaved.value = false;
  try {
    // An empty or non-numeric box is sent as null; the backend refuses it with its message
    const value = Number.isFinite(uploadMaxMbInput.value) ? uploadMaxMbInput.value : null;
    const settings = await apiPut("/api/settings/app", { upload_max_mb: value });
    uploadMaxMb.value = settings.upload_max_mb;
    uploadMaxMbInput.value = settings.upload_max_mb;
    appSaved.value = true;
  } catch (err) {
    appSaveError.value = err.message;
  } finally {
    appSaving.value = false;
  }
}

onMounted(() => {
  loadStatus();
  loadAppSettings();
});
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

    <div class="card settings-card mt-3">
      <div class="card-header"><i class="fa-solid fa-upload me-2"></i>Uploads</div>
      <div class="card-body">
        <div v-if="appLoadError" class="alert alert-danger mb-0">{{ appLoadError }}</div>
        <div v-else-if="uploadMaxMb === null" class="text-secondary">Loading…</div>
        <form v-else-if="canEditSettings" novalidate @submit.prevent="saveAppSettings">
          <label class="form-label" for="upload-max-mb">Largest file for documents and photos</label>
          <div class="d-flex flex-wrap align-items-start gap-2">
            <div class="input-group upload-limit">
              <input
                id="upload-max-mb"
                v-model.number="uploadMaxMbInput"
                type="number"
                class="form-control"
                :class="{ 'is-invalid': appSaveError }"
                :min="UPLOAD_MAX_MB_MIN"
                :max="UPLOAD_MAX_MB_MAX"
                step="1"
                @input="appSaved = false"
              />
              <span class="input-group-text">MB</span>
            </div>
            <button type="submit" class="btn btn-primary" :disabled="appSaving || uploadMaxMbInput === uploadMaxMb">
              <span v-if="appSaving" class="spinner-border spinner-border-sm me-1"></span>Save
            </button>
            <span v-if="appSaved" class="text-success align-self-center small">Saved</span>
          </div>
          <div v-if="appSaveError" class="invalid-feedback d-block">{{ appSaveError }}</div>
          <div class="form-text">From {{ UPLOAD_MAX_MB_MIN }} to {{ UPLOAD_MAX_MB_MAX }} MB; applies at once.</div>
        </form>
        <dl v-else class="row mb-0">
          <dt class="col-sm-4">Largest file</dt>
          <dd class="col-sm-8 mb-0">{{ uploadMaxMb }} MB</dd>
        </dl>
      </div>
    </div>
  </div>
</template>

<style scoped>
.db-card,
.settings-card {
  max-width: 640px;
}
.upload-limit {
  max-width: 160px;
}
</style>
