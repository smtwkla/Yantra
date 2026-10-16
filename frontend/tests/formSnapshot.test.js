import { describe, expect, it } from "vitest";
import { formSnapshot } from "../src/utils/formSnapshot.js";

const file = (name, content = "x", lastModified = 1000) => new File([content], name, { lastModified });

describe("formSnapshot", () => {
  it("gives the same snapshot for the same values", () => {
    expect(formSnapshot({ a: "x", b: 1, c: null })).toBe(formSnapshot({ a: "x", b: 1, c: null }));
  });

  it("differs when a string, number or null changes", () => {
    const base = formSnapshot({ a: "x", b: 1, c: null });
    expect(formSnapshot({ a: "y", b: 1, c: null })).not.toBe(base);
    expect(formSnapshot({ a: "x", b: 2, c: null })).not.toBe(base);
    expect(formSnapshot({ a: "x", b: 1, c: 0 })).not.toBe(base);
  });

  it("is the same again after a change is undone", () => {
    const form = { a: "x" };
    const before = formSnapshot(form);
    form.a = "xy";
    expect(formSnapshot(form)).not.toBe(before);
    form.a = "x";
    expect(formSnapshot(form)).toBe(before);
  });

  it("sees a chosen File, and tells files apart", () => {
    const none = formSnapshot({ file: null });
    const a = formSnapshot({ file: file("a.pdf") });
    expect(a).not.toBe(none);
    expect(formSnapshot({ file: file("b.pdf") })).not.toBe(a);
    expect(formSnapshot({ file: file("a.pdf", "longer") })).not.toBe(a);
    expect(formSnapshot({ file: file("a.pdf") })).toBe(a);
  });

  it("ignores the order of a Set but not its members", () => {
    expect(formSnapshot({ s: new Set([3, 1, 2]) })).toBe(formSnapshot({ s: new Set([1, 2, 3]) }));
    expect(formSnapshot({ s: new Set([1, 2, 3, 4]) })).not.toBe(formSnapshot({ s: new Set([1, 2, 3]) }));
    expect(formSnapshot({ s: new Set() })).not.toBe(formSnapshot({ s: new Set([1]) }));
  });

  it("handles nested objects and arrays", () => {
    const a = { x: { y: [1, { z: "q" }] } };
    expect(formSnapshot(a)).toBe(formSnapshot({ x: { y: [1, { z: "q" }] } }));
    expect(formSnapshot({ x: { y: [1, { z: "r" }] } })).not.toBe(formSnapshot(a));
    expect(formSnapshot({ x: { y: [1] } })).not.toBe(formSnapshot(a));
  });

  it("treats undefined like an absent key", () => {
    expect(formSnapshot({ a: undefined })).toBe(formSnapshot({}));
  });
});
