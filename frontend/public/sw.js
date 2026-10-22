// Yantra's service worker (docs/steps/S021-alerts-push/1-brief.md § 1.1, § 3, § 7 decision 2).
//
// Two jobs only: show a pushed alert, and open its ticket when the alert is tapped.  It caches
// nothing and has no fetch handler, so every page load goes to the network as before: Yantra
// stays online-only and the stale-bundle check (stores/appVersion.js) works unchanged.
// A new sw.js takes over at once (skipWaiting + clients.claim); with no fetch handler that
// cannot break an open page.

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// The payload is push_core.push_data: {title, body, path, tag, silent}
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { body: event.data ? event.data.text() : "" };
  }
  const options = {
    body: data.body || "",
    icon: "/icons/icon-192.png",
    // A later alert of the same ticket (the escalation) replaces the earlier one and rings again
    tag: data.tag || undefined,
    renotify: Boolean(data.tag),
    silent: Boolean(data.silent),
    data: { path: data.path || "/" },
  };
  event.waitUntil(self.registration.showNotification(data.title || "Yantra", options));
});

// Only a path on this origin is opened; anything else opens the start page
function targetUrl(path) {
  const url = new URL(typeof path === "string" && path.startsWith("/") && !path.startsWith("//") ? path : "/",
    self.location.origin);
  return url.origin === self.location.origin ? url.href : self.location.origin + "/";
}

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = targetUrl(event.notification.data && event.notification.data.path);
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    const open = windows.find((client) => new URL(client.url).origin === self.location.origin);
    if (open) {
      await open.focus();
      // navigate() needs a controlled window; an uncontrolled one is focused as it is
      if (open.navigate) {
        try {
          await open.navigate(url);
          return;
        } catch {
          // falls through to a new window
        }
      }
    }
    await self.clients.openWindow(url);
  })());
});
