<script setup>
/**
 * My notifications (docs/steps/S021-alerts-push/1-brief.md § 1.3): this device's state with Turn
 * on / Turn off, Send a test, my devices with Remove, the email card with Send test email (S032
 * § 1.5), and What you will get.
 *
 * The state and the rules live in stores/notifications.js (the bell's dot reads the same) and the
 * server; this page shows them. An iPhone needs Yantra on the Home Screen before it can get
 * notifications at all (iOS 16.4 or later).
 */
import { computed, onMounted, ref } from "vue";
import { userPersonId, userRoles } from "../stores/auth";
import {
  deviceState, devices, loadNotifications, pushConfig, removeDevice, sendTest, sendTestEmail, turnOff, turnOn,
} from "../stores/notifications";
import { BLOCKED } from "../push";
import { formatDateTime } from "../utils/datetime";

const loadError = ref("");
const actionError = ref("");
const busy = ref(false);
const testSent = ref("");
const confirmingId = ref(null);
const emailBusy = ref(false);
const emailError = ref("");
const emailSent = ref("");

const isItAdmin = computed(() => userRoles.value.includes("it_admin"));
const youGet = computed(() => pushConfig.value?.you_get ?? []);
const canTest = computed(() => pushConfig.value?.enabled && devices.value.length > 0);
const inTeam = computed(() => !["loading", "not_in_team"].includes(deviceState.value));
// S032: the email channel, as the server reports it; the address is the person's own, from the login
const email = computed(() => pushConfig.value?.email ?? { enabled: false, address: null });
const canTestEmail = computed(() => email.value.enabled && Boolean(email.value.address));

async function load() {
  loadError.value = "";
  try {
    await loadNotifications(userPersonId.value);
  } catch (err) {
    loadError.value = err.message;
  }
}

/** Run one action with the buttons held; its refusal shows in the card. */
async function act(action) {
  busy.value = true;
  actionError.value = "";
  testSent.value = "";
  try {
    await action();
  } catch (err) {
    // A refused permission shows as the Blocked state itself, not as an error line
    if (err.kind !== BLOCKED) actionError.value = err.message;
  } finally {
    busy.value = false;
  }
}

// Called straight from the tap: iOS lets only a tap ask for the permission
const onTurnOn = () => act(turnOn);
const onTurnOff = () => act(turnOff);

function onTest() {
  act(async () => {
    const count = await sendTest();
    testSent.value = `Sent to ${count} ${count === 1 ? "device" : "devices"}`;
  });
}

async function onTestEmail() {
  emailBusy.value = true;
  emailError.value = "";
  emailSent.value = "";
  try {
    const address = await sendTestEmail();
    emailSent.value = `A test email is on its way to ${address}. Check your inbox in a few minutes.`;
  } catch (err) {
    emailError.value = err.message;
  } finally {
    emailBusy.value = false;
  }
}

function onRemove(device) {
  act(async () => {
    await removeDevice(device);
    confirmingId.value = null;
  });
}

onMounted(load);
</script>

<template>
  <div class="py-3 notifications-page">
    <div class="card">
      <div class="card-header"><i class="fa-solid fa-mobile-screen me-2"></i>This device</div>
      <div class="card-body">
        <div v-if="loadError" class="alert alert-danger mb-0">{{ loadError }}</div>
        <div v-else-if="deviceState === 'loading'" class="text-secondary">Checking…</div>

        <template v-else-if="deviceState === 'not_in_team'">
          <p v-if="isItAdmin" class="mb-0">You are not in Team. Add yourself in Masters › Team to get test messages.</p>
          <p v-else class="mb-0">You are not in Team. Ask IT admin to add you.</p>
        </template>

        <p v-else-if="deviceState === 'not_set_up'" class="mb-0">
          Notifications are not set up on this server yet. Ask IT admin.
        </p>

        <template v-else-if="deviceState === 'iphone_home'">
          <p class="fw-semibold">Add Yantra to the Home Screen, then open it from the icon.</p>
          <p class="text-secondary small mb-0">
            On an iPhone, notifications work only in the Home Screen app (iOS 16.4 or later). In Safari, tap
            Share › Add to Home Screen.
          </p>
        </template>

        <p v-else-if="deviceState === 'unsupported'" class="mb-0">
          This browser cannot get notifications. Use Chrome on Android, or open Yantra from the Home Screen on an
          iPhone.
        </p>

        <template v-else-if="deviceState === 'blocked'">
          <p class="fw-semibold">Notifications are blocked for Yantra in this browser.</p>
          <p class="text-secondary small mb-0">
            Open the browser's site settings for Yantra, allow notifications, then reload this page.
          </p>
        </template>

        <template v-else>
          <p v-if="deviceState === 'on'">
            <span class="badge text-bg-success me-1">On</span>Notifications are on for this phone.
          </p>
          <p v-else>
            <span class="badge text-bg-secondary me-1">Off</span>Notifications are off for this phone. Turn them on
            to get alerts here.
          </p>
          <div class="d-flex flex-wrap gap-2">
            <button v-if="deviceState === 'off'" class="btn btn-primary" :disabled="busy" @click="onTurnOn">
              <span v-if="busy" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="fa-solid fa-bell me-1"></i>Turn on for this phone
            </button>
            <button v-else class="btn btn-outline-secondary" :disabled="busy" @click="onTurnOff">
              <i class="fa-solid fa-bell-slash me-1"></i>Turn off
            </button>
          </div>
        </template>

        <div v-if="actionError" class="alert alert-danger mt-3 mb-0">{{ actionError }}</div>
      </div>
    </div>

    <div v-if="inTeam" class="card mt-3">
      <div class="card-header d-flex justify-content-between align-items-center gap-2">
        <span><i class="fa-solid fa-list me-2"></i>My devices</span>
        <button v-if="canTest" class="btn btn-outline-primary" :disabled="busy" @click="onTest">
          <i class="fa-solid fa-paper-plane me-1"></i>Send a test
        </button>
      </div>
      <div v-if="testSent" class="alert alert-success py-2 m-2 mb-0">{{ testSent }}</div>
      <div v-if="!devices.length" class="card-body text-secondary">No device has notifications on.</div>
      <ul v-else class="list-group list-group-flush">
        <li v-for="device in devices" :key="device.id" class="list-group-item">
          <div class="d-flex align-items-center gap-2">
            <div class="flex-grow-1 text-break">
              <div>
                {{ device.label }}
                <span v-if="device.this_device" class="badge text-bg-info ms-1">This device</span>
              </div>
              <div class="small text-secondary">
                Added {{ formatDateTime(device.created_at) }}
                · Last sent {{ device.last_sent_at ? formatDateTime(device.last_sent_at) : "never" }}
              </div>
              <div v-if="device.last_error" class="small text-danger">Last error: {{ device.last_error }}</div>
            </div>
            <button
              v-if="confirmingId !== device.id"
              class="btn btn-outline-danger"
              :disabled="busy"
              @click="confirmingId = device.id"
            >
              Remove
            </button>
          </div>
          <div v-if="confirmingId === device.id" class="d-flex flex-wrap align-items-center justify-content-end gap-3 mt-2">
            <span>Remove {{ device.label }}? That device gets no alerts until it turns them on again.</span>
            <button class="btn btn-danger" :disabled="busy" @click="onRemove(device)">Yes</button>
            <button class="btn btn-outline-secondary" @click="confirmingId = null">No</button>
          </div>
        </li>
      </ul>
    </div>

    <div v-if="inTeam" class="card mt-3 email-card">
      <div class="card-header d-flex justify-content-between align-items-center gap-2">
        <span><i class="fa-solid fa-envelope me-2"></i>Email</span>
        <button v-if="canTestEmail" class="btn btn-outline-primary" :disabled="emailBusy" @click="onTestEmail">
          <span v-if="emailBusy" class="spinner-border spinner-border-sm me-1"></span>
          <i v-else class="fa-solid fa-paper-plane me-1"></i>Send test email
        </button>
      </div>
      <div class="card-body">
        <p v-if="!email.enabled" class="mb-0">Email is not set up on this server yet. Ask IT admin.</p>
        <p v-else-if="!email.address" class="mb-0">
          Your login has no email address, so you get no email. Ask IT admin to add an email address to your login.
        </p>
        <p v-else class="mb-0 text-break">Email goes to {{ email.address }}, from your login.</p>
        <div v-if="emailSent" class="alert alert-success py-2 mt-3 mb-0 text-break">{{ emailSent }}</div>
        <div v-if="emailError" class="alert alert-danger mt-3 mb-0">{{ emailError }}</div>
      </div>
    </div>

    <div v-if="inTeam" class="card mt-3">
      <div class="card-header"><i class="fa-solid fa-bullhorn me-2"></i>What you will get</div>
      <div class="card-body">
        <ul v-if="youGet.length" class="mb-0">
          <li v-for="line in youGet" :key="line">{{ line }}</li>
        </ul>
        <p v-else-if="isItAdmin" class="mb-0">Test messages only. IT admin holds no site role.</p>
        <p v-else class="mb-0">Nothing yet. Ask your engineer.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notifications-page {
  max-width: 640px;
}
</style>
