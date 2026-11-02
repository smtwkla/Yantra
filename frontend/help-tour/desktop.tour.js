import { test } from "@playwright/test";
import { asPerson, closeDialog, DATA, dialogOpen, shot, tryDo } from "./shot.js";

const id = DATA.ids;
const T = DATA.tickets;
const J = DATA.jobs;
const P = DATA.plans;
const sel = async (dialog, label, option) => {
  const s = dialog.getByLabel(label).first();
  const opts = await s.locator("option").allTextContents();
  const pick = opts.find((o) => o.includes(option)) ?? opts[1];
  await s.selectOption({ label: pick.trim() });
};

test("desktop shell and equipment", async ({ page }) => {
  await asPerson(page, "engineer", "/me");
  await shot(page, "03-me-engineer-desktop");
  await page.goto("/equipment");
  await shot(page, "13-equipment-list-desktop");
  await tryDo("search", async () => {
    await page.getByPlaceholder(/Code, name/).first().fill("compressor");
    await page.waitForTimeout(800);
    await shot(page, "14-equipment-search-desktop");
  });
  await page.goto(`/equipment/${id["Main extruder"]}`);
  await shot(page, "15-equipment-detail-desktop", { full: true, maxHeight: 2000 });
  await page.goto(`/equipment/${id["Extruder main gearbox"]}`);
  await shot(page, "16-component-unit-desktop", { full: true, maxHeight: 1600 });
  await page.goto(`/labels?ids=${id["Main extruder"]},${id["Screw compressor 1"]},${id["Screw compressor 2"]}&parts=1`);
  await shot(page, "17-labels-print-desktop");
  await page.goto("/asset-list");
  await shot(page, "18-asset-list-print-desktop");
});

test("desktop tickets", async ({ page }) => {
  await asPerson(page, "engineer", "/tickets");
  await shot(page, "25-tickets-list-desktop");
  await page.goto(`/tickets/${T.bis}`);
  await shot(page, "26-ticket-detail-desktop", { full: true, maxHeight: 1800 });
  await tryDo("close", async () => {
    await page.getByRole("button", { name: /^Close/ }).first().click();
    const d = await dialogOpen(page);
    await tryDo("cause", () => sel(d, /Cause/, "Expected wear"));
    await tryDo("action", () => sel(d, /Action/, "Replace"));
    await shot(page, "27-ticket-close-dialog-desktop");
    await closeDialog(page);
  });
  await page.goto(`/tickets/${T.new}`);
  await tryDo("assign", async () => {
    await page.getByRole("button", { name: "Assign", exact: true }).first().click();
    await dialogOpen(page);
    await shot(page, "28-ticket-assign-dialog-desktop");
    await closeDialog(page);
  });
  await page.goto(`/tickets/${T.sched}`);
  await shot(page, "29-ticket-on-hold-desktop");
});

test("desktop improvements", async ({ page }) => {
  await asPerson(page, "engineer", "/tickets/improvements");
  await shot(page, "30-improvements-list-desktop");
  await page.goto(`/tickets/improvements/${DATA.improvement}`);
  await shot(page, "31-improvement-detail-desktop", { full: true, maxHeight: 2400 });
  await page.goto("/tickets/improvements/register");
  await shot(page, "32-improvement-register-desktop");
  await page.goto(`/tickets/${T.closed}`);
  await tryDo("start improvement", async () => {
    await page.getByRole("button", { name: "Start improvement" }).first().click();
    const d = await dialogOpen(page);
    await d.getByLabel("Title").fill("Cooling fan belts wear out early");
    await d.getByLabel("Problem").fill("Fan belts on both compressors last 3 months instead of 12.");
    await shot(page, "33-start-improvement-dialog-desktop");
    await closeDialog(page);
  });
});

test("desktop lesson and readings", async ({ page }) => {
  await asPerson(page, "engineer", `/equipment/lessons/${DATA.lesson}`);
  await shot(page, "36-lesson-page-desktop");
  await page.goto(`/equipment/${id["Main extruder"]}`);
  await page.getByRole("link", { name: "Open register" }).or(page.getByRole("button", { name: "Open register" })).first().click();
  await shot(page, "42-readings-register-desktop");
});

test("desktop pm", async ({ page }) => {
  await asPerson(page, "engineer", `/equipment/pm/${P.ext}`);
  await shot(page, "60-pm-plan-desktop", { full: true, maxHeight: 1800 });
  await tryDo("add item", async () => {
    await page.getByRole("button", { name: "Add item", exact: true }).click();
    const d = await dialogOpen(page);
    await tryDo("type", () => d.locator("label.btn", { hasText: "Check" }).click());
    await d.getByLabel("What to do or check").fill("Clean the cooler fins with compressed air");
    await shot(page, "61-pm-add-item-dialog-desktop");
    await closeDialog(page);
  });
  await page.goto(`/equipment/${id["Screw compressor 2"]}/pm/new`);
  await shot(page, "62-pm-new-plan-desktop", { full: true, maxHeight: 1600 });

  await page.goto("/pm");
  await shot(page, "63-pm-jobs-due-desktop");
  await page.goto("/pm?tab=upcoming");
  await shot(page, "64-pm-jobs-upcoming-desktop");
  await page.goto("/pm?tab=to_verify");
  await shot(page, "65-pm-jobs-to-verify-desktop");
  await page.goto("/pm?tab=done");
  await shot(page, "66-pm-jobs-done-desktop");

  await page.goto(`/pm/jobs/${J.c2}`);
  await shot(page, "67-pm-job-to-verify-desktop", { full: true, maxHeight: 1800 });
  await tryDo("verify", async () => {
    await page.getByRole("button", { name: "Verify job" }).click();
    await dialogOpen(page);
    await shot(page, "68-pm-verify-dialog-desktop");
    await closeDialog(page);
  });
  await tryDo("send back", async () => {
    await page.getByRole("button", { name: "Send back", exact: true }).click();
    const sb = await dialogOpen(page);
    await tryDo("remark", () => sb.locator("textarea").first().fill("Tighten the hose clamp at the dryer, then check again."));
    await shot(page, "69-pm-send-back-dialog-desktop");
    await closeDialog(page);
  });

  await page.goto(`/pm/jobs/${J.press}`);
  await tryDo("reschedule", async () => {
    await page.getByRole("button", { name: "Reschedule job" }).click();
    const rs = await dialogOpen(page);
    await tryDo("date", async () => {
      const t = new Date(Date.now() + 4 * 86400000 + 5.5 * 3600000).toISOString().slice(0, 10);
      await rs.getByLabel("New due date").fill(t);
    });
    await tryDo("why", () => rs.getByLabel("Why is the job moved?").fill("Press runs a rush order until Friday."));
    await shot(page, "70-pm-reschedule-dialog-desktop");
    await closeDialog(page);
  });
  await tryDo("skip", async () => {
    await page.getByRole("button", { name: "Skip job" }).click();
    const sk = await dialogOpen(page);
    await tryDo("why", () => sk.getByLabel("Why is the job skipped?").fill("Press idle; no orders this month."));
    await shot(page, "71-pm-skip-dialog-desktop");
    await closeDialog(page);
  });
  await page.goto(`/pm/jobs/${J.mill}`);
  await shot(page, "72-pm-job-verified-desktop", { full: true, maxHeight: 1600 });
  await page.goto(`/pm/jobs/${J.skip}`);
  await shot(page, "73-pm-job-skipped-desktop");
});

test("desktop contracts", async ({ page }) => {
  await asPerson(page, "manager", `/contracts/${DATA.contract}`);
  await shot(page, "80-contract-page-desktop", { full: true, maxHeight: 2400 });
  await page.goto(`/equipment/${id["Screw compressor 1"]}`);
  await tryDo("scroll", () => page.getByText("Under contract").first().scrollIntoViewIfNeeded());
  await shot(page, "81-contract-card-on-machine-desktop");
});

test("desktop masters", async ({ page }) => {
  await asPerson(page, "admin", "/masters");
  for (const [label, slug] of [["Sites", "sites"], ["Units", "units"], ["Classes", "classes"], ["Models", "models"],
    ["Meter types", "meter-types"], ["Failure codes", "failure-codes"], ["Trades", "trades"], ["Vendors", "vendors"],
    ["Team", "team"], ["Contracts", "contracts"]]) {
    await tryDo(label, async () => {
      await page.getByRole("button", { name: label, exact: true }).or(page.getByRole("link", { name: label, exact: true }))
        .filter({ visible: true }).first().click();
      await shot(page, `85-masters-${slug}-desktop`);
    });
  }
});

test("desktop settings", async ({ page }) => {
  await asPerson(page, "admin", "/settings");
  await shot(page, "95-settings-admin-desktop", { full: true, maxHeight: 2400 });
  await asPerson(page, "it_admin", "/settings");
  await shot(page, "96-settings-it-admin-desktop");
  await asPerson(page, "manager", "/notifications");
  await shot(page, "91-notifications-desktop");
});
