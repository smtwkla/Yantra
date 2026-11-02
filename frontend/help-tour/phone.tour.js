import { test } from "@playwright/test";
import { asPerson, closeDialog, DATA, dialogOpen, shot, tryDo } from "./shot.js";

const id = DATA.ids;
const T = DATA.tickets;
const J = DATA.jobs;

test("phone floor", async ({ page }) => {
  // Me
  await asPerson(page, "technician", "/me");
  await shot(page, "01-me-open-work-phone");
  await asPerson(page, "operator", "/me");
  await shot(page, "02-me-operator-phone");

});

test("phone equipment", async ({ page }) => {
  await asPerson(page, "operator", "/equipment");
  await shot(page, "10-equipment-list-phone");
  await page.goto(`/e/${DATA.codes["Main extruder"]}`);
  await shot(page, "11-qr-landing-phone");
  await page.goto(`/equipment/${id["Main extruder"]}`);
  await shot(page, "12-equipment-detail-phone", { full: true, maxHeight: 1200 });

});

test("phone raise", async ({ page }) => {
  await asPerson(page, "operator", `/tickets/new?equipment_id=${id["Screw compressor 2"]}`);
  await tryDo("search", async () => {
    await page.getByPlaceholder(/Code, name/).first().fill("compressor");
    await page.waitForTimeout(800);
  });
  await shot(page, "20-raise-ticket-pick-machine-phone");
  await page.goto(`/equipment/${id["Screw compressor 2"]}`);
  await page.getByRole("link", { name: "Raise ticket" }).or(page.getByRole("button", { name: "Raise ticket" })).first().click();
  await tryDo("intensity", () => page.getByText("Running, reduced").first().click({ timeout: 3000 }));
  await tryDo("symptom", async () => {
    const s = page.locator("select").first();
    const o = (await s.locator("option").allTextContents()).find((t) => t.includes("Low output"));
    await s.selectOption({ label: o.trim() });
  });
  await tryDo("desc", () => page.getByLabel(/Description|What is wrong/).first().fill("Air pressure drops to 5 bar when both lines run. Normal is 7 bar.", { timeout: 3000 }));
  await shot(page, "21-raise-ticket-filled-phone", { full: true, maxHeight: 1200 });

});

test("phone tickets", async ({ page }) => {
  await asPerson(page, "technician", "/tickets");
  await shot(page, "22-tickets-list-phone");
  await page.goto(`/tickets/${T.prog}`);
  await shot(page, "23-ticket-detail-phone", { full: true, maxHeight: 1200 });
  await tryDo("back in service", async () => {
    await page.getByRole("button", { name: /Back in service|Fixed/ }).first().click({ timeout: 3000 });
    await dialogOpen(page);
    await shot(page, "24-ticket-back-in-service-dialog-phone");
    await closeDialog(page);
  });

});

test("phone readings", async ({ page }) => {
  await asPerson(page, "operator", "/readings");
  await tryDo("sheet value", () => page.locator("main input[inputmode=decimal], main input[type=text]").filter({ visible: true }).first().fill("6262"));
  await shot(page, "40-readings-sheet-phone", { full: true, maxHeight: 1200 });
  await page.goto(`/equipment/${id["Screw compressor 1"]}`);
  await tryDo("log reading", async () => {
    await page.getByRole("button", { name: "Log reading" }).first().click({ timeout: 5000 });
    await dialogOpen(page);
    await page.locator(".modal.show input[inputmode=decimal], .modal.show input[type=number], .modal.show input[type=text]").first().fill("6252.5");
    await shot(page, "41-log-reading-dialog-phone");
    await closeDialog(page);
  });

});

test("phone lesson", async ({ page }) => {
  await asPerson(page, "operator", `/equipment/lessons/${DATA.lesson}`);
  await shot(page, "35-lesson-page-phone", { full: true, maxHeight: 1200 });

});

test("phone pm", async ({ page }) => {
  await asPerson(page, "technician", "/pm");
  await shot(page, "50-pm-list-due-phone");
  await page.goto(`/pm/jobs/${J.ext}`);
  await shot(page, "51-pm-job-before-start-phone", { full: true, maxHeight: 1200 });
  await page.getByRole("button", { name: "Start job" }).click();
  const row = (text) => page.locator(`.pm-item[data-item="${text}"]`);
  await row("No oil leaks at the gearbox").getByRole("button", { name: "OK", exact: true }).click();
  await row("Vacuum gauge reads -0.9 bar or better").getByRole("button", { name: "Not OK", exact: true }).click();
  await tryDo("remark", () => row("Vacuum gauge reads -0.9 bar or better").getByRole("textbox").first().fill("Gauge shows -0.8 bar only.", { timeout: 3000 }));
  await shot(page, "52-pm-job-filling-phone", { full: true, maxHeight: 1400 });
  await tryDo("remark save", () => row("Vacuum gauge reads -0.9 bar or better").getByRole("button", { name: "Save", exact: true }).click({ timeout: 3000 }));
  await row("Grease the auger shaft bearings").getByRole("button", { name: "Done", exact: true }).click();
  const r = row("Gearbox oil temperature");
  await r.getByRole("textbox").first().fill("63");
  await r.getByRole("button", { name: "Save", exact: true }).click();
  await page.waitForTimeout(800);
  await shot(page, "53-pm-job-filled-phone", { full: true, maxHeight: 1600 });
  await page.getByRole("button", { name: "Mark job done" }).click();
  await dialogOpen(page);
  await shot(page, "54-pm-mark-done-dialog-phone");
  await closeDialog(page);

  await page.goto(`/pm/jobs/${J.back}`);
  await shot(page, "55-pm-job-sent-back-phone", { full: true, maxHeight: 1400 });

});

test("phone notifications", async ({ page }) => {
  await asPerson(page, "technician", "/notifications");
  await shot(page, "90-notifications-phone");
});
