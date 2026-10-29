import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";
import { SHARE_COPIED_MS, useShareLink } from "../src/composables/useShareLink.js";

const PAYLOAD = { title: "TK-1", text: "TK-1 · A.B · M1 — Noise", url: "https://app.example.test/tickets/7" };

function stubDevice({ share, clipboard, coarse = true, matchMedia = true } = {}) {
  vi.stubGlobal("navigator", { share, clipboard });
  if (matchMedia) vi.stubGlobal("matchMedia", () => ({ matches: coarse }));
  else vi.stubGlobal("matchMedia", undefined);
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useShareLink (S066)", () => {
  it("share mode calls navigator.share with the title, text and url", async () => {
    const share = vi.fn().mockResolvedValue();
    const writeText = vi.fn();
    stubDevice({ share, clipboard: { writeText } });
    const link = useShareLink();
    expect(link.mode).toBe("share");
    await link.share(PAYLOAD);
    expect(share).toHaveBeenCalledWith(PAYLOAD);
    expect(writeText).not.toHaveBeenCalled();
  });

  it("calls navigator.share before any await", () => {
    const share = vi.fn().mockResolvedValue();
    stubDevice({ share, clipboard: { writeText: vi.fn() } });
    useShareLink().share(PAYLOAD); // not awaited
    expect(share).toHaveBeenCalledTimes(1);
  });

  it("an AbortError copies nothing and shows nothing", async () => {
    const abort = Object.assign(new Error("closed"), { name: "AbortError" });
    const writeText = vi.fn();
    stubDevice({ share: vi.fn().mockRejectedValue(abort), clipboard: { writeText } });
    const link = useShareLink();
    await link.share(PAYLOAD);
    expect(writeText).not.toHaveBeenCalled();
    expect(link.copied.value).toBe(false);
    expect(link.manualUrl.value).toBe("");
  });

  it("another share failure falls back to the copy path", async () => {
    const writeText = vi.fn().mockResolvedValue();
    stubDevice({ share: vi.fn().mockRejectedValue(new Error("denied")), clipboard: { writeText } });
    const link = useShareLink();
    await link.share(PAYLOAD);
    expect(writeText).toHaveBeenCalledWith(PAYLOAD.url);
    expect(link.copied.value).toBe(true);
  });

  it("copy mode writes the url and sets copied for SHARE_COPIED_MS", async () => {
    const writeText = vi.fn().mockResolvedValue();
    stubDevice({ clipboard: { writeText } }); // no navigator.share
    const link = useShareLink();
    expect(link.mode).toBe("copy");
    await link.share(PAYLOAD);
    expect(writeText).toHaveBeenCalledWith(PAYLOAD.url);
    expect(link.copied.value).toBe(true);
    vi.advanceTimersByTime(SHARE_COPIED_MS - 1);
    expect(link.copied.value).toBe(true);
    vi.advanceTimersByTime(1);
    expect(link.copied.value).toBe(false);
  });

  it("copy mode calls writeText before any await", () => {
    const writeText = vi.fn().mockResolvedValue();
    stubDevice({ clipboard: { writeText } });
    useShareLink().share(PAYLOAD); // not awaited
    expect(writeText).toHaveBeenCalledTimes(1);
  });

  it("closing the scope clears the Link copied timer", async () => {
    stubDevice({ clipboard: { writeText: vi.fn().mockResolvedValue() } });
    const scope = effectScope();
    const link = scope.run(() => useShareLink());
    await link.share(PAYLOAD);
    expect(vi.getTimerCount()).toBe(1);
    scope.stop();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("a mouse device with navigator.share still copies", () => {
    stubDevice({ share: vi.fn(), clipboard: { writeText: vi.fn() }, coarse: false });
    expect(useShareLink().mode).toBe("copy");
  });

  it("a second tap restarts the timer", async () => {
    stubDevice({ clipboard: { writeText: vi.fn().mockResolvedValue() } });
    const link = useShareLink();
    await link.share(PAYLOAD);
    vi.advanceTimersByTime(2000);
    await link.share(PAYLOAD);
    vi.advanceTimersByTime(2000);
    expect(link.copied.value).toBe(true);
    vi.advanceTimersByTime(1000);
    expect(link.copied.value).toBe(false);
  });

  it("no navigator.clipboard sets manualUrl", async () => {
    stubDevice({ clipboard: undefined });
    const link = useShareLink();
    await link.share(PAYLOAD);
    expect(link.manualUrl.value).toBe(PAYLOAD.url);
    expect(link.copied.value).toBe(false);
  });

  it("a refused writeText sets manualUrl", async () => {
    stubDevice({ clipboard: { writeText: vi.fn().mockRejectedValue(new Error("NotAllowedError")) } });
    const link = useShareLink();
    await link.share(PAYLOAD);
    expect(link.manualUrl.value).toBe(PAYLOAD.url);
    expect(link.copied.value).toBe(false);
  });

  it("no window.matchMedia means copy mode", () => {
    stubDevice({ share: vi.fn(), clipboard: { writeText: vi.fn() }, matchMedia: false });
    expect(useShareLink().mode).toBe("copy");
  });
});
