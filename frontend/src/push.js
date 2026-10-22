/**
 * Web push in the browser (docs/steps/S021-alerts-push/1-brief.md § 3) — the only file that
 * touches navigator.serviceWorker, PushManager and Notification.
 *
 * - registerServiceWorker(): at start-up (main.js), once;
 * - the device's state: supported, iPhone, Home Screen app, permission;
 * - currentSubscription(), subscribe(publicKey), unsubscribe();
 * - endpointHash(endpoint): the device's key, as the server makes it (SHA-256, lowercase hex).
 *
 * Every failure is caught here and becomes a PushError whose message the page shows; nothing is
 * written to the console (the browser tests fail on any console.error, S021 BS1-08).
 */

const SERVICE_WORKER = "/sw.js";
// A service worker that never becomes active must not hang the Turn on button
const READY_TIMEOUT_MS = 10_000;

export const NOT_STARTED = "This browser could not start notifications. Reload the page and try again.";
export const NOT_TURNED_ON = "This browser could not turn notifications on. Try again, or use Chrome on Android.";
export const NOT_ALLOWED = "Notifications were not turned on. Tap Turn on for this phone again, then choose Allow.";
export const BLOCKED = "blocked";

/** A failure the page shows as it is; `kind` is BLOCKED when the person refused permission. */
export class PushError extends Error {
  constructor(message, kind = null) {
    super(message);
    this.kind = kind;
  }
}

let registration = null;

/** True when this browser has the parts web push needs. */
export function isPushSupported() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

/** An iPhone or iPad (iPadOS asks as a Mac with a touch screen). */
export function isIphone() {
  return /iPhone|iPad|iPod/.test(navigator.userAgent)
    || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

/** Running as the installed app (Home Screen on iOS, an installed app on Android). */
export function isStandalone() {
  return window.matchMedia?.("(display-mode: standalone)").matches === true || navigator.standalone === true;
}

/** "granted", "denied", "default", or "unsupported". */
export function permission() {
  return "Notification" in window ? Notification.permission : "unsupported";
}

/** Register sw.js once -> the registration, or null when the browser has none or it failed. */
export function registerServiceWorker() {
  if (!registration) {
    registration = "serviceWorker" in navigator
      ? navigator.serviceWorker.register(SERVICE_WORKER).catch(() => null)
      : Promise.resolve(null);
  }
  return registration;
}

async function readyRegistration() {
  const registered = await registerServiceWorker();
  if (!registered) throw new PushError(NOT_STARTED);
  if (registered.active) return registered;
  const timeout = new Promise((resolve) => { setTimeout(() => resolve(null), READY_TIMEOUT_MS); });
  const ready = await Promise.race([navigator.serviceWorker.ready, timeout]);
  if (!ready) throw new PushError(NOT_STARTED);
  return ready;
}

/** The browser's subscription, or null (none, no service worker, no push). */
export async function currentSubscription() {
  if (!isPushSupported()) return null;
  const registered = await registerServiceWorker();
  if (!registered?.pushManager) return null;
  try {
    return await registered.pushManager.getSubscription();
  } catch {
    return null;
  }
}

function base64UrlToBytes(text) {
  const padded = text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4);
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
}

function sameKey(buffer, bytes) {
  if (!buffer) return false;
  const held = new Uint8Array(buffer);
  return held.length === bytes.length && held.every((value, i) => value === bytes[i]);
}

/**
 * Turn push on in this browser -> the subscription as JSON ({endpoint, keys: {p256dh, auth}}).
 * Call it straight from a tap: iOS grants the permission only to a request made by a tap, so
 * the request is the first thing done, before any await.
 */
export async function subscribe(publicKey) {
  if (!isPushSupported()) throw new PushError(NOT_TURNED_ON);
  let asked;
  try {
    asked = Notification.requestPermission();
  } catch {
    throw new PushError(NOT_TURNED_ON);
  }
  const answer = await asked;
  // Refused: the page shows the Blocked state. Closed without an answer: say what to do.
  if (answer === "denied") throw new PushError(BLOCKED, BLOCKED);
  if (answer !== "granted") throw new PushError(NOT_ALLOWED);
  const ready = await readyRegistration();
  const key = base64UrlToBytes(publicKey);
  try {
    const existing = await ready.pushManager.getSubscription();
    if (existing) {
      // The same server key: use it as it is; another (the server's keys changed): start again
      if (sameKey(existing.options?.applicationServerKey, key)) return existing.toJSON();
      await existing.unsubscribe();
    }
    const created = await ready.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key });
    return created.toJSON();
  } catch {
    throw new PushError(NOT_TURNED_ON);
  }
}

/** Turn push off in this browser -> the endpoint it had (for the server), or null. */
export async function unsubscribe() {
  const held = await currentSubscription();
  if (!held) return null;
  const { endpoint } = held;
  try {
    await held.unsubscribe();
  } catch {
    // The server's row goes anyway; the browser's own subscription then just waits unused
  }
  return endpoint;
}

/** SHA-256 of the endpoint, lowercase hex, as push_core.endpoint_hash; null without crypto.subtle. */
export async function endpointHash(endpoint) {
  if (!globalThis.crypto?.subtle) return null;
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(endpoint));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}
