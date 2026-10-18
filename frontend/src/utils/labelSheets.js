/**
 * QR label sheets (docs/steps/S014-qr-labels/1-brief.md) — pure helpers for the print page.
 */

export const LABELS_PER_SHEET = 15; // A4: 3 across, 5 down, 52 mm squares
export const MAX_LABELS = 300;      // the API's cap per request

const POSITIVE_INTEGER = /^[1-9][0-9]*$/;

/**
 * The print page's query → `{ ids, withParts }`, or null when the link holds no valid list.
 * `ids=12,15,40` (repeats dropped, order kept); `parts=1` adds each node's parts.
 */
export function parseLabelQuery(query) {
  const raw = typeof query?.ids === "string" ? query.ids : "";
  const parts = raw.split(",").map((p) => p.trim());
  if (raw === "" || !parts.every((p) => POSITIVE_INTEGER.test(p))) return null;
  const ids = [...new Set(parts.map(Number))];
  return { ids, withParts: query.parts === "1" };
}

/** Labels in sheets of `perSheet`: 16 labels → [15, 1]; none → []. */
export function chunkSheets(labels, perSheet = LABELS_PER_SHEET) {
  const sheets = [];
  for (let i = 0; i < labels.length; i += perSheet) sheets.push(labels.slice(i, i + perSheet));
  return sheets;
}

/** The print page's address for these ids, for a new tab. */
export function labelsPath(ids, withParts = false) {
  return `/labels?ids=${ids.join(",")}&parts=${withParts ? "1" : "0"}`;
}
