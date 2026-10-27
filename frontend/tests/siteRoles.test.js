import { describe, expect, it } from "vitest";
import {
  describeSiteRow, displayRoleLabel, roleLabel, siteRoleChoices, SITE_ROLES, TECHNICIAN,
} from "../src/utils/siteRoles.js";

describe("displayRoleLabel (S064 UX-26)", () => {
  it("names site roles as the Team dialog does, and the token roles", () => {
    expect(displayRoleLabel("maint_engineer")).toBe("Engineer");
    expect(displayRoleLabel(TECHNICIAN)).toBe("Technician");
    expect(displayRoleLabel("it_admin")).toBe("IT admin");
    expect(displayRoleLabel("admin")).toBe("Admin");
  });

  it("shows any other value as it is", () => {
    expect(displayRoleLabel("maintenance_team")).toBe("maintenance_team");
  });
});

describe("site roles", () => {
  it("labels every role, and a legacy row without one", () => {
    expect(roleLabel("maint_supervisor")).toBe("Supervisor");
    expect(roleLabel(TECHNICIAN)).toBe("Technician");
    expect(roleLabel(null)).toBe("No role");
    expect(SITE_ROLES.map((r) => r.value)).toContain("maint_storekeeper");
  });

  it("describes a row with its units or all units", () => {
    expect(describeSiteRow({ site_code: "SMTW", role: TECHNICIAN, all_units: false }, ["FWMILL", "MCC1"]))
      .toBe("SMTW Technician (FWMILL, MCC1)");
    expect(describeSiteRow({ site_code: "VEL", role: "maint_manager", all_units: true }, []))
      .toBe("VEL Manager (all units)");
  });
});

describe("site role choices (S017 user decision 5)", () => {
  const values = (choices) => choices.map((r) => r.value);

  it("IT admin: every role with a login, Technician or Operator without", () => {
    expect(values(siteRoleChoices(true, true))).toEqual(SITE_ROLES.map((r) => r.value));
    expect(values(siteRoleChoices(true, false))).toEqual([TECHNICIAN, "maint_operator"]);
  });

  it("an engineer: Technician only, login or not", () => {
    expect(values(siteRoleChoices(false, true))).toEqual([TECHNICIAN]);
    expect(values(siteRoleChoices(false, false))).toEqual([TECHNICIAN]);
  });
});
