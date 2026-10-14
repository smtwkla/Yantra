import { onBeforeUnmount } from "vue";

/**
 * Delay `callback` until `delayMs` after the last schedule() call (search boxes).
 * A pending call is cancelled when the component unmounts.
 */
export function useDebounced(callback, delayMs) {
  let timer = null;
  const cancel = () => clearTimeout(timer);
  const schedule = () => {
    cancel();
    timer = setTimeout(callback, delayMs);
  };
  onBeforeUnmount(cancel);
  return { schedule, cancel };
}
