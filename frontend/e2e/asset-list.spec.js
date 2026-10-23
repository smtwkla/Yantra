// The printable asset list (S015) — what a browser can show of its manual checks: one section
// per unit, the header, the two switches (parts indented with the count line, checklist with
// the signature footer), the switches kept on reload and left off paper, a user's own units
// only, and the empty case.  Paper (100 %, page 2's header) stays a device check.
import { test, expect } from "./support/test.js";
import { asPerson, seedIds } from "./support/people.js";

let seed;

test.beforeAll(async () => {
  seed = await seedIds();
});

const section = (page, unit) => page.locator("section.unit-section", { has: page.getByRole("heading", { name: new RegExp(`^${unit} `) }) });

test("manager: a section per unit with its header; parts indented with the count line; checklist with signatures", async ({ page }) => {
  await asPerson(page, "manager", "/asset-list");
  for (const unit of ["SMTW.MCC1", "SMTW.MCC2", "BRICKS.FILTER"]) {
    await expect(section(page, unit)).toBeVisible();
  }
  const mcc2 = section(page, "SMTW.MCC2");
  await expect(mcc2.getByRole("heading", { level: 1 })).toHaveText("SMTW Main factory, Pavoorchatram");
  await expect(mcc2.locator(".header-line").last()).toContainText(/Printed on \d{2}-\d{2}-\d{4} \d{2}:\d{2} by Arun \(manager\)/);
  await expect(mcc2.locator(".count-line")).toHaveText(/^\d+ equipment$/);
  await expect(mcc2.getByText(seed.gearbox.code)).toHaveCount(0);

  await page.getByLabel("Include parts").check();
  await expect(page).toHaveURL(/parts=1/);
  const machineRow = mcc2.locator("tbody tr", { hasText: seed.extruder.code });
  const partRow = machineRow.locator("xpath=following-sibling::tr[1]");
  await expect(partRow).toContainText(seed.gearbox.code);
  await expect(partRow.locator("td").nth(2)).toHaveCSS("padding-left", /^1[45]\.\d+px$/); // 4 mm
  await expect(machineRow.locator("td").nth(2)).toHaveCSS("padding-left", "0px");
  // The count line agrees with the rows: machines at depth 0, parts below them
  const parts = await mcc2.locator("tbody tr.part").count();
  const machines = (await mcc2.locator("tbody tr").count()) - parts;
  expect(parts).toBeGreaterThan(0);
  await expect(mcc2.locator(".count-line")).toHaveText(`${machines} equipment, ${parts} parts`);

  await page.getByLabel("Checklist columns").check();
  await expect(mcc2.getByRole("columnheader", { name: "Remarks" })).toBeVisible();
  await expect(mcc2.locator(".signatures")).toContainText("Checked by");
  await expect(mcc2.locator(".signatures")).toContainText("Verified by (accounts)");

  // A reload keeps the switches (they live in the link); on paper they are left out
  await page.reload();
  await expect(page.getByLabel("Include parts")).toBeChecked();
  await expect(page.getByLabel("Checklist columns")).toBeChecked();
  await page.emulateMedia({ media: "print" });
  await expect(page.getByLabel("Include parts")).toBeHidden();
  await expect(page.getByRole("button", { name: "Print" })).toBeHidden();
  await page.emulateMedia({ media: "screen" });

  // Leaving the page takes its A4 @page rule away, so other screens print as they like
  await page.goto("/equipment");
  await expect(page.getByRole("button", { name: /Print asset list/ })).toBeVisible();
  const pageRules = await page.evaluate(() => [...document.head.querySelectorAll("style")].filter((s) => s.textContent.includes("@page")).length);
  expect(pageRules).toBe(0);
});

test("operator of one unit: only that unit's section", async ({ page }) => {
  await asPerson(page, "operator", "/asset-list");
  await expect(section(page, "SMTW.MCC2")).toBeVisible();
  await expect(page.locator("section.unit-section")).toHaveCount(1);
});

test("filters that match nothing say so", async ({ page }) => {
  await asPerson(page, "manager", "/asset-list?lifecycle=out_of_use");
  await expect(page.getByText("Nothing to list for these filters")).toBeVisible();
});
