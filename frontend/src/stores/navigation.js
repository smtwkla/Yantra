/**
 * Navigation items — single source of truth for sidebar and bottom nav.
 *
 * perm:  minimum permission to show the item (null = always visible).
 * perms: alternatives — the item shows when the user holds ANY one of them.
 */

export const navItems = [
  { name: "masters", path: "/masters", icon: "fa-solid fa-industry", label: "Masters", perm: "masters:read" },
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

/** Path of the first nav item the user may see — the landing page; null when none. */
export function landingPath(permissions) {
  const item = navItems.find((i) => canSeeNavItem(i, permissions));
  return item ? item.path : null;
}
