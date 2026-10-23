// Notifications (S021 § 8 Automated, § 10 A1): My notifications, the bell and its dot, the device
// list, Settings › Notifications, the manifest and the service worker.
//
// The e2e backend has push on (its own VAPID pair per lane) and runs no worker, so nothing is ever
// sent. Headless Chromium answers Notification.permission "denied" even after
// context.grantPermissions(["notifications"]), so the tests that need a person who has not been
// asked yet stub the permission (askablePermission), as the "denied" test stubs its refusal.
// Headless Chromium has no push account either, so a real pushManager.subscribe() may fail: the
// tests that need "on" stub the browser's PushManager (fakePushManager) and let the page post
// the stubbed subscription itself; the device rows of "My devices" are seeded through the API.
// The iPhone 14 project (WebKit) checks the page's own rule, "an iPhone not running from the
// Home Screen" (BR2-14), never whether the engine has PushManager.
import { test, expect } from "./support/test.js";
import { expectFieldMessage } from "./support/dialogs.js";
import { apiAs, asPerson } from "./support/people.js";

const WEBKIT = "phone-webkit";
const DESKTOP = "desktop-chromium";
const IN_TEAM = ["operator", "supervisor", "technician", "engineer", "manager", "storekeeper"];
const ANDROID_CHROME = "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) "
  + "Chrome/130.0.0.0 Mobile Safari/537.36";
const KEYS = { p256dh: "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQ", auth: "tBHItJI5svbpez7KI4CCXg" };

/** The visible bell (the top bar is drawn twice: desktop and phone). */
function bell(page) {
  return page.getByRole("link", { name: "My notifications" }).filter({ visible: true });
}

function dot(page) {
  return bell(page).locator(".bell-dot");
}

/** Notification.permission "default" until the page asks, then "granted" (the person allows it). */
async function askablePermission(page) {
  await page.addInitScript(() => {
    let state = "default";
    Object.defineProperty(Notification, "permission", { get: () => state });
    Notification.requestPermission = async () => {
      state = "granted";
      return state;
    };
  });
}

/** Make the browser's PushManager answer as a phone with a push account would (Chromium only). */
async function fakePushManager(page) {
  await page.addInitScript((keys) => {
    let current = null;
    const endpoint = `https://fcm.googleapis.com/fcm/send/e2e-${Math.random().toString(36).slice(2)}`;
    const made = () => ({
      endpoint,
      options: { applicationServerKey: null },
      toJSON: () => ({ endpoint, keys }),
      unsubscribe: async () => { current = null; return true; },
    });
    PushManager.prototype.getSubscription = async function getSubscription() { return current; };
    PushManager.prototype.subscribe = async function subscribe() { current = made(); return current; };
  }, KEYS);
}

/** Remove every device of a seed person (setup: the lanes' databases outlive one project's run). */
async function removeDevices(key) {
  const api = await apiAs(key);
  try {
    const { items } = await (await api.get("/api/push/subscriptions")).json();
    for (const device of items) expect((await api.delete(`/api/push/subscriptions/${device.id}`)).status()).toBe(204);
  } finally {
    await api.dispose();
  }
}

/** A device for a seed person, through the API, as an Android phone's Chrome would send it. */
async function seedDevice(key) {
  const api = await apiAs(key);
  try {
    const endpoint = `https://fcm.googleapis.com/fcm/send/e2e-seed-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const res = await api.post("/api/push/subscriptions", {
      data: { endpoint, keys: KEYS }, headers: { "User-Agent": ANDROID_CHROME },
    });
    expect(res.status(), await res.text()).toBe(201);
    return res.json();
  } finally {
    await api.dispose();
  }
}

test("S021: My notifications opens for every seed person in Team and offers Turn on for this phone", async ({ page, consoleWatch }, testInfo) => {
  test.skip(testInfo.project.name === WEBKIT, "an iPhone shows the Home Screen step instead (next test)");
  await askablePermission(page);
  for (const key of IN_TEAM) {
    await test.step(key, async () => {
      await asPerson(page, key, "/notifications");
      await expect(page.getByRole("button", { name: "Turn on for this phone" })).toBeVisible();
    });
  }
  // With the permission granted the page reaches the browser's subscribe call. Headless Chromium
  // usually has no push account, so either the device turns on or the page says it could not
  // (and Chrome itself logs that a Playwright context, always incognito, has no Push API).
  consoleWatch.allowBrowserError("does not support the Push API in incognito mode");
  await page.getByRole("button", { name: "Turn on for this phone" }).click();
  await expect(page.getByText(/Notifications are on for this phone|could not turn notifications on/)).toBeVisible();
});

test("S021: on an iPhone outside the Home Screen the page explains Add to Home Screen, and the bell has its dot", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== WEBKIT, "the iPhone 14 project only");
  await asPerson(page, "engineer", "/notifications");
  await expect(page.getByText("Add Yantra to the Home Screen, then open it from the icon.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Turn on for this phone" })).toHaveCount(0);
  await expect(dot(page)).toBeVisible();
});

test("S021: a browser that blocked notifications is told how to unblock them", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== DESKTOP, "desktop Chromium: Playwright cannot deny a permission, so it is stubbed");
  await page.addInitScript(() => {
    Object.defineProperty(Notification, "permission", { get: () => "denied" });
  });
  await asPerson(page, "engineer", "/notifications");
  await expect(page.getByText("Notifications are blocked for Yantra in this browser.")).toBeVisible();
  await expect(page.getByText(/allow notifications, then reload this page/)).toBeVisible();
  await expect(dot(page)).toBeVisible();
});

test("S021: the bell shows on every screen and opens My notifications", async ({ page }) => {
  await asPerson(page, "engineer", "/equipment");
  for (const path of ["/equipment", "/tickets", "/tickets/new", "/masters"]) {
    await test.step(path, async () => {
      await page.goto(path);
      await expect(bell(page)).toBeVisible();
    });
  }
  await bell(page).click();
  await expect(page).toHaveURL(/\/notifications$/);
  await expect(page.locator(".topbar-center").filter({ visible: true })).toHaveText("My notifications");
});

test("S021: the dot shows to people who would get alerts on a device that is off — not to IT admin or a storekeeper", async ({ page }) => {
  for (const key of ["engineer", "technician", "manager", "supervisor"]) {
    await test.step(`${key}: dot`, async () => {
      await asPerson(page, key, "/equipment");
      await expect(dot(page)).toBeVisible();
    });
  }
  for (const key of ["it_admin", "storekeeper"]) {
    await test.step(`${key}: no dot`, async () => {
      await asPerson(page, key, "/equipment");
      await expect(bell(page)).toBeVisible();
      await expect(dot(page)).toHaveCount(0);
    });
  }
});

test("S021: Turn on clears the dot at once, and Turn off sets it again, without a reload", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === WEBKIT, "an iPhone outside the Home Screen cannot turn on (tested above)");
  await askablePermission(page);
  await fakePushManager(page);
  await asPerson(page, "engineer", "/notifications");
  await expect(dot(page)).toBeVisible();
  await page.getByRole("button", { name: "Turn on for this phone" }).click();
  await expect(page.getByText("Notifications are on for this phone.")).toBeVisible();
  await expect(dot(page)).toHaveCount(0);
  await expect(page.getByText("This device", { exact: true }).last()).toBeVisible();   // the badge in My devices
  await page.getByRole("button", { name: "Turn off" }).click();
  await expect(page.getByRole("button", { name: "Turn on for this phone" })).toBeVisible();
  await expect(dot(page)).toBeVisible();
});

test("S021: without a Team record the page says so and offers no Turn on — IT admin and anyone else", async ({ page }) => {
  await asPerson(page, "it_admin", "/notifications");
  await expect(page.getByText("You are not in Team. Add yourself in Masters › Team to get test messages.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Turn on for this phone" })).toHaveCount(0);

  // A login with a site role but no Team record (no seeded person with this login)
  await page.context().setExtraHTTPHeaders({ "X-Test-Role": "maint_engineer", "X-Test-User": "e2e_ghost" });
  await page.goto("/notifications");
  await expect(page.getByText("You are not in Team. Ask IT admin to add you.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Turn on for this phone" })).toHaveCount(0);
  await expect(dot(page)).toHaveCount(0);
});

test("S021: a device seeded through the API is listed; Send a test reports it; Remove asks first, then removes it", async ({ page }) => {
  await removeDevices("manager");
  await seedDevice("manager");
  await asPerson(page, "manager", "/notifications");
  const row = page.locator(".list-group-item").filter({ hasText: "Android · Chrome" });
  await expect(row).toBeVisible();
  await expect(row).toContainText("Last sent never");

  await page.getByRole("button", { name: "Send a test" }).click();
  await expect(page.getByText("Sent to 1 device")).toBeVisible();

  await row.getByRole("button", { name: "Remove" }).click();
  await expect(row.getByText("Remove Android · Chrome? That device gets no alerts until it turns them on again.")).toBeInViewport();
  await row.getByRole("button", { name: "Yes" }).click();
  await expect(page.getByText("No device has notifications on.")).toBeVisible();
});

test("S021 A1: What you will get — the engineer's breakdowns and defects, the technician's assigned jobs", async ({ page }) => {
  await asPerson(page, "engineer", "/notifications");
  const lines = page.locator(".card").filter({ hasText: "What you will get" });
  await expect(lines).toContainText("Breakdowns and defects at SMTW, escalations");
  await expect(lines).toContainText("Jobs assigned to you");
  await asPerson(page, "technician", "/notifications");
  await expect(lines.getByRole("listitem")).toHaveText(["Jobs assigned to you"]);
  await asPerson(page, "storekeeper", "/notifications");
  await expect(lines).toContainText("Nothing yet. Ask your engineer.");
});

test("S021: Settings › Notifications — IT admin changes B, it stays after a reload; 4 is refused on its box; the manager reads", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/settings/notifications", 400);   // the refused 4
  await asPerson(page, "it_admin", "/settings");
  const card = page.locator(".card").filter({ hasText: "Escalate a breakdown not acknowledged after" });
  await expect(card).toContainText("Push notifications work on this server.");
  const boxB = card.getByLabel("B — Slows production, repair within the shift");
  try {
    await boxB.fill("4");
    await card.getByRole("button", { name: "Save" }).click();
    await expectFieldMessage(card, "Must be a whole number from 5 to 1440");
    await expect(boxB).toBeFocused();

    await boxB.fill("20");
    await card.getByRole("button", { name: "Save" }).click();
    await expect(card.getByText("Saved")).toBeVisible();
    await page.reload();
    await expect(card.getByLabel("B — Slows production, repair within the shift")).toHaveValue("20");

    await asPerson(page, "manager", "/settings");
    await expect(card).toContainText("B — Slows production, repair within the shift");
    await expect(card).toContainText("20 min");
    await expect(card.getByRole("button", { name: "Save" })).toHaveCount(0);
  } finally {
    const api = await apiAs("it_admin");
    try {
      const res = await api.put("/api/settings/notifications", { data: { escalate_minutes: { A: 10, B: 30, C: 60 } } });
      expect(res.status()).toBe(200);
    } finally {
      await api.dispose();
    }
  }
});

test("S021: the manifest is served and parses; the service worker registers", async ({ page }, testInfo) => {
  await asPerson(page, "engineer", "/equipment");
  const res = await page.request.get("/manifest.webmanifest");
  expect(res.ok()).toBe(true);
  const manifest = JSON.parse(await res.text());
  expect(manifest).toMatchObject({ id: "/", name: "Yantra", start_url: "/", scope: "/", display: "standalone" });
  expect(manifest.icons.map((icon) => icon.sizes)).toEqual(expect.arrayContaining(["192x192", "512x512"]));
  for (const icon of manifest.icons) expect((await page.request.get(icon.src)).ok()).toBe(true);
  // The service worker on Chromium; WebKit's is not what an iPhone runs (§ 8)
  if (testInfo.project.name !== WEBKIT) {
    const scope = await page.evaluate(async () => (await navigator.serviceWorker.ready).scope);
    expect(new URL(scope).pathname).toBe("/");
  }
});

test("S032: the manager sees the closed-ticket email line and their address; Send test email says it is on its way", async ({ page }) => {
  // The manager's token carries an email claim (people.js EMAILS); the page load stores it
  await asPerson(page, "manager", "/notifications");
  await expect(page.locator(".card").filter({ hasText: "What you will get" })).toContainText("Closed tickets at SMTW, by email");
  const card = page.locator(".email-card");
  await expect(card).toContainText("Email goes to e2e_manager@example.test, from your login.");
  await card.getByRole("button", { name: "Send test email" }).click();
  await expect(card.getByText("A test email is on its way to e2e_manager@example.test. Check your inbox in a few minutes."))
    .toBeVisible();
});

test("S032: a person whose login has no email is told so, and gets no Send test email", async ({ page }) => {
  await asPerson(page, "technician", "/notifications");
  const card = page.locator(".email-card");
  await expect(card).toContainText(
    "Your login has no email address, so you get no email. Ask IT admin to add an email address to your login.");
  await expect(card.getByRole("button", { name: "Send test email" })).toHaveCount(0);
});
