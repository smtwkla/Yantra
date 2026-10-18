/**
 * The equipment form's Model picker (docs/steps/S012-equipment-models/1-brief.md § 1.4):
 * the list it offers and how each model reads. Pure: no imports.
 *
 * A model item is the masters API's: {id, label, class_id, class_code, type_name, active, …}.
 */

/** "Atlas Copco GA37 — CMP / Screw compressor"; "… — HP" for a model without a type. */
export function pickerLabel(model) {
  const kind = model.type_name ? `${model.class_code} / ${model.type_name}` : model.class_code;
  return `${model.label} — ${kind}`;
}

/**
 * The models to offer, in the API's order (manufacturer, then designation):
 * - only active ones, except the node's current model (`currentId`, on edit), kept and marked
 *   "(inactive)" as classes and types are;
 * - of the class filter's class when one is chosen (`classId`, "" for all); the model now
 *   picked in the form (`selectedId`) stays listed, so the select never shows a blank.
 * Returns [{id, text}].
 */
export function modelChoices(models, { classId = "", currentId = null, selectedId = null } = {}) {
  return (models ?? [])
    .filter((m) => m.active || m.id === currentId)
    .filter((m) => classId === "" || m.class_id === classId || m.id === selectedId)
    .map((m) => ({ id: m.id, text: `${pickerLabel(m)}${m.active ? "" : " (inactive)"}` }));
}

/** True when a class is chosen in the filter and it has no active model yet (the form's hint). */
export function classHasNoModel(models, classId) {
  return classId !== "" && !(models ?? []).some((m) => m.active && m.class_id === classId);
}
