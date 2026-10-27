/**
 * The equipment list's property filter (docs/steps/S062-property-filter/1-brief.md) — pure helpers:
 * the operators by data type, the `props` value in the URL and the API (§ 5.1), a line's
 * completeness, the words of the filter line, and the level rule on the first filter (§ 1 item 4a).
 * The checks of the values are the backend's (property_filter_core).
 */

export const MAX_RULES = 10;
const MAX_PROPS_LENGTH = 4000; // as the backend: a longer value cannot be read

export const MATCH_ALL = "all";
export const MATCH_ANY = "any";

// The operators each data type takes, in the dialog's order (the backend's OPERATORS)
const COMPARE = ["eq", "ne", "lt", "le", "gt", "ge"];
export const OPERATORS = {
  number: [...COMPARE, "between", "has", "none"],
  choice: ["in", "not_in", "has", "none"],
  text: ["contains", "eq", "has", "none"],
  yes_no: ["eq", "has", "none"],
  geo: ["has", "none"],
};

// Words, not symbols (A3): "more than", not ">"
const WORDS = {
  eq: "equals", ne: "not equal to", lt: "less than", le: "at most", gt: "more than", ge: "at least",
  between: "between", in: "is", not_in: "is not", contains: "contains", has: "has a value", none: "has no value",
};
// "is" reads better than "equals" for text and yes / no
const WORDS_BY_TYPE = { text: { eq: "is" }, yes_no: { eq: "is" } };

/** The operator's words, e.g. "more than"; an unknown operator shows as sent. */
export function operatorLabel(dataType, op) {
  return WORDS_BY_TYPE[dataType]?.[op] ?? WORDS[op] ?? op;
}

/** The operators of a data type; none for an unknown type. */
export function operatorsOf(dataType) {
  return OPERATORS[dataType] ?? [];
}

/** has / none take no value. */
export function takesValue(op) {
  return op !== "has" && op !== "none";
}

/** "not equal to" and "is not" leave out the machines with no value (D4): the dialog says so. */
export function excludesNoValue(op) {
  return op === "ne" || op === "not_in";
}

/**
 * The filter → the `props` text: {"match", "rules": [{property_id, op, value}]}, the keys in this
 * order and no others; has / none carry no value. Null for no rule (no property filter).
 */
export function encodeFilter(filter) {
  if (!filter || !filter.rules?.length) return null;
  const rules = filter.rules.map((rule) => {
    const out = { property_id: rule.property_id, op: rule.op };
    if (takesValue(rule.op)) out.value = rule.value;
    return out;
  });
  return JSON.stringify({ match: filter.match === MATCH_ANY ? MATCH_ANY : MATCH_ALL, rules });
}

const isPlainObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const isWholeNumber = (value) => Number.isInteger(value) && value >= 1;

/**
 * The `props` text → `{ match, rules }`, or null when it cannot be read (a hand-edited or cut
 * bookmark): not JSON, not the shape of § 5.1, more than MAX_RULES lines, or too long.
 */
export function decodeFilter(raw) {
  if (typeof raw !== "string" || raw === "" || raw.length > MAX_PROPS_LENGTH) return null;
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isPlainObject(data) || !Array.isArray(data.rules) || data.rules.length > MAX_RULES) return null;
  const match = data.match ?? MATCH_ALL;
  if (match !== MATCH_ALL && match !== MATCH_ANY) return null;
  if (!data.rules.every((rule) => isPlainObject(rule) && isWholeNumber(rule.property_id))) return null;
  return {
    match,
    rules: data.rules.map((rule) => ({ property_id: rule.property_id, op: rule.op, value: rule.value })),
  };
}

const filled = (text) => typeof text === "string" && text.trim() !== "";

/**
 * A rule is complete when it has a property and the value its operator needs (presentational: the
 * backend judges the value itself). `dataType` is the property's.
 */
export function ruleComplete(rule, dataType) {
  if (!rule.property_id || !rule.op) return false;
  if (!takesValue(rule.op)) return true;
  if (rule.op === "between") return Array.isArray(rule.value) && rule.value.length === 2 && rule.value.every(filled);
  if (dataType === "choice") return Array.isArray(rule.value) && rule.value.length > 0;
  if (dataType === "yes_no") return typeof rule.value === "boolean";
  return filled(rule.value);
}

/** A dialog line → a filter rule ({property_id, op, value}); `dataType` is the line's property's. */
export function ruleOfLine(line, dataType) {
  const rule = { property_id: line.property_id, op: line.op };
  if (!takesValue(line.op)) return rule;
  if (line.op === "between") rule.value = [line.low, line.high];
  else if (dataType === "choice") rule.value = [...line.optionIds];
  else if (dataType === "yes_no") rule.value = line.value === "" ? "" : line.value === "true";
  else rule.value = line.value;
  return rule;
}

/**
 * The dialog's state as text, to compare two states. Both sides must be built with the same
 * `dataTypeOf(line)` (the property list may load between them), or equal lines would differ.
 */
export function filterSnapshot(match, lines, dataTypeOf) {
  return JSON.stringify({ match, rules: lines.map((line) => ruleOfLine(line, dataTypeOf(line))) });
}

function valueWords(property, rule) {
  if (!takesValue(rule.op)) return "";
  const unit = property?.unit ? ` ${property.unit}` : "";
  if (rule.op === "between") {
    const [low, high] = Array.isArray(rule.value) ? rule.value : [];
    return ` ${low} and ${high}${unit}`;
  }
  if (property?.data_type === "choice") {
    const ids = Array.isArray(rule.value) ? rule.value : [];
    const labels = ids.map((id) => property.options?.find((o) => o.id === id)?.label ?? `#${id}`);
    return ` ${labels.join(" or ")}`;
  }
  if (property?.data_type === "yes_no") return rule.value === true ? " Yes" : rule.value === false ? " No" : "";
  if (property?.data_type === "text") return ` "${rule.value}"`;
  return ` ${rule.value}${unit}`;
}

/** One condition in words: "Rated power more than 7.5 kW", "Mobility is Portable or Mobile". */
export function describeRule(rule, properties) {
  const property = (properties ?? []).find((p) => p.id === rule.property_id);
  const name = property ? property.name : `#${rule.property_id}`;
  return `${name} ${operatorLabel(property?.data_type, rule.op)}${valueWords(property, rule)}`;
}

/**
 * The filter line (§ 1 item 3) and the print header's part: "Properties: <condition>" for one,
 * "Properties (all of): … · …" or "Properties (any of): … · …" for more, the asset list's " · "
 * between them; "Properties: cannot be read" for a null (unreadable) filter. `properties`: the
 * masters list (with options), or null while loading (names then read "#12").
 */
export function describeFilter(filter, properties) {
  if (!filter) return "Properties: cannot be read";
  const conditions = filter.rules.map((rule) => describeRule(rule, properties)).join(" · ");
  if (filter.rules.length < 2) return `Properties: ${conditions}`;
  return `Properties (${filter.match === MATCH_ANY ? "any" : "all"} of): ${conditions}`;
}

/**
 * The query changes for a new `props` (null clears it). The first property filter at the default
 * level (no `level` in the URL) also sets level=all, so the motors and gearboxes show (D11; the
 * search's rule). A change to an existing filter, or any level in the URL, keeps the level.
 */
export function propsChanges(query, encoded) {
  const changes = { props: encoded };
  if (encoded && !query?.props && !query?.level) changes.level = "all";
  return changes;
}
