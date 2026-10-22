import { computed, ref } from "vue";

/** How many entries a long list shows before *Show all*. */
export const SHOWN_AT_FIRST = 10;

/**
 * The first `limit` entries of a list, and a toggle that expands it in place (the equipment
 * history, the ticket timeline). `items` is a getter, so the list follows its source.
 */
export function useShowMore(items, limit = SHOWN_AT_FIRST) {
  const expanded = ref(false);
  const all = computed(() => items() ?? []);
  const shown = computed(() => (expanded.value ? all.value : all.value.slice(0, limit)));
  const canExpand = computed(() => all.value.length > limit);
  const toggle = () => { expanded.value = !expanded.value; };
  const toggleLabel = computed(() => (expanded.value ? "Show fewer" : `Show all ${all.value.length}`));
  return { shown, canExpand, toggle, toggleLabel };
}
