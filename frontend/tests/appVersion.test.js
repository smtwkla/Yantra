/**
 * Tests for the stale-bundle comparison in stores/appVersion.js.
 *
 * The rule under test is deliberately conservative: a false positive nags the
 * user on every check with no way to clear it, so anything ambiguous must mean
 * "no update".
 */

import { describe, it, expect } from "vitest";
import { isOutdated } from "../src/stores/appVersion";

describe("isOutdated", () => {
  it("flags an update when the server is on a different version", () => {
    expect(isOutdated("0.5.11", "0.5.12")).toBe(true);
  });

  it("stays quiet when the versions match", () => {
    expect(isOutdated("0.5.11", "0.5.11")).toBe(false);
  });

  it("compares by inequality, not ordering", () => {
    // A rollback is still a bundle the client is not running.
    expect(isOutdated("0.5.12", "0.5.11")).toBe(true);
  });

  it("ignores 'unknown' — the backend could not read its VERSION file", () => {
    expect(isOutdated("0.5.11", "unknown")).toBe(false);
  });

  it("ignores a missing or non-string server version", () => {
    expect(isOutdated("0.5.11", undefined)).toBe(false);
    expect(isOutdated("0.5.11", null)).toBe(false);
    expect(isOutdated("0.5.11", "")).toBe(false);
    expect(isOutdated("0.5.11", 511)).toBe(false);
    expect(isOutdated("0.5.11", { version: "0.5.12" })).toBe(false);
  });

  it("ignores a missing version on our side", () => {
    // AppSidebar renders "?" when the build-time define was absent.
    expect(isOutdated(undefined, "0.5.12")).toBe(false);
    expect(isOutdated("", "0.5.12")).toBe(false);
    expect(isOutdated("?", "0.5.12")).toBe(false);
  });
});
