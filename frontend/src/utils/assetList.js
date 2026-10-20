/**
 * Printable asset list (docs/steps/S015-asset-list/1-brief.md) — pure helpers for the print page.
 * The page's link uses the equipment list's own query keys, so the list's filters carry over.
 */

import { STATUS_LABELS } from "./equipmentLabels";

// The list's filter keys that choose machines; level, q and page are deliberately not here (§ 4)
const FILTER_KEYS = ["site_id", "unit_id", "class_id", "type_id", "status", "criticality"];

const text = (value) => (typeof value === "string" ? value : "");

/** The print page's address for the list's `route.query`, for a new tab. */
export function assetListPath(listQuery, withParts = false, checklist = false) {
  const params = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    if (text(listQuery?.[key])) params.set(key, listQuery[key]);
  }
  if (listQuery?.scrapped === "1") params.set("scrapped", "1");
  if (withParts) params.set("parts", "1");
  if (checklist) params.set("check", "1");
  const query = params.toString();
  return query ? `/asset-list?${query}` : "/asset-list";
}

/**
 * The print page's query → `{ params, withParts, checklist }`: `params` are the API's filters
 * (unknown keys dropped); the switches default to off. `include_scrapped` is sent for
 * `scrapped=1` or `status=scrapped`, the list's own rule.
 */
export function parseAssetListQuery(query) {
  const params = {};
  for (const key of FILTER_KEYS) {
    if (text(query?.[key])) params[key] = query[key];
  }
  if (query?.scrapped === "1" || params.status === "scrapped") params.include_scrapped = "1";
  return { params, withParts: query?.parts === "1", checklist: query?.check === "1" };
}

/**
 * The filter line of a section header, e.g. "Class: RPP · Status: In service"; "All equipment"
 * with no filter. Site and unit are not named (the header has them). `lookups` is
 * `{ classes, types }`, the masters lists (either may be null while loading).
 */
export function filtersLabel(params, lookups = {}) {
  const parts = [];
  if (params.class_id) {
    const found = (lookups.classes ?? []).find((c) => String(c.id) === String(params.class_id));
    parts.push(`Class: ${found ? found.code : `#${params.class_id}`}`);
  }
  if (params.type_id) {
    const found = (lookups.types ?? []).find((t) => String(t.id) === String(params.type_id));
    parts.push(`Type: ${found ? found.name : `#${params.type_id}`}`);
  }
  if (params.status) parts.push(`Status: ${STATUS_LABELS[params.status] ?? params.status}`);
  if (params.criticality) parts.push(`Criticality: ${params.criticality}`);
  // status=scrapped already says it
  if (params.include_scrapped && params.status !== "scrapped") parts.push("scrapped included");
  return parts.length ? parts.join(" · ") : "All equipment";
}
