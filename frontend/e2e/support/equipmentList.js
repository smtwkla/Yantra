// The equipment list on any width (S064 UX-08): below md the rows are cards and the selects are
// folded behind "Filters (n)"; from md up the rows are the table's and the selects are inline.
import { expect } from "./test.js";

/** The list's rows that the user sees: the table's on a desktop, the cards on a phone. */
export function equipmentRows(page) {
  return page.locator('[data-test="equipment-row"]:visible');
}

/** The visible row of `machine` (its code is on the row). */
export function equipmentRow(page, machine) {
  return equipmentRows(page).filter({ hasText: machine.code });
}

/** Opens the phone's folded filters, so a select can be used; a no-op from md up (no button). */
export async function openFilters(page) {
  // The search box shows on every width: once it is there, the toolbar is rendered
  await expect(page.getByRole("searchbox", { name: "Search" })).toBeVisible();
  const toggle = page.getByRole("button", { name: /^Filters \(\d+\)/ });
  if (!(await toggle.isVisible())) return;
  if ((await toggle.getAttribute("aria-expanded")) !== "true") await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
}
