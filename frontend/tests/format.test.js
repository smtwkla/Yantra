import { describe, expect, it } from "vitest";
import { formatBytes } from "../src/utils/format.js";

describe("formatBytes", () => {
  it("shows bytes below 1 KB", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(999)).toBe("999 B");
  });

  it("shows KB and MB with one decimal", () => {
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(20 * 1024 * 1024)).toBe("20.0 MB");
  });

  it("returns empty for anything that is not a size", () => {
    expect(formatBytes(null)).toBe("");
    expect(formatBytes(-1)).toBe("");
    expect(formatBytes(Number.NaN)).toBe("");
  });
});
