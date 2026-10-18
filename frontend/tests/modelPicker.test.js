import { describe, expect, it } from "vitest";
import { classHasNoModel, modelChoices, pickerLabel } from "../src/utils/modelPicker.js";

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
});

describe("classHasNoModel", () => {
  it("is true only for a chosen class without an active model", () => {
    expect(classHasNoModel(MODELS, 1)).toBe(false);
    expect(classHasNoModel([OLD], 1)).toBe(true);
    expect(classHasNoModel(MODELS, 9)).toBe(true);
    expect(classHasNoModel(MODELS, "")).toBe(false);
  });
});
