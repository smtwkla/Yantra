// PM set-up by API for the PM specs (S104 § 8.4): since S104 a machine gets a plan only through a PM template linked
// to it. `pmPlanByApi` takes the plan body the S096–S102 specs were written with (a title, the trigger, a meter named
// by node and type, the items, the assignee and Last done in one object) and makes it the S104 way: a template of the
// work (POST /api/pm/templates), attached to the machine (POST /api/pm/plans), then the machine's own settings
// (PUT /api/pm/plans/<id>), all as the engineer (S024: set-up by API). A template name is unique in the lane's
// database, so the machine's code follows the title ("S098 flow plan · S098-…"); the specs find rows by the title,
// which the name still holds. S104 A1: a meter named on another node than the plan's (S096's parent meter) becomes a
// meter link on the node (*Use a meter from above*), set before the template is attached.
import { expect } from "@playwright/test";
import { linkMeterByApi } from "./meters.js";
import { apiAs } from "./people.js";

// The plan row's own fields (pm_plans_core.PLAN_FIELDS); every other field of the old body is the template's
const PLAN_FIELDS = ["assignee_id", "last_done_on", "last_done_meter"];

/** An S096-shaped item → the template's (S104 § 5.2): a reading with a meter is a Meter reading (its limits are the
 * machine's meter's, D6), one without a Measurement. A meter of another node than `nodeId` goes into `links`
 * ({meter_type_id: node id}), for a meter link on the node (A1). */
export function templateItem(item, nodeId, links = {}) {
  const { meter_equipment_id: meterNode, ...rest } = item;
  if (item.item_type !== "reading" || "reading_kind" in item) return rest;
  if (!item.meter_type_id) return { ...rest, reading_kind: "measurement" };
  if (meterNode && meterNode !== nodeId) links[item.meter_type_id] = meterNode;
  return { ...rest, reading_kind: "meter", unit: null, min_value: null, max_value: null };
}

/** An old plan body → {template, settings, links}: `links` maps a meter type id to the node whose meter it is. */
export function splitPlanBody(node, body) {
  const template = {};
  const settings = {};
  const links = {};
  for (const [key, value] of Object.entries(body)) {
    if (PLAN_FIELDS.includes(key)) settings[key] = value;
    else if (key === "title") template.name = `${value} · ${node.code}`;
    else if (key === "meter_equipment_id") {
      if (value && value !== node.id) links[body.meter_type_id] = value;
    } else if (key === "items") template.items = value.map((item) => templateItem(item, node.id, links));
    else if (key !== "equipment_id") template[key] = value;
  }
  return { template, settings, links };
}

/** A template made of `body`'s work, attached to `node` (its meter links set first), then `body`'s plan settings
 * -> the plan's detail. */
export async function pmPlanByApi(node, body, { as = "engineer" } = {}) {
  const { template, settings, links } = splitPlanBody(node, body);
  for (const [meterTypeId, sourceId] of Object.entries(links)) {
    await linkMeterByApi(node, { id: sourceId }, Number(meterTypeId));
  }
  const api = await apiAs(as);
  try {
    let res = await api.post("/api/pm/templates", { data: template });
    expect(res.status(), await res.text()).toBe(201);
    const made = await res.json();
    res = await api.post("/api/pm/plans", { data: { equipment_id: node.id, template_id: made.id } });
    expect(res.status(), await res.text()).toBe(201);
    let plan = await res.json();
    if (Object.keys(settings).length) {
      res = await api.put(`/api/pm/plans/${plan.id}`, { data: settings });
      expect(res.status(), await res.text()).toBe(200);
      plan = await res.json();
    }
    return { ...plan, items: plan.template.items };
  } finally {
    await api.dispose();
  }
}

/** A change of a plan's template (its work, its trigger, {active}) as the engineer -> the template's answer. */
export async function changeTemplateByApi(plan, fields, { as = "engineer" } = {}) {
  const api = await apiAs(as);
  try {
    const res = await api.put(`/api/pm/templates/${plan.template.id}`, { data: fields });
    expect(res.status(), await res.text()).toBe(200);
    return await res.json();
  } finally {
    await api.dispose();
  }
}
