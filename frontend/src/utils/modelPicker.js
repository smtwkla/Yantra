/**
 * The equipment form's Model picker (docs/steps/S012-equipment-models/1-brief.md § 1.4):
 * the list it offers and how each model reads. Pure: no imports.
 *
 * A model item is the masters API's: {id, label, class_id, class_code, type_name, active, …}.
 *
 * A component-unit may have no model (S033): the picker then offers *No model* first, and the
 * form picks the class and type directly from noModelClassChoices / noModelTypeChoices.
 */

/** The Model select's value for "No model" (S033 § 1.5); model ids are numbers, so it never clashes. */
export const NO_MODEL = "none";

/** The one level that may have no model (S033 § 1.1). */
export const NO_MODEL_LEVEL = "component_unit";

/** "Atlas Copco GA37 — CMP / Screw compressor"; "… — HP" for a model without a type. */
export function pickerLabel(model) {
  const kind = model.type_name ? `${model.class_code} / ${model.type_name}` : model.class_code;
  return `${model.label} — ${kind}`;
}

// Active records, plus the node's current one when it is inactive: an unchanged inactive value is
// kept, so it stays listed and is marked
const activeOrCurrent = (items, currentId) => (items ?? []).filter((x) => x.active || x.id === currentId);
const inactiveMark = (x) => (x.active ? "" : " (inactive)");

/**
 * The models to offer, in the API's order (manufacturer, then designation):
 * - *No model* first, for a component-unit only (`level`; default: not offered);
 * - only active ones, except the node's current model (`currentId`, on edit), kept and marked
 *   "(inactive)" as classes and types are;
 * - of the class filter's class when one is chosen (`classId`, "" for all); the model now
 *   picked in the form (`selectedId`) stays listed, so the select never shows a blank.
 * Returns [{id, text}].
 */
export function modelChoices(models, { classId = "", currentId = null, selectedId = null, level = null } = {}) {
  const choices = activeOrCurrent(models, currentId)
    .filter((m) => classId === "" || m.class_id === classId || m.id === selectedId)
    .map((m) => ({ id: m.id, text: `${pickerLabel(m)}${inactiveMark(m)}` }));
  return level === NO_MODEL_LEVEL ? [{ id: NO_MODEL, text: "No model" }, ...choices] : choices;
}

/** True when a class is chosen in the filter and it has no active model yet (the form's hint). */
export function classHasNoModel(models, classId) {
  return classId !== "" && !(models ?? []).some((m) => m.active && m.class_id === classId);
}

/** The classes a component-unit without a model may pick: active ones, and its current one kept. [{id, text}] */
export function noModelClassChoices(classes, currentId = null) {
  return activeOrCurrent(classes, currentId).map((c) => ({ id: c.id, text: `${c.code} — ${c.name}${inactiveMark(c)}` }));
}

/** The types of `classId` it may pick, the same way; none until a class is picked. [{id, text}] */
export function noModelTypeChoices(types, classId, currentId = null) {
  return activeOrCurrent(types, currentId)
    .filter((t) => classId !== "" && t.class_id === classId)
    .map((t) => ({ id: t.id, text: `${t.name}${inactiveMark(t)}` }));
}

/**
 * What picking No model prefills: the class from the class filter, else the node's own (edit); the
 * type from the node only when that class is the node's own, since a type belongs to one class.
 * Empty string = nothing picked.
 */
export function noModelDefaults({ classFilter = "", currentClassId = null, currentTypeId = null } = {}) {
  const classId = classFilter !== "" ? classFilter : (currentClassId ?? "");
  return { class_id: classId, type_id: classId === currentClassId ? (currentTypeId ?? "") : "" };
}
