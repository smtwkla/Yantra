/**
 * Date formatting — display only, no timezone conversion.
 *
 * The API sends IST datetimes as "YYYY-MM-DDTHH:MM:SS+05:30" (db_helpers.row_to_dict).
 * They are shown as-is: DD-MM-YYYY HH:MM, no TZ suffix.
 */

const ISO_RE = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/;

/** "2026-10-12T08:05:00+05:30" → "12-10-2026 08:05"; date-only → "12-10-2026"; else "". */
export function formatDateTime(value) {
  if (typeof value !== "string") return "";
  const m = ISO_RE.exec(value);
  if (!m) return "";
  const [, y, mo, d, h, mi] = m;
  const date = `${d}-${mo}-${y}`;
  return h ? `${date} ${h}:${mi}` : date;
}

/** The date part only: "2026-10-12T08:05:00+05:30" → "12-10-2026"; else "". */
export function formatDate(value) {
  return formatDateTime(value).slice(0, 10);
}
