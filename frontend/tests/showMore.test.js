import { describe, expect, it } from "vitest";
import { ref } from "vue";
import { SHOWN_AT_FIRST, useShowMore } from "../src/composables/useShowMore.js";

const numbers = (n) => Array.from({ length: n }, (_, i) => i);

describe("useShowMore", () => {
  it("shows a short list whole, with nothing to expand", () => {
    const { shown, canExpand } = useShowMore(() => numbers(3));
    expect(shown.value).toEqual([0, 1, 2]);
    expect(canExpand.value).toBe(false);
  });

  it("shows exactly the limit with nothing to expand", () => {
    const { shown, canExpand } = useShowMore(() => numbers(SHOWN_AT_FIRST));
    expect(shown.value).toHaveLength(SHOWN_AT_FIRST);
    expect(canExpand.value).toBe(false);
  });

  it("cuts a long list to the first entries, and the toggle expands and folds it", () => {
    const { shown, canExpand, toggle, toggleLabel } = useShowMore(() => numbers(12));
    expect(shown.value).toEqual(numbers(10));
    expect(canExpand.value).toBe(true);
    expect(toggleLabel.value).toBe("Show all 12");
    toggle();
    expect(shown.value).toEqual(numbers(12));
    expect(toggleLabel.value).toBe("Show fewer");
    toggle();
    expect(shown.value).toHaveLength(10);
  });

  it("follows its source and treats a missing list as empty", () => {
    const source = ref(null);
    const { shown, canExpand } = useShowMore(() => source.value);
    expect(shown.value).toEqual([]);
    source.value = numbers(11);
    expect(shown.value).toHaveLength(10);
    expect(canExpand.value).toBe(true);
  });
});
