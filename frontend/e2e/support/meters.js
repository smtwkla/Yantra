// The meters set-up of the browser tests (S038, moved here by S039 BS1-03): a machine of its own
// press model, with the model's meters and its own, made through the API as admin (S024: tests
// set up by API).
import { expect } from "@playwright/test";
import { apiAs } from "./people.js";

// S038: a node's meters are its model's plus its own.  Each test makes its own press model and
// machine through the API (never the seed's SMTW-HYP-01 model, which stays free for other tests;
// S039 BR3-03), named after the project: the three projects share one database.
export async function meterMachine(testInfo, tag, { unit = "SMTW.MCC1", modelMeters = [], ownMeters = [] } = {}) {
  const api = await apiAs("admin");
  try {
    const items = async (url) => (await (await api.get(url)).json()).items;
    const created = async (url, data) => {
      const res = await api.post(url, { data });
      expect(res.status(), await res.text()).toBe(201);
      return await res.json();
    };
    const [units, makers, classes, meterTypes] = await Promise.all([
      items("/api/masters/units"), items("/api/masters/manufacturers"), items("/api/masters/equipment-classes"),
      items("/api/masters/meter-types"),
    ]);
    const typeId = (name) => meterTypes.find((t) => t.name === name).id;
    const name = `S038 press ${tag} ${testInfo.project.name}`;
    const model = await created("/api/masters/equipment-models", {
      manufacturer_id: makers.find((m) => m.name === "Generic").id,
      designation: `${name} ${Date.now().toString(36)}`, class_id: classes.find((c) => c.code === "HP").id, type_id: null,
    });
    for (const [meter, limits] of modelMeters) {
      await created(`/api/masters/equipment-models/${model.id}/meters`, { meter_type_id: typeId(meter), ...limits });
    }
    const machine = await created("/api/equipment", {
      level: "equipment", unit_id: units.find((u) => u.full_code === unit).id, model_id: model.id, name,
    });
    for (const [meter, limits] of ownMeters) {
      await created(`/api/equipment/${machine.id}/meters`, { meter_type_id: typeId(meter), ...limits });
    }
    return machine;
  } finally {
    await api.dispose();
  }
}

/**
 * A reading of the machine's meter `name`, logged through the API as the operator (a test's own
 * set-up; S039 CR1-02).  `takenAt` is the time string the test computed once (`istLocal(...)`), so
 * the test expects exactly what was sent, whatever the clock does meanwhile (CR1-01).
 */
export async function logByApi(machine, name, value, takenAt, extra = {}) {
  const api = await apiAs("operator");
  try {
    const types = await (await api.get("/api/masters/meter-types")).json();
    const meterType = types.items.find((t) => t.name === name);
    const res = await api.post(`/api/equipment/${machine.id}/readings`, {
      data: { meter_type_id: meterType.id, value, taken_at: takenAt, ...extra },
    });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}
