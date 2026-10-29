import { describe, expect, it } from "vitest";
import { formatDate, formatDateTime } from "../src/utils/datetime.js";

describe("formatDateTime", () => {
  it("formats an API datetime as DD-MM-YYYY HH:MM without converting", () => {
    expect(formatDateTime("2026-10-12T08:05:59+05:30")).toBe("12-10-2026 08:05");
  });

  it("formats a date-only value", () => {
    expect(formatDateTime("2026-10-12")).toBe("12-10-2026");
  });

  it("returns empty for anything it cannot read", () => {
    expect(formatDateTime(null)).toBe("");
    expect(formatDateTime(undefined)).toBe("");
    expect(formatDateTime("")).toBe("");
    expect(formatDateTime("yesterday")).toBe("");
    expect(formatDateTime(1760000000)).toBe("");
  });
});

describe("formatDate", () => {
  it("keeps the date part of a datetime", () => {
    expect(formatDate("2026-10-12T08:05:59+05:30")).toBe("12-10-2026");
  });

  it("formats a date-only value", () => {
    expect(formatDate("2026-10-12")).toBe("12-10-2026");
  });

  it("returns empty for anything it cannot read", () => {
    expect(formatDate("")).toBe("");
    expect(formatDate(null)).toBe("");
  });
});
