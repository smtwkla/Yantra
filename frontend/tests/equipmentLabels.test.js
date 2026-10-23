import { describe, expect, it } from "vitest";
import {
  CRITICALITY_BADGE_CLASS, CRITICALITY_LABELS, LEVEL_LABELS, LIFECYCLE_BADGE_CLASS, LIFECYCLE_HELP, LIFECYCLE_LABELS,
  describeEvent,
} from "../src/utils/equipmentLabels.js";

// The enums of backend/equipment_core.py
const LEVELS = ["equipment", "component_unit", "component"];
const LIFECYCLES = ["in_service", "standby", "out_of_use", "scrapped"];
const CRITICALITIES = ["A", "B", "C"];

const ev = (event, old_value, new_value) => ({ event, old_value, new_value });

describe("label maps", () => {
  it("cover every enum value of S002", () => {
    expect(Object.keys(LEVEL_LABELS).sort()).toEqual([...LEVELS].sort());
    for (const map of [LIFECYCLE_LABELS, LIFECYCLE_HELP, LIFECYCLE_BADGE_CLASS]) {
      expect(Object.keys(map).sort()).toEqual([...LIFECYCLES].sort());
    }
    for (const map of [CRITICALITY_LABELS, CRITICALITY_BADGE_CLASS]) {
      expect(Object.keys(map).sort()).toEqual([...CRITICALITIES].sort());
    }
  });
});

describe("describeEvent", () => {
  it("created ignores old_value", () => {
    expect(describeEvent(ev("created", null, "SMTW.FWMILL.VBM001"))).toBe("Created");
    expect(describeEvent(ev("created", "anything", "SMTW.FWMILL.VBM001"))).toBe("Created");
  });

  it("moves show the old and new path", () => {
    expect(describeEvent(ev("moved_unit", "SMTW.FWMILL.VBM001", "SSVT.SHOP.VBM001")))
      .toBe("Moved: SMTW.FWMILL.VBM001 → SSVT.SHOP.VBM001");
    expect(describeEvent(ev("moved_parent", "SMTW.FWMILL.VBM001.DRV002", "SMTW.FWMILL.VBM002.DRV005")))
      .toBe("Moved: SMTW.FWMILL.VBM001.DRV002 → SMTW.FWMILL.VBM002.DRV005");
  });

  it("lifecycle uses the labels", () => {
    expect(describeEvent(ev("lifecycle", "in_service", "standby"))).toBe("Lifecycle: In service → Standby");
    expect(describeEvent(ev("lifecycle", "out_of_use", "scrapped"))).toBe("Lifecycle: Out of use → Scrapped");
  });

  it("criticality shows the literal inherit as Inherited", () => {
    expect(describeEvent(ev("criticality", "B", "A"))).toBe("Criticality: B → A");
    expect(describeEvent(ev("criticality", "inherit", "A"))).toBe("Criticality: Inherited → A");
    expect(describeEvent(ev("criticality", "A", "inherit"))).toBe("Criticality: A → Inherited");
  });

  it("class shows the class codes", () => {
    expect(describeEvent(ev("class", "VBM", "HP"))).toBe("Class: VBM → HP");
  });

  it("type shows the type names, and none as None", () => {
    expect(describeEvent(ev("type", "none", "Closed execution"))).toBe("Type: None → Closed execution");
    expect(describeEvent(ev("type", "Closed execution", "Open execution")))
      .toBe("Type: Closed execution → Open execution");
    expect(describeEvent(ev("type", "Open execution", "none"))).toBe("Type: Open execution → None");
  });

  it("model shows the model labels", () => {
    expect(describeEvent(ev("model", "Atlas Copco GA37", "Atlas Copco GA55")))
      .toBe("Model: Atlas Copco GA37 → Atlas Copco GA55");
  });

  it("an unknown event is shown by name", () => {
    expect(describeEvent(ev("mystery", null, null))).toBe("mystery");
  });
});
