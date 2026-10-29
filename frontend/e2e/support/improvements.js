// Set-up of improvements by API for the improvement specs (S068): a ticket that is back in service,
// and an improvement started from it.
import { expect } from "@playwright/test";
import { apiAs, personId } from "./people.js";
import { istLocal, raiseByApi } from "./tickets.js";

/**
 * A ticket on `machineId` raised by the engineer with *Already fixed* (S018 A1), so it is back in
 * service and can start an improvement. A breakdown stopped 60 min ago and fixed 10 min ago
 * (50 min down), or a defect (no downtime).
 */
export async function raiseFixed(machineId, description, { breakdown = false } = {}) {
  const kannan = await personId("technician");
  return raiseByApi("engineer", {
    equipment_id: machineId,
    intensity: breakdown ? "critical" : "degraded",
    description,
    ...(breakdown ? { occurred_at: istLocal(60) } : {}),
    restore: { person_id: kannan, ...(breakdown ? { occurred_at: istLocal(10) } : {}) },
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
