/**
 * A refusal is always in view (docs/steps/S026-refusal-in-view/1-brief.md § 4.3).
 *
 * Finds the first refused field or message inside `container` (page order), scrolls it to the
 * middle of whatever scrolls (the dialog body or the page) and puts the cursor in its field.
 * Plain DOM, no Vue: FormModal and the Raise ticket page both call it.
 */

const FIRST_REFUSAL = ".is-invalid, .invalid-feedback.d-block, .alert-danger";
const FOCUSABLE = "input, select, textarea, button";

export function revealError(container) {
  const target = container?.querySelector(FIRST_REFUSAL);
  if (!target) return;
  // Instant, not smooth: a smooth scroll would still be moving when a test (or the user) looks
  target.scrollIntoView({ block: "center" });
  // preventScroll: the scroll above is the one that counts; focus() would otherwise put the field at the edge
  if (target.classList.contains("is-invalid")) {
    target.focus({ preventScroll: true });
  } else if (target.classList.contains("invalid-feedback")) {
    target.parentElement?.querySelector(FOCUSABLE)?.focus({ preventScroll: true });
  }
  // The top .alert-danger bar: scrolled to only, there is nothing to type in it
}
