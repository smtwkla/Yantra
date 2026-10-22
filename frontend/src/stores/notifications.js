/**
 * Notifications store (docs/steps/S021-alerts-push/1-brief.md § 1.3) — the state of this device,
 * my devices, and the bell's dot, shared by the top bar and *My notifications*.
 *
 * "On" means the browser holds a subscription AND the server lists it as this device
 * (this_device). The dot shows only when the person would get alerts (*What you will get* is not
 * empty) and this device is off, blocked, an iPhone not on the Home Screen, or a browser without
 * push — never for "not set up on this server" or "not in Team", which nobody on the floor can
 * fix (BR2-05, BR3-06). Turn on, Turn off and Remove update it at once, without a reload.
 *
 * Every rule about who gets what is the server's (GET /api/push/config's you_get); this store only
 * reads the browser's state through push.js.
 */

import { computed, ref } from "vue";
import { apiDelete, apiGet, apiPost } from "../api";
import * as push from "../push";

// Sign-out waits at most this long for this device's removal (best effort)
const SIGN_OUT_WAIT_MS = 3_000;

/** Who is signed in as a Team person, null when nobody (CR1-08: given by the caller, so this
 * store does not import auth.js, which imports this one). */
const personId = ref(null);
/** {enabled, public_key, you_get: [...]} from the server, or null before the first load. */
export const pushConfig = ref(null);
/** My devices, as GET /api/push/subscriptions lists them. */
export const devices = ref([]);
export const thisDeviceOn = ref(false);
export const permissionState = ref("default");

/** One of: loading, not_in_team, not_set_up, iphone_home, unsupported, blocked, on, off. */
export const deviceState = computed(() => {
  if (!pushConfig.value) return "loading";
  if (personId.value === null) return "not_in_team";
  if (!pushConfig.value.enabled) return "not_set_up";
  if (push.isIphone() && !push.isStandalone()) return "iphone_home";
  if (!push.isPushSupported()) return "unsupported";
  if (permissionState.value === "denied") return "blocked";
  return thisDeviceOn.value ? "on" : "off";
});

const NEEDS_ATTENTION = ["off", "blocked", "iphone_home", "unsupported"];

export const showDot = computed(
  () => Boolean(pushConfig.value?.you_get?.length) && NEEDS_ATTENTION.includes(deviceState.value),
);

async function loadDevices() {
  const held = await push.currentSubscription();
  const hash = held ? await push.endpointHash(held.endpoint) : null;
  const list = await apiGet(`/api/push/subscriptions${hash ? `?endpoint_hash=${hash}` : ""}`);
  devices.value = list.items;
  thisDeviceOn.value = Boolean(held) && list.items.some((device) => device.this_device);
}

/** Read the server's config, this browser's state and my devices. ``ownPersonId`` is the signed-in
 * person's id (auth.js userPersonId) or null. Throws the API's error. */
export async function loadNotifications(ownPersonId) {
  personId.value = ownPersonId ?? null;
  pushConfig.value = await apiGet("/api/push/config");
  permissionState.value = push.permission();
  await loadDevices();
}

/** Turn on: call straight from the tap (push.subscribe asks for permission first, § 1.2). */
export async function turnOn() {
  try {
    const subscription = await push.subscribe(pushConfig.value.public_key);
    await apiPost("/api/push/subscriptions", subscription);
  } finally {
    permissionState.value = push.permission();
  }
  await loadDevices();
}

/** Turn off: this browser stops, and its row on the server goes. */
export async function turnOff() {
  const endpoint = await push.unsubscribe();
  if (endpoint) await apiPost("/api/push/subscriptions/remove", { endpoint });
  await loadDevices();
}

export async function removeDevice(device) {
  await apiDelete(`/api/push/subscriptions/${device.id}`);
  await loadDevices();
}

/** A test alert to all my devices -> how many. */
export async function sendTest() {
  return (await apiPost("/api/push/test")).devices;
}

/**
 * Sign-out: this device's subscription is removed, whoever owns the row, so a phone that changes
 * hands stops getting the previous person's alerts (§ 1.2, BR3-03). Best effort and bounded: a
 * failure (offline, a slow server) never blocks sign-out; the next person's Turn on moves the row.
 */
export async function forgetThisDevice() {
  const removal = (async () => {
    const endpoint = await push.unsubscribe();
    if (endpoint) await apiPost("/api/push/subscriptions/remove", { endpoint });
  })().catch(() => {});
  const limit = new Promise((resolve) => { setTimeout(resolve, SIGN_OUT_WAIT_MS); });
  await Promise.race([removal, limit]);
}
