/**
 * Update detection — notices when the browser is running an outdated bundle.
 *
 * Why this exists: index.html is served no-cache (tooling/build/nginx.conf) so
 * a page *load* always picks up a new build.  But a tab left open on the shop
 * floor never reloads, and keeps running old JS indefinitely.  This compares
 * the version baked into the running bundle at build time against the version
 * the server reports right now, and flags a mismatch for UpdateToast.vue.
 *
 * Both numbers come from the same root VERSION file — vite.config.js bakes it
 * in as __APP_VERSION__, and the backend serves it from /api/version.
 *
 * The user is prompted, never interrupted: we must not reload a tab out from
 * under someone half-way through entering a breakdown or a PM job.
 */

import { ref } from "vue";

/** How often to re-check while the tab is actually on screen. */
const CHECK_INTERVAL_MS = 15 * 60 * 1000;

/** True once the server reports a version different from ours. */
export const updateAvailable = ref(false);

/** The version the server is on — shown in the toast. */
export const serverVersion = ref(null);

let intervalId = null;

/**
 * Decide whether `serverValue` means our bundle is outdated.
 *
 * Pure so it can be tested without a network or a DOM.  Deliberately
 * conservative: anything we cannot interpret means "no update", because a
 * false positive nags the user on every check with no way to clear it.
 *
 * @param {string} ourValue    version baked into this bundle
 * @param {*}      serverValue version reported by /api/version
 * @returns {boolean}
 */
export function isOutdated(ourValue, serverValue) {
  // A non-string server value means a broken or proxied response.
  if (typeof serverValue !== "string" || serverValue === "") return false;
  // "unknown" = the backend could not read its VERSION file; not a real version.
  if (serverValue === "unknown") return false;
  // Our own version is missing only in odd dev builds — nothing to compare to.
  if (typeof ourValue !== "string" || ourValue === "" || ourValue === "?") return false;
  return ourValue !== serverValue;
}

/** Version compiled into this bundle, or null if the define was missing. */
function ourVersion() {
  return typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : null;
}

/**
 * Ask the server for its version and update `updateAvailable`.
 *
 * Silent on failure: the shop floor loses connectivity routinely, and a failed
 * check is not something the user can act on.  Never clears an update that has
 * already been detected — the new build does not go away.
 */
export async function checkVersion() {
  if (updateAvailable.value) return; // already flagged; nothing to re-check

  try {
    // Plain fetch, not api.js: this is public, needs no Bearer token, and must
    // not be served from cache — a cached reply would hide the very update we
    // are looking for.
    const response = await fetch("/api/version", { cache: "no-store" });
    if (!response.ok) return;

    const data = await response.json();
    if (isOutdated(ourVersion(), data?.version)) {
      serverVersion.value = data.version;
      updateAvailable.value = true;
      stopVersionChecks(); // found it — stop polling
    }
  } catch {
    // Offline or backend restarting. Try again at the next check.
  }
}

/** Re-check when the tab comes back to the foreground. */
function onVisibilityChange() {
  if (document.visibilityState === "visible") checkVersion();
}

/**
 * Begin watching for updates.  Called once from App.vue.
 *
 * Checks on tab foregrounding (the mobile case — an operator returning to the
 * app) plus a slow interval while visible.  No background polling: mobile
 * Chrome throttles it anyway, and it would only cost battery.
 */
export function startVersionChecks() {
  if (intervalId !== null) return; // already running

  document.addEventListener("visibilitychange", onVisibilityChange);
  intervalId = setInterval(() => {
    if (document.visibilityState === "visible") checkVersion();
  }, CHECK_INTERVAL_MS);

  checkVersion();
}

export function stopVersionChecks() {
  if (intervalId !== null) {
    clearInterval(intervalId);
    intervalId = null;
  }
  document.removeEventListener("visibilitychange", onVisibilityChange);
}

/** Reload onto the new build. */
export function reloadApp() {
  window.location.reload();
}
