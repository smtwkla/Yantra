/**
 * Site roles — labels and order for the Team dialog (S011 A1). The backend's
 * config_rbac.SITE_ROLES is the source of truth and validates every save; this list only
 * names the roles for display, in the same order.
 */

export const TECHNICIAN = "maint_technician";
export const OPERATOR = "maint_operator";

/** The roles a person without a login may hold (config_rbac.NO_LOGIN_ROLES; S017 user decision 5). */
export const NO_LOGIN_ROLES = [TECHNICIAN, OPERATOR];

export const SITE_ROLES = [
  { value: "maint_manager", label: "Manager" },
  { value: "maint_engineer", label: "Engineer" },
  { value: "maint_supervisor", label: "Supervisor" },
  { value: TECHNICIAN, label: "Technician" },
  { value: OPERATOR, label: "Operator" },
  { value: "maint_storekeeper", label: "Storekeeper" },
];

/** "Technician", or "No role" for a legacy row (unit rows moved from the old unit access). */
export function roleLabel(role) {
  return SITE_ROLES.find((r) => r.value === role)?.label ?? (role ? role : "No role");
}

/** A site row as text: "SMTW Technician (FWMILL, MCC1)" or "VEL Manager (all units)". */
export function describeSiteRow(row, unitCodes) {
  const where = row.all_units ? "all units" : unitCodes.join(", ") || "no units";
  return `${row.site_code} ${roleLabel(row.role)} (${where})`;
}

/**
 * The roles the Team dialog offers for a site row. IT admin: every role for a person with a
 * login, Technician or Operator without one (S017 user decision 5). Anyone else (an engineer
 * assigning at their site): Technician only (S011 A1, gate A).
 */
export function siteRoleChoices(isItAdmin, hasLogin) {
  if (!isItAdmin) return SITE_ROLES.filter((r) => r.value === TECHNICIAN);
  return hasLogin ? SITE_ROLES : SITE_ROLES.filter((r) => NO_LOGIN_ROLES.includes(r.value));
}
