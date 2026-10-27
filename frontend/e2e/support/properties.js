// Equipment properties (S043): a class of its own with a model and one machine of it, and the
// properties a test needs, made through the API as admin (S024: tests set up by API).  A class of
// its own per test, because the three projects share one database and a class's properties show
// on every machine of it.
import { expect } from "@playwright/test";
import { apiAs } from "./people.js";

// 2–4 capital letters (the class-code rule); random, so a re-run on the same database never clashes
function classCode() {
  return Array.from({ length: 4 }, () => String.fromCharCode(65 + Math.floor(Math.random() * 26))).join("");
}

async function ok(res) {
  expect(res.ok(), `${res.url()}: ${res.status()} ${await res.text()}`).toBe(true);
  return res.json();
}

/**
 * propertySetup(tag, {properties, link, values}) -> {cls, model, node, properties}.
 * `properties`: request bodies of the properties to make; `link`: add them to the class (default
 * true); `values`: {<index in properties>: value} set on the model.  `tag` makes the names unique
 * (the project's name and a random part).
 */
export async function propertySetup(tag, { properties = [], link = true, values = {} } = {}) {
  const api = await apiAs("admin");
  try {
    const cls = await ok(await api.post("/api/masters/equipment-classes", { data: { code: classCode(), name: `E2E props ${tag}` } }));
    const maker = await ok(await api.post("/api/masters/manufacturers", { data: { name: `E2E maker ${tag}` } }));
    const model = await ok(await api.post("/api/masters/equipment-models", {
      data: { manufacturer_id: maker.id, designation: "P-1", class_id: cls.id },
    }));
    const units = await ok(await api.get("/api/masters/units"));
    const unit = units.items.find((u) => u.full_code === "SMTW.MCC1");
    const node = await ok(await api.post("/api/equipment", {
      data: { level: "equipment", unit_id: unit.id, model_id: model.id, name: `E2E props machine ${tag}` },
    }));
    const made = [];
    for (const body of properties) made.push(await ok(await api.post("/api/masters/properties", { data: body })));
    if (link && made.length) {
      await ok(await api.post(`/api/masters/equipment-classes/${cls.id}/properties`, { data: { property_ids: made.map((p) => p.id) } }));
    }
    const entries = Object.entries(values).map(([index, value]) => [String(made[index].id), value]);
    if (entries.length) {
      await ok(await api.put(`/api/masters/equipment-models/${model.id}/properties`, { data: { values: Object.fromEntries(entries) } }));
    }
    return { cls, model, node, properties: made };
  } finally {
    await api.dispose();
  }
}

/**
 * An equipment category of its own (S063), named `E2E category <tag>`, with the classes `classes`
 * put in it, made as admin.  The e2e database has no categories (nothing is seeded, S063 Q1).
 */
export async function categorySetup(tag, classes = []) {
  const api = await apiAs("admin");
  try {
    const category = await ok(await api.post("/api/masters/equipment-categories", { data: { name: `E2E category ${tag}` } }));
    for (const cls of classes) {
      await ok(await api.put(`/api/masters/equipment-classes/${cls.id}`, { data: { category_id: category.id } }));
    }
    return category;
  } finally {
    await api.dispose();
  }
}

/** A component-unit with no model (S033) of class `cls` under `parent`, made as admin (BS1-01). */
export async function noModelPart(parent, cls, name) {
  const api = await apiAs("admin");
  try {
    return await ok(await api.post("/api/equipment", {
      data: { level: "component_unit", parent_id: parent.id, model_id: null, class_id: cls.id, name },
    }));
  } finally {
    await api.dispose();
  }
}

/** A tag for names: the project's name and a random part. */
export function propertyTag(testInfo) {
  return `${testInfo.project.name} ${Math.random().toString(36).slice(2, 7)}`;
}
