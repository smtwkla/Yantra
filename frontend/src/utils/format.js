/**
 * Number formatting — display only.
 */

const KB = 1024;
const MB = 1024 * 1024;

/** A file size: under 1 KB in bytes, then KB or MB with one decimal (1536 → "1.5 KB"). */
export function formatBytes(n) {
  if (typeof n !== "number" || !Number.isFinite(n) || n < 0) return "";
  if (n < KB) return `${n} B`;
  if (n < MB) return `${(n / KB).toFixed(1)} KB`;
  return `${(n / MB).toFixed(1)} MB`;
}
