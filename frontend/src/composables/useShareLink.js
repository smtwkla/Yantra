import { getCurrentScope, onScopeDispose, ref } from "vue";

/** How long "Link copied" stays on screen (S066). */
export const SHARE_COPIED_MS = 3000;

/**
 * S066: send a link the easiest way the device allows.
 *
 * `mode` is "share" on a phone (the browser has `navigator.share` and the main pointer is coarse),
 * else "copy"; it is picked once, when the composable is created. `share({ title, text, url })`
 * opens the share sheet, or copies `url`. `copied` is true for SHARE_COPIED_MS after a copy.
 * `manualUrl` holds the link when the copy could not run, so the screen can show it to copy by hand.
 *
 * Safari allows `navigator.share` and `clipboard.writeText` only inside the tap's user activation,
 * so `share()` makes its call before any `await`.
 */
export function useShareLink() {
  const coarsePointer = window.matchMedia?.("(pointer: coarse)")?.matches ?? false;
  const mode = typeof navigator.share === "function" && coarsePointer ? "share" : "copy";
  const copied = ref(false);
  const manualUrl = ref("");
  let timer = null;

  function stopTimer() {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  }

  async function copy(url) {
    stopTimer();
    copied.value = false;
    manualUrl.value = "";
    if (typeof navigator.clipboard?.writeText !== "function") {
      manualUrl.value = url;
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      manualUrl.value = url; // refused: the user copies by hand
      return;
    }
    copied.value = true;
    timer = setTimeout(() => {
      copied.value = false;
      timer = null;
    }, SHARE_COPIED_MS);
  }

  async function share(payload) {
    if (mode === "copy") return copy(payload.url);
    try {
      await navigator.share(payload);
    } catch (err) {
      if (err?.name === "AbortError") return; // the user closed the sheet
      await copy(payload.url);
    }
  }

  if (getCurrentScope()) onScopeDispose(stopTimer);

  return { mode, share, copied, manualUrl };
}
