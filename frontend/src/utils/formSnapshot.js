/**
 * formSnapshot — a string that compares two states of a form by value, so a
 * dialog can tell whether the user changed anything (changed and changed back
 * counts as unchanged).
 *
 * Plain JSON.stringify writes a File as {} (choosing a file would not count)
 * and a Set as {}, so both get a replacer. A Set is sorted only to make the
 * string stable. `undefined` values drop out ({a: undefined} equals {}); the
 * forms use "" and null, so this is harmless.
 */

const numericOrTextOrder = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

function replacer(_key, value) {
  if (value instanceof File) return `file:${value.name}:${value.size}:${value.lastModified}`;
  if (value instanceof Set) return [...value].sort(numericOrTextOrder);
  return value;
}

export function formSnapshot(value) {
  return JSON.stringify(value, replacer);
}
