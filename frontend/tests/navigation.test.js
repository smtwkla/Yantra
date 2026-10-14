import { describe, expect, it } from "vitest";
import { canOpenRoute, canSeeNavItem, landingPath, navItems } from "../src/stores/navigation.js";

// What /api/auth/me returns per role (backend config_rbac.py — see test_rbac.py's role matrix)
const OPERATOR = ["masters:read"];
const ENGINEER = ["equipment:edit", "masters:read"];
const MANAGER = ["equipment:edit", "masters:read", "settings:read"];
const IT_ADMIN = [
  "equipment:edit", "masters:edit", "masters:read", "masters:read_senior", "settings:edit", "settings:read",
];

const visible = (perms) => navItems.filter((i) => canSeeNavItem(i, perms)).map((i) => i.name);

describe("navigation permissions", () => {
  it("maint_operator sees Masters only and cannot open Settings", () => {
    expect(visible(OPERATOR)).toEqual(["masters"]);
    expect(canOpenRoute("settings", OPERATOR)).toBe(false);
  });

  it("manager and IT admin see Masters and Settings", () => {
    expect(visible(MANAGER)).toEqual(["masters", "settings"]);
    expect(visible(IT_ADMIN)).toEqual(["masters", "settings"]);
  });

  it("everyone with a role lands on Masters", () => {
    for (const perms of [OPERATOR, ENGINEER, MANAGER, IT_ADMIN]) {
      expect(landingPath(perms)).toBe("/masters");
    }
  });

  it("routes outside the nav guard themselves", () => {
    expect(canOpenRoute("not-a-nav-item", OPERATOR)).toBe(true);
  });

  it("no permissions → no landing page", () => {
    expect(landingPath([])).toBeNull();
  });

  it("perms alternatives: any one of them is enough", () => {
    const item = { name: "x", perms: ["a:read", "b:read"] };
    expect(canSeeNavItem(item, ["b:read"])).toBe(true);
    expect(canSeeNavItem(item, ["c:read"])).toBe(false);
  });
});
