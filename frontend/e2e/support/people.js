// Who the browser is (S024 § 1.2, § 5.1).  Each seed person (tooling/e2e/seed_e2e.py) has
// the login e2e_<key>; the browser sends the test headers on every request of its context,
// and the e2e backend builds the user from the database's memberships, as in production.
import { expect, request as playwrightRequest } from "@playwright/test";
import { BACKEND_URL } from "./stack.js";

// IT admin holds a token role; everyone else logs in as maintenance_team (S011)
const TOKEN_ROLE = { it_admin: "it_admin", admin: "admin" };

/** The test headers of a seed person. */
export function headersFor(key) {
  return { "X-Test-Role": TOKEN_ROLE[key] ?? "maintenance_team", "X-Test-User": `e2e_${key}` };
}

/**
 * Open the app at `path` as the seed person `key` — "technician", "engineer", … — and check
 * who it is before going on: /api/auth/me answers with that login, and the top bar shows the
 * person's name.  Calling it again on the same page switches the person (the app reads who
 * it is once per page load, so it loads the page again).
 */
export async function asPerson(page, key, path = "/") {
  await page.context().setExtraHTTPHeaders(headersFor(key));
  const meResponse = page.waitForResponse((r) => r.url().endsWith("/api/auth/me"));
  await page.goto(path);
  const me = await (await meResponse).json();
  expect(me.username, "the backend did not see the test headers").toBe(`e2e_${key}`);
  await expect(page.locator(".topbar-right").filter({ visible: true })).toContainText(me.name);
  return me;
}

/** An API client acting as a seed person, straight against the e2e backend (setup and look-ups). */
export async function apiAs(key) {
  return playwrightRequest.newContext({ baseURL: BACKEND_URL, extraHTTPHeaders: headersFor(key) });
}

/** The seed's equipment (seed_e2e.EQUIPMENT), by name: codes are generated, so they are looked up. */
export const EQUIPMENT = {
  extruder: "E2E extruder",
  gearbox: "E2E extruder gearbox",
  scrapped: "E2E scrapped compressor",
  mcc1Mill: "E2E MCC1 mill",
  filterPump: "E2E filter pump",
};

/**
 * The ids and codes of the seed's equipment, read through the API as admin:
 * {extruder: {id, code, ...}, ...}.  For a beforeAll (the `request` fixture is per test).
 */
export async function seedIds() {
  const api = await apiAs("admin");
  try {
    const res = await api.get("/api/equipment?level=all&include_scrapped=1&q=E2E&per_page=100");
    expect(res.ok(), `equipment look-up failed: ${res.status()}`).toBe(true);
    const byName = new Map((await res.json()).items.map((e) => [e.name, e]));
    return Object.fromEntries(Object.entries(EQUIPMENT).map(([key, name]) => {
      if (!byName.has(name)) throw new Error(`seed equipment "${name}" not found`);
      return [key, byName.get(name)];
    }));
  } finally {
    await api.dispose();
  }
}

/** A seed person's own Team record id (their /api/auth/me person_id). */
export async function personId(key) {
  const api = await apiAs(key);
  try {
    return (await (await api.get("/api/auth/me")).json()).person_id;
  } finally {
    await api.dispose();
  }
}
