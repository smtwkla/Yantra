import { describe, expect, it } from "vitest";
import { canOpenRoute, canSeeNavItem, homePath, isActivePath, landingNavItem, landingPath, navItems } from "../src/stores/navigation.js";

// What /api/auth/me returns per role — kept equal to backend/tests/test_rbac.py's role matrix.
// From S011 a site role's keys come from its membership; the manager's breadth is "all units"
// there, not equipment:read_all_units (IT admin's alone).  S017: ticket:read and ticket:raise
// for every maintenance role, the supervisor and IT admin; not the storekeeper.
const TICKETS = ["ticket:read", "ticket:raise"];
const OPERATOR = ["equipment:read", "masters:read", ...TICKETS];
const STOREKEEPER = ["equipment:read", "masters:read"];
const SUPERVISOR = OPERATOR;
const ENGINEER = [
  "equipment:read", "equipment:edit", "masters:read", "people:assign_technicians", "people:edit", ...TICKETS,
];
const MANAGER = [
  "equipment:edit", "equipment:purge_documents", "equipment:read", "masters:read", "people:assign_technicians",
  "people:edit", "settings:read", ...TICKETS,
];
const IT_ADMIN = [
  "equipment:read", "equipment:read_all_units", "equipment:edit", "equipment:purge_documents", "masters:edit",
  "masters:read", "masters:read_senior", "settings:edit", "settings:read", "people:assign_technicians", "people:edit",
  ...TICKETS,
];

const visible = (perms) => navItems.filter((i) => canSeeNavItem(i, perms)).map((i) => i.name);

describe("navigation permissions", () => {
  it("maint_operator sees Me, Equipment, Tickets and Masters, and cannot open Settings", () => {
    expect(visible(OPERATOR)).toEqual(["me", "equipment", "tickets", "masters"]);
    expect(canOpenRoute("settings", OPERATOR)).toBe(false);
  });

  it("Me is first for every role with ticket:read; manager and IT admin also see Settings (S035)", () => {
    expect(visible(ENGINEER)).toEqual(["me", "equipment", "tickets", "masters"]);
    expect(visible(MANAGER)).toEqual(["me", "equipment", "tickets", "masters", "settings"]);
    expect(visible(IT_ADMIN)).toEqual(["me", "equipment", "tickets", "masters", "settings"]);
  });

  it("the storekeeper sees no Tickets and cannot open the list (S017 user decision 7)", () => {
    expect(visible(STOREKEEPER)).toEqual(["equipment", "masters"]);
    expect(canOpenRoute("tickets", STOREKEEPER)).toBe(false);
    expect(canOpenRoute("me", STOREKEEPER)).toBe(false); // S031
  });

  it("everyone with ticket:read lands on Me; the storekeeper lands on Equipment (S035)", () => {
    for (const perms of [OPERATOR, SUPERVISOR, ENGINEER, MANAGER, IT_ADMIN]) {
      expect(landingPath(perms)).toBe("/me");
    }
    expect(landingPath(STOREKEEPER)).toBe("/equipment");
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

  it("the home path is the landing page, or Equipment when the user has none (S035)", () => {
    expect(homePath(OPERATOR)).toBe("/me");
    expect(homePath(STOREKEEPER)).toBe("/equipment");
    expect(homePath([])).toBe("/equipment");
  });

  it("the landing nav item is Me for roles with ticket:read, Equipment for the storekeeper", () => {
    for (const perms of [OPERATOR, SUPERVISOR, ENGINEER, MANAGER, IT_ADMIN]) {
      expect(landingNavItem(perms)).toBe(navItems[0]);
      expect(landingNavItem(perms).label).toBe("Me");
    }
    expect(landingNavItem(STOREKEEPER).label).toBe("Equipment");
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
