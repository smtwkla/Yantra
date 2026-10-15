import { onBeforeUnmount } from "vue";

/** How long a search box waits after the last keystroke. */
export const SEARCH_DELAY_MS = 300;

/**
 * Delay `callback` until `delayMs` after the last schedule() call (search boxes).
 * A pending call is cancelled when the component unmounts.
 */
export function useDebounced(callback, delayMs = SEARCH_DELAY_MS) {
  let timer = null;
  const cancel = () => clearTimeout(timer);
  const schedule = () => {
    cancel();
    timer = setTimeout(callback, delayMs);
  };
  onBeforeUnmount(cancel);
  return { schedule, cancel };
}
