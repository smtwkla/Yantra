/**
 * Navigation items — single source of truth for sidebar and bottom nav.
 *
 * perm:  minimum permission to show the item (null = always visible).
 * perms: alternatives — the item shows when the user holds ANY one of them.
 */

export const navItems = [
  { name: "me", path: "/me", icon: "fa-solid fa-user", label: "Me", perm: "ticket:read" },
  { name: "equipment", path: "/equipment", icon: "fa-solid fa-gears", label: "Equipment", perm: "equipment:read" },
  { name: "tickets", path: "/tickets", icon: "fa-solid fa-triangle-exclamation", label: "Tickets", perm: "ticket:read" },
  // S050: every equipment:read holder; the storekeeper and IT admin see only the Register tab
  { name: "readings", path: "/readings", icon: "fa-solid fa-gauge", label: "Readings", perm: "equipment:read" },
  // S064 UX-12: only the people who maintain masters data see the item (and may open the route);
  // masters:read stays every role's for the pick-lists
  {
    name: "masters", path: "/masters", icon: "yi-icon yi-table-edit", label: "Masters",
    perms: ["masters:edit", "equipment:edit", "people:edit", "failure_codes:edit"],
  },
  { name: "settings", path: "/settings", icon: "fa-solid fa-gear", label: "Settings", perm: "settings:read" },
];

/** True when the user's permission list allows the nav item to be shown. */
export function canSeeNavItem(item, permissions) {
  if (item.perms) return item.perms.some((p) => permissions.includes(p));
  if (!item.perm) return true;
  return permissions.includes(item.perm);
}

/**
 * Whether the route ``name`` may be opened. Routes that are nav items follow
 * the item's permission; routes outside the nav are allowed.
 */
export function canOpenRoute(name, permissions) {
  const item = navItems.find((i) => i.name === name);
  return !item || canSeeNavItem(item, permissions);
}

/** The first nav item the user may see — the landing page; null when none. */
export function landingNavItem(permissions) {
  return navItems.find((i) => canSeeNavItem(i, permissions)) ?? null;
}

/** Path of the landing page; null when the user has none. */
export function landingPath(permissions) {
  return landingNavItem(permissions)?.path ?? null;
}

/** Where "/" goes after login: the landing page, or Equipment (its "no access" screen shows there) when none. */
export function homePath(permissions) {
  return landingPath(permissions) ?? "/equipment";
}

/** Whether a nav item is the current page — also true on its sub-pages (/equipment/5 → Equipment). */
export function isActivePath(routePath, itemPath) {
  return routePath === itemPath || routePath.startsWith(`${itemPath}/`);
}
