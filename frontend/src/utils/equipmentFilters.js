/**
 * The equipment list's category filter (docs/steps/S063-equipment-category/1-brief.md § 5.4):
 * pure helpers for the class select under a chosen category. Ids come from the URL as strings
 * and from the API as numbers, so they are compared as strings.
 */

const same = (a, b) => String(a) === String(b);

/** A copy of `records`, active ones first, then by `key` (a select's order: classes, categories). */
export function activeFirstBy(records, key) {
  return [...(records ?? [])].sort((a, b) => Number(b.active) - Number(a.active) || a[key].localeCompare(b[key]));
}

/**
 * The class select's choices: every class without a category; with one, only its classes. A
 * chosen class outside it stays listed, last, so a hand-made URL never filters invisibly. Active
 * classes come first, then inactive ones, each by code.
 */
export function classChoicesFor(classes, categoryId, selectedClassId) {
  const all = activeFirstBy(classes, "code");
  if (!categoryId) return all;
  const shown = all.filter((c) => same(c.category_id, categoryId));
  const selected = all.find((c) => same(c.id, selectedClassId));
  if (selected && !shown.includes(selected)) shown.push(selected);
  return shown;
}

/** True when the chosen class is not in the chosen category, so choosing the category clears it. */
export function classOutsideCategory(classes, categoryId, classId) {
  if (!categoryId || !classId) return false;
  const found = (classes ?? []).find((c) => same(c.id, classId));
  return !found || !same(found.category_id, categoryId);
}
