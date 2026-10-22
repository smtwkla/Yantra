<script setup>
/**
 * Settings — system status and app settings.
 * - Database card: reachability, server and schema version.
 * - Uploads card: the upload size limit (S006 § 5.7), editable with settings:edit,
 *   read-only with settings:read. The backend validates the range.
 * - Removed documents card: restore or delete for good, with equipment:purge_documents (S008).
 * - Labels card: the address QR labels carry (S014 § 3), editable with settings:edit; the
 *   backend validates it and sends the default until the first save.
 * - Network card: the plant's internal ranges, editable with settings:edit, and the address the
 *   server sees for this browser (S013 § 5.2). The backend validates and refuses a list that
 *   would block the saver.
 * - Notifications card (S021 § 1.6): escalation times per criticality grade, whether push is set
 *   up — its own component, NotificationsSettings.vue.
 * - Background tasks card: each scheduled task's last and next run, Overdue when the worker
 *   seems stopped, and the failed count (S013 § 5.6).
 * - Access log card, with access_log:view (S013 § 5.4).
 */
import { computed, onMounted, ref } from "vue";
import { apiGet, apiPut } from "../api";
import { userPermissions } from "../stores/auth";
import { formatDateTime } from "../utils/datetime";
import AccessLog from "./settings/AccessLog.vue";
import NotificationsSettings from "./settings/NotificationsSettings.vue";
import RemovedDocuments from "./settings/RemovedDocuments.vue";

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
const canPurgeDocuments = computed(() => userPermissions.value.includes("equipment:purge_documents"));
const canViewAccessLog = computed(() => userPermissions.value.includes("access_log:view"));
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

// ---------------------------------------------------------------------------
// Labels — the link address printed in every QR label
// ---------------------------------------------------------------------------

const labelBaseUrl = ref(null);    // as stored (or the default)
const labelBaseUrlInput = ref(""); // as typed
const labelsLoadError = ref("");
const labelsSaveError = ref("");
const labelsSaving = ref(false);
const labelsSaved = ref(false);

function showLabels(body) {
  labelBaseUrl.value = body.base_url;
  labelBaseUrlInput.value = body.base_url;
}

async function loadLabels() {
  labelsLoadError.value = "";
  try {
    showLabels(await apiGet("/api/settings/labels"));
  } catch (err) {
    labelsLoadError.value = err.message;
  }
}

async function saveLabels() {
  labelsSaving.value = true;
  labelsSaveError.value = "";
  labelsSaved.value = false;
  try {
    showLabels(await apiPut("/api/settings/labels", { base_url: labelBaseUrlInput.value }));
    labelsSaved.value = true;
  } catch (err) {
    labelsSaveError.value = err.message;
  } finally {
    labelsSaving.value = false;
  }
}

// ---------------------------------------------------------------------------
// Network — the internal ranges (IT admin may use Yantra only from inside them)
// ---------------------------------------------------------------------------

const network = ref(null);        // {networks: [...], your_ip, your_ip_internal}, as stored
const networksInput = ref("");    // as typed, one range per line
const networkLoadError = ref("");
const networkSaveError = ref("");
const networkSaving = ref(false);
const networkSaved = ref(false);

const networksText = (body) => body.networks.join("\n");

function showNetwork(body) {
  network.value = body;
  networksInput.value = networksText(body);
}

async function loadNetwork() {
  networkLoadError.value = "";
  try {
    showNetwork(await apiGet("/api/settings/network"));
  } catch (err) {
    networkLoadError.value = err.message;
  }
}

async function saveNetwork() {
  networkSaving.value = true;
  networkSaveError.value = "";
  networkSaved.value = false;
  try {
    showNetwork(await apiPut("/api/settings/network", { networks: networksInput.value }));
    networkSaved.value = true;
  } catch (err) {
    networkSaveError.value = err.message;
  } finally {
    networkSaving.value = false;
  }
}

const networksChanged = computed(() => network.value !== null && networksInput.value !== networksText(network.value));

// ---------------------------------------------------------------------------
// Background tasks — the worker's scheduled tasks
// ---------------------------------------------------------------------------

const TASK_LABELS = { purge_access_log: "Delete access-log entries older than 365 days" };
const TASK_STATUS_BADGES = {
  done: "text-bg-success",
  failed: "text-bg-danger",
  pending: "text-bg-secondary",
  running: "text-bg-info",
};

const tasks = ref(null); // {tasks: [...], failed_count}
const tasksLoading = ref(false);
const tasksLoadError = ref("");

async function loadTasks() {
  tasksLoading.value = true;
  tasksLoadError.value = "";
  try {
    tasks.value = await apiGet("/api/settings/tasks");
  } catch (err) {
    tasksLoadError.value = err.message;
  } finally {
    tasksLoading.value = false;
  }
}

onMounted(() => {
  loadStatus();
  loadAppSettings();
  loadLabels();
  loadNetwork();
  loadTasks();
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

    <div class="card settings-card mt-3">
      <div class="card-header"><i class="fa-solid fa-qrcode me-2"></i>Labels</div>
      <div class="card-body">
        <div v-if="labelsLoadError" class="alert alert-danger mb-0">{{ labelsLoadError }}</div>
        <div v-else-if="labelBaseUrl === null" class="text-secondary">Loading…</div>
        <form v-else-if="canEditSettings" novalidate @submit.prevent="saveLabels">
          <label class="form-label" for="label-base-url">Label link address</label>
          <div class="d-flex flex-wrap align-items-start gap-2">
            <input
              id="label-base-url"
              v-model="labelBaseUrlInput"
              type="text"
              class="form-control label-address"
              :class="{ 'is-invalid': labelsSaveError }"
              spellcheck="false"
              @input="labelsSaved = false"
            />
            <button type="submit" class="btn btn-primary" :disabled="labelsSaving || labelBaseUrlInput === labelBaseUrl">
              <span v-if="labelsSaving" class="spinner-border spinner-border-sm me-1"></span>Save
            </button>
            <span v-if="labelsSaved" class="text-success align-self-center small">Saved</span>
          </div>
          <div v-if="labelsSaveError" class="invalid-feedback d-block">{{ labelsSaveError }}</div>
          <div class="form-text">
            Each QR label opens this address + /e/ + the equipment code, whoever prints it. Only the host
            (no path), at most 40 characters. Labels already printed keep the address they were printed with.
          </div>
        </form>
        <dl v-else class="row mb-0">
          <dt class="col-sm-4">Label link address</dt>
          <dd class="col-sm-8 mb-0">{{ labelBaseUrl }}</dd>
        </dl>
      </div>
    </div>

    <div class="card settings-card mt-3">
      <div class="card-header"><i class="fa-solid fa-network-wired me-2"></i>Network</div>
      <div class="card-body">
        <div v-if="networkLoadError" class="alert alert-danger mb-0">{{ networkLoadError }}</div>
        <div v-else-if="!network" class="text-secondary">Loading…</div>
        <template v-else>
          <p class="mb-2">
            Your address: <strong>{{ network.your_ip || "unknown" }}</strong> —
            <span v-if="network.your_ip_internal" class="badge text-bg-success">internal</span>
            <span v-else class="badge text-bg-warning">external</span>
          </p>
          <form v-if="canEditSettings" novalidate @submit.prevent="saveNetwork">
            <label class="form-label" for="internal-networks">Plant network ranges</label>
            <textarea
              id="internal-networks"
              v-model="networksInput"
              class="form-control font-monospace"
              :class="{ 'is-invalid': networkSaveError }"
              rows="4"
              spellcheck="false"
              @input="networkSaved = false"
            ></textarea>
            <div v-if="networkSaveError" class="invalid-feedback d-block">{{ networkSaveError }}</div>
            <div class="form-text">
              One range per line, e.g. 10.24.0.0/16 (include the VPN pool). IT admin can use Yantra only from these;
              other roles work from anywhere. Applies here at once, everywhere within 5 minutes. A list that leaves
              out your own address is refused; it does not check other sites' ranges, so check each before saving.
            </div>
            <div class="d-flex align-items-center gap-2 mt-2">
              <button type="submit" class="btn btn-primary" :disabled="networkSaving || !networksChanged">
                <span v-if="networkSaving" class="spinner-border spinner-border-sm me-1"></span>Save
              </button>
              <span v-if="networkSaved" class="text-success small">Saved</span>
            </div>
          </form>
          <dl v-else class="row mb-0">
            <dt class="col-sm-4">Plant network ranges</dt>
            <dd class="col-sm-8 mb-0 font-monospace">
              <div v-for="range in network.networks" :key="range">{{ range }}</div>
            </dd>
          </dl>
        </template>
      </div>
    </div>

    <NotificationsSettings />

    <div class="card settings-card mt-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span><i class="fa-solid fa-gears me-2"></i>Background tasks</span>
        <button class="btn btn-sm btn-outline-secondary" :disabled="tasksLoading" title="Refresh" @click="loadTasks">
          <i class="fa-solid fa-rotate" :class="{ 'fa-spin': tasksLoading }"></i>
        </button>
      </div>
      <div class="card-body">
        <div v-if="tasksLoadError" class="alert alert-danger mb-0">{{ tasksLoadError }}</div>
        <div v-else-if="!tasks" class="text-secondary">Loading…</div>
        <template v-else>
          <div v-for="task in tasks.tasks" :key="task.task_type" class="mb-3">
            <div class="fw-semibold">
              {{ TASK_LABELS[task.task_type] || task.task_type }}
              <span class="text-secondary small fw-normal">— daily at {{ task.daily_at }}</span>
            </div>
            <div class="small">
              Last run:
              <template v-if="task.last_run">
                {{ formatDateTime(task.last_run) }}
                <span class="badge ms-1" :class="TASK_STATUS_BADGES[task.last_status] || 'text-bg-light'">
                  {{ task.last_status }}
                </span>
              </template>
              <span v-else class="text-secondary">never</span>
            </div>
            <div class="small">
              Next run: {{ formatDateTime(task.next_run) }}
              <span v-if="task.overdue" class="badge text-bg-danger ms-1">Overdue — is the worker running?</span>
            </div>
          </div>
          <div class="small" :class="tasks.failed_count > 0 ? 'text-danger fw-semibold' : 'text-secondary'">
            Failed tasks: {{ tasks.failed_count }}
          </div>
        </template>
      </div>
    </div>

    <AccessLog v-if="canViewAccessLog" />

    <RemovedDocuments v-if="canPurgeDocuments" />
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
.label-address {
  max-width: 360px;
}
</style>
