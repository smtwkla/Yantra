import { describe, expect, it } from "vitest";
import {
  NO_MODEL, classHasNoModel, modelChoices, noModelClassChoices, noModelDefaults, noModelTypeChoices, pickerLabel,
} from "../src/utils/modelPicker.js";

const model = (id, classId, overrides = {}) => ({
  id, class_id: classId, class_code: classId === 1 ? "CMP" : "HP", label: `Maker M${id}`,
  type_name: null, active: 1, ...overrides,
});

const GA37 = model(1, 1, { label: "Atlas Copco GA37", type_name: "Screw compressor" });
const HYP = model(2, 2, { label: "SMTW (in-house) SMTW-HYP-01" });
const OLD = model(3, 1, { label: "Atlas Copco GA11", active: 0 });
const MODELS = [GA37, HYP, OLD];

const ids = (choices) => choices.map((c) => c.id);

describe("pickerLabel", () => {
  it("reads Maker designation — CLASS / Type", () => {
    expect(pickerLabel(GA37)).toBe("Atlas Copco GA37 — CMP / Screw compressor");
  });

  it("leaves the type out when the model has none", () => {
    expect(pickerLabel(HYP)).toBe("SMTW (in-house) SMTW-HYP-01 — HP");
  });
});

describe("modelChoices", () => {
  it("offers active models only", () => {
    expect(ids(modelChoices(MODELS))).toEqual([1, 2]);
  });

  it("keeps the node's current inactive model and marks it", () => {
    const choices = modelChoices(MODELS, { currentId: 3 });
    expect(ids(choices)).toEqual([1, 2, 3]);
    expect(choices[2].text).toBe("Atlas Copco GA11 — CMP (inactive)");
  });

  it("narrows to the class filter's class", () => {
    expect(ids(modelChoices(MODELS, { classId: 2 }))).toEqual([2]);
    expect(ids(modelChoices(MODELS, { classId: "" }))).toEqual([1, 2]);
  });

  it("keeps the model already picked when the filter is on another class", () => {
    expect(ids(modelChoices(MODELS, { classId: 2, selectedId: 1 }))).toEqual([1, 2]);
  });

  it("copes with a list not loaded yet", () => {
    expect(modelChoices(null)).toEqual([]);
  });

  // S033: a component-unit may have no model
  it("offers No model first for a component-unit only", () => {
    expect(modelChoices(MODELS, { level: "component_unit" })).toEqual([
      { id: NO_MODEL, text: "No model" }, ...modelChoices(MODELS),
    ]);
    expect(ids(modelChoices(MODELS, { level: "equipment" }))).toEqual([1, 2]);
    expect(ids(modelChoices(MODELS, { level: "component" }))).toEqual([1, 2]);
    expect(NO_MODEL).toBe("none");
  });
});

describe("noModelClassChoices", () => {
  const CLASSES = [
    { id: 1, code: "GB", name: "Gearbox", active: 1 },
    { id: 2, code: "MO", name: "Motor", active: 0 },
  ];

  it("offers active classes, and keeps the current inactive one marked", () => {
    expect(noModelClassChoices(CLASSES)).toEqual([{ id: 1, text: "GB — Gearbox" }]);
    expect(noModelClassChoices(CLASSES, 2)).toEqual([
      { id: 1, text: "GB — Gearbox" }, { id: 2, text: "MO — Motor (inactive)" },
    ]);
    expect(noModelClassChoices(null)).toEqual([]);
  });
});

describe("noModelTypeChoices", () => {
  const TYPES = [
    { id: 5, class_id: 1, name: "Helical", active: 1 },
    { id: 6, class_id: 1, name: "Worm", active: 0 },
    { id: 7, class_id: 2, name: "Induction", active: 1 },
  ];

  it("offers the active types of the picked class, and keeps the current inactive one marked", () => {
    expect(noModelTypeChoices(TYPES, 1)).toEqual([{ id: 5, text: "Helical" }]);
    expect(noModelTypeChoices(TYPES, 1, 6)).toEqual([{ id: 5, text: "Helical" }, { id: 6, text: "Worm (inactive)" }]);
    expect(noModelTypeChoices(TYPES, 2, 6)).toEqual([{ id: 7, text: "Induction" }]);
  });

  it("offers none until a class is picked", () => {
    expect(noModelTypeChoices(TYPES, "")).toEqual([]);
  });
});

describe("classHasNoModel", () => {
  it("is true only for a chosen class without an active model", () => {
    expect(classHasNoModel(MODELS, 1)).toBe(false);
    expect(classHasNoModel([OLD], 1)).toBe(true);
    expect(classHasNoModel(MODELS, 9)).toBe(true);
    expect(classHasNoModel(MODELS, "")).toBe(false);
  });
});

describe("noModelDefaults", () => {
  it("takes the class filter, and no type when the filter is another class than the node's", () => {
    expect(noModelDefaults({ classFilter: 2, currentClassId: 1, currentTypeId: 5 })).toEqual({ class_id: 2, type_id: "" });
  });

  it("keeps the node's class and type on edit with no filter", () => {
    expect(noModelDefaults({ classFilter: "", currentClassId: 1, currentTypeId: 5 })).toEqual({ class_id: 1, type_id: 5 });
  });

  it("keeps the node's type when the filter is the node's own class", () => {
    expect(noModelDefaults({ classFilter: 1, currentClassId: 1, currentTypeId: 5 })).toEqual({ class_id: 1, type_id: 5 });
  });

  it("starts empty on create with no filter", () => {
    expect(noModelDefaults({ classFilter: "", currentClassId: null, currentTypeId: null })).toEqual({ class_id: "", type_id: "" });
  });

  it("gives No type when the node has no type", () => {
    expect(noModelDefaults({ classFilter: "", currentClassId: 1, currentTypeId: null })).toEqual({ class_id: 1, type_id: "" });
  });
});
