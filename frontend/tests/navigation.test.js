import { describe, expect, it } from "vitest";
import { canOpenRoute, canSeeNavItem, isActivePath, landingNavItem, landingPath, navItems } from "../src/stores/navigation.js";

// What /api/auth/me returns per role — kept equal to backend/tests/test_rbac.py's role matrix.
// From S011 a site role's keys come from its membership; the manager's breadth is "all units"
// there, not equipment:read_all_units (IT admin's alone).
const OPERATOR = ["equipment:read", "masters:read"];
const SUPERVISOR = OPERATOR;
const ENGINEER = ["equipment:read", "equipment:edit", "masters:read", "people:assign_technicians", "people:edit"];
const MANAGER = [
  "equipment:edit", "equipment:purge_documents", "equipment:read", "masters:read", "people:assign_technicians",
  "people:edit", "settings:read",
];
const IT_ADMIN = [
  "equipment:read", "equipment:read_all_units", "equipment:edit", "equipment:purge_documents", "masters:edit",
  "masters:read", "masters:read_senior", "settings:edit", "settings:read", "people:assign_technicians", "people:edit",
];

const visible = (perms) => navItems.filter((i) => canSeeNavItem(i, perms)).map((i) => i.name);

describe("navigation permissions", () => {
  it("maint_operator sees Equipment and Masters, and cannot open Settings", () => {
    expect(visible(OPERATOR)).toEqual(["equipment", "masters"]);
    expect(canOpenRoute("settings", OPERATOR)).toBe(false);
  });

  it("Equipment is first for every role; manager and IT admin also see Settings", () => {
    expect(visible(ENGINEER)).toEqual(["equipment", "masters"]);
    expect(visible(MANAGER)).toEqual(["equipment", "masters", "settings"]);
    expect(visible(IT_ADMIN)).toEqual(["equipment", "masters", "settings"]);
  });

  it("everyone with a role lands on Equipment", () => {
    for (const perms of [OPERATOR, SUPERVISOR, ENGINEER, MANAGER, IT_ADMIN]) {
      expect(landingPath(perms)).toBe("/equipment");
    }
  });

  it("an item stays active on its sub-pages, but not on a path that merely starts the same", () => {
    expect(isActivePath("/equipment", "/equipment")).toBe(true);
    expect(isActivePath("/equipment/5", "/equipment")).toBe(true);
    expect(isActivePath("/equipmentx", "/equipment")).toBe(false);
    expect(isActivePath("/masters", "/equipment")).toBe(false);
  });

  it("routes outside the nav guard themselves", () => {
    expect(canOpenRoute("not-a-nav-item", OPERATOR)).toBe(true);
  });

  it("no permissions → no landing page", () => {
    expect(landingPath([])).toBeNull();
    expect(landingNavItem([])).toBeNull();
  });

  it("the landing nav item is Equipment for every role", () => {
    for (const perms of [OPERATOR, SUPERVISOR, ENGINEER, MANAGER, IT_ADMIN]) {
      expect(landingNavItem(perms)).toBe(navItems[0]);
      expect(landingNavItem(perms).label).toBe("Equipment");
    }
  });

  it("the not-found route opens for every role, and for none", () => {
    for (const perms of [OPERATOR, SUPERVISOR, ENGINEER, MANAGER, IT_ADMIN, []]) {
      expect(canOpenRoute("not-found", perms)).toBe(true);
    }
  });

  it("perms alternatives: any one of them is enough", () => {
    const item = { name: "x", perms: ["a:read", "b:read"] };
    expect(canSeeNavItem(item, ["b:read"])).toBe(true);
    expect(canSeeNavItem(item, ["c:read"])).toBe(false);
  });
});
