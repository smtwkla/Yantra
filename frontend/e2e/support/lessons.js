// Set-up of one-point lessons by API for the lesson specs (S077): two machines of class HP in the
// operator's unit, a lesson written as the engineer, a photo added to it.  Each test makes its own
// machines, so no seed machine gains a lesson and no other spec's page changes (BR1-10).
import fs from "node:fs";
import { expect } from "@playwright/test";
import { TEST_PHOTO } from "./improvements.js";
import { meterMachine } from "./meters.js";
import { apiAs } from "./people.js";

/**
 * Two machines of class `HP` in SMTW.MCC2, the unit of the seed operator (`meterMachine` makes each with
 * its own press model, named after `tag` and the project) -> {a, b, className}.
 */
export async function lessonMachines(testInfo, tag) {
  const a = await meterMachine(testInfo, `${tag} A`, { unit: "SMTW.MCC2" });
  const b = await meterMachine(testInfo, `${tag} B`, { unit: "SMTW.MCC2" });
  const api = await apiAs("admin");
  try {
    const classes = (await (await api.get("/api/masters/equipment-classes")).json()).items;
    return { a, b, className: classes.find((c) => c.code === "HP").name };
  } finally {
    await api.dispose();
  }
}

/**
 * Write a lesson on `machine` as the engineer -> the detail.  `forClass` ticks the class; `actionId` links a
 * *Lesson* countermeasure (the machine must be the improvement's).
 */
export async function writeLessonByApi(machine, {
  title = "S077 set-up: keep the panel door shut", body = "S077 set-up: dust stops the press.", forClass = false, actionId = null,
} = {}) {
  const api = await apiAs("engineer");
  try {
    const res = await api.post("/api/procedures", {
      data: { equipment_id: machine.id, title, body, for_class: forClass, ...(actionId ? { action_id: actionId } : {}) },
    });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/**
 * Retire `lesson` as the engineer.  A test that writes a class lesson ends with this: a class lesson
 * shows on every machine of its class, and a retired one shows on no card for a reader.
 */
export async function retireLessonByApi(lesson) {
  const api = await apiAs("engineer");
  try {
    const res = await api.put(`/api/procedures/${lesson.id}`, { data: { active: false } });
    expect(res.status(), await res.text()).toBe(200);
  } finally {
    await api.dispose();
  }
}

/** Upload the test photo to `lesson` as the engineer, titled `title` -> the document. */
export async function addLessonPhotoByApi(lesson, title) {
  const api = await apiAs("engineer");
  try {
    const res = await api.post(`/api/procedures/${lesson.id}/documents`, {
      multipart: { kind: "photo", title, file: { name: "test-photo.jpg", mimeType: "image/jpeg", buffer: fs.readFileSync(TEST_PHOTO) } },
    });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}
