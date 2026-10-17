/**
 * Tests for the masters cache in stores/masters.js: fetched once, shared, and
 * fetched again only on `refresh` or after resetMasters().
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.fn();
vi.mock("../src/api", () => ({ apiGet: (...args) => apiGet(...args) }));

import { ensureSites, ensureUnits, resetMasters, sites } from "../src/stores/masters";

beforeEach(() => {
  resetMasters();
  apiGet.mockReset();
  apiGet.mockImplementation(async (url) => ({ items: [{ id: 1, url }] }));
});

describe("ensureSites", () => {
  it("fetches once and hands back the cached list after", async () => {
    const first = await ensureSites();
    const second = await ensureSites();
    expect(apiGet).toHaveBeenCalledTimes(1);
    expect(apiGet).toHaveBeenCalledWith("/api/masters/sites?include_inactive=1");
    expect(second).toBe(first);
    expect(sites.value).toBe(first);
  });

  it("fetches again when asked to refresh, so another user's new site shows", async () => {
    await ensureSites();
    apiGet.mockImplementation(async () => ({ items: [{ id: 1 }, { id: 2 }] }));
    const refreshed = await ensureSites({ refresh: true });
    expect(apiGet).toHaveBeenCalledTimes(2);
    expect(refreshed).toHaveLength(2);
    expect(sites.value).toBe(refreshed);
  });

  it("fetches again after resetMasters()", async () => {
    await ensureSites();
    resetMasters();
    expect(sites.value).toBeNull();
    await ensureSites();
    expect(apiGet).toHaveBeenCalledTimes(2);
  });

  it("keeps each list apart", async () => {
    await ensureSites();
    await ensureUnits();
    expect(apiGet).toHaveBeenCalledTimes(2);
    expect(apiGet).toHaveBeenLastCalledWith("/api/masters/units?include_inactive=1");
  });
});
