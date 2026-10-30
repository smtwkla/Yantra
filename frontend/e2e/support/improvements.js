// Set-up of improvements by API for the improvement specs (S068): a ticket that is back in service,
// and an improvement started from it.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect } from "@playwright/test";
import { apiAs, personId } from "./people.js";
import { istDay, istLocal, raiseByApi } from "./tickets.js";

/** The test photo, a small JPEG. */
export const TEST_PHOTO = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "fixtures", "test-photo.jpg");

/**
 * A ticket on `machineId` raised by the engineer with *Already fixed* (S018 A1), so it is back in
 * service and can start an improvement. A breakdown stopped `minutesAgo` minutes ago (default 60) and
 * fixed 50 minutes later (50 min down), or a defect (no downtime). `minutesAgo` goes back up to the
 * 7-day back-dating of a ticket (S076: a register test wants a ticket 3 days old).
 */
export async function raiseFixed(machineId, description, { breakdown = false, minutesAgo = 60 } = {}) {
  const kannan = await personId("technician");
  return raiseByApi("engineer", {
    equipment_id: machineId,
    intensity: breakdown ? "critical" : "degraded",
    description,
    ...(breakdown ? { occurred_at: istLocal(minutesAgo) } : {}),
    restore: { person_id: kannan, ...(breakdown ? { occurred_at: istLocal(minutesAgo - 50) } : {}) },
  });
}

/** Start an improvement from `ticket` through the API as the engineer, who leads it -> the detail. */
export async function startImprovementByApi(ticket, { title = `Set-up: ${ticket.serial}`, problem = "Set-up problem text" } = {}) {
  const lead = await personId("engineer");
  const api = await apiAs("engineer");
  try {
    const res = await api.post("/api/improvements", { data: { ticket_id: ticket.id, title, problem, lead_id: lead } });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/** Drop `improvement` with `reason` through the API as the engineer, who leads it -> the detail (S076). */
export async function dropByApi(improvement, reason) {
  const api = await apiAs("engineer");
  try {
    const res = await api.post(`/api/improvements/${improvement.id}/drop`, { data: { reason } });
    expect(res.status(), await res.text()).toBe(200);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/** Add `ticket` to `improvement` through the API as the engineer -> the detail. */
export async function addTicketByApi(improvement, ticket) {
  const api = await apiAs("engineer");
  try {
    const res = await api.post(`/api/improvements/${improvement.id}/tickets`, { data: { ticket_id: ticket.id } });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/** The owner choices of `improvement` as the engineer sees them: [{id, name}] (S071; people with no login too). */
export async function ownerChoices(improvement) {
  const api = await apiAs("engineer");
  try {
    const res = await api.get(`/api/improvements/owners?improvement_id=${improvement.id}`);
    expect(res.status(), await res.text()).toBe(200);
    return (await res.json()).items;
  } finally {
    await api.dispose();
  }
}

/**
 * Add a countermeasure to `improvement` through the API as the engineer -> {detail, action}, the
 * action being the one just added.  `owner` is the person's name as the Team shows it.
 */
export async function addActionByApi(improvement, {
  owner = "Kannan (technician)", kind = "corrective", text = "S071 set-up: fit the new gasket", due = istDay(14),
} = {}) {
  const person = (await ownerChoices(improvement)).find((p) => p.name === owner);
  expect(person, `${owner} is not an owner choice`).toBeTruthy();
  const api = await apiAs("engineer");
  try {
    const res = await api.post(`/api/improvements/${improvement.id}/actions`, {
      data: { kind, text, owner_id: person.id, due_date: due },
    });
    expect(res.status(), await res.text()).toBe(201);
    const detail = await res.json();
    return { detail, action: detail.actions.at(-1) };
  } finally {
    await api.dispose();
  }
}

/** Mark `action` done through the API as the seed person `key` (the owner or the engineer) -> the detail. */
export async function markDoneByApi(improvement, action, key = "engineer", doneText = "S071 set-up: done") {
  const api = await apiAs(key);
  try {
    const res = await api.post(`/api/improvements/${improvement.id}/actions/${action.id}/done`, { data: { done_text: doneText } });
    expect(res.status(), await res.text()).toBe(200);
    return await res.json();
  } finally {
    await api.dispose();
  }
}

/** Upload the test photo to `action` through the API as the seed person `key`, titled `title` -> the document. */
export async function uploadActionPhotoByApi(action, title, key = "engineer") {
  const api = await apiAs(key);
  try {
    const res = await api.post(`/api/improvements/actions/${action.id}/documents`, {
      multipart: { kind: "photo", title, file: { name: "test-photo.jpg", mimeType: "image/jpeg", buffer: fs.readFileSync(TEST_PHOTO) } },
    });
    expect(res.status(), await res.text()).toBe(201);
    return await res.json();
  } finally {
    await api.dispose();
  }
}
