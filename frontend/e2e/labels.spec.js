// QR labels (S014) — what a browser can show: 15 labels on a sheet element, 16 labels make two,
// labels printed from the equipment list's ticks, and the label's link /e/<code> opening the
// equipment page.  The sheets are checked in the page (print emulation does not paginate);
// 52 mm on paper, and scanning, stay device checks.
import { test, expect } from "./support/test.js";
import { apiAs, asPerson, seedIds } from "./support/people.js";

const PER_SHEET = 15;
const SPARE_UNIT = "SMTW.KILN"; // no seed equipment: the labels' own machines go here

let seed;
let ids; // 16 machine ids for the sheets

/** At least `count` machines at the spare unit, made through the API as admin when missing -> their ids. */
async function machinesAtSpareUnit(count) {
  const api = await apiAs("admin");
  try {
    const unit = (await (await api.get("/api/masters/units")).json()).items.find((u) => u.full_code === SPARE_UNIT);
    const model = (await (await api.get("/api/masters/equipment-models")).json()).items.find((m) => m.designation === "Generic bore pump");
    const listed = await (await api.get(`/api/equipment?unit_id=${unit.id}&per_page=100`)).json();
    const found = listed.items.map((e) => e.id);
    for (let n = found.length; n < count; n += 1) {
      const res = await api.post("/api/equipment", {
        data: { level: "equipment", unit_id: unit.id, model_id: model.id, name: `E2E label pump ${n + 1}` },
      });
      expect(res.status(), await res.text()).toBe(201);
      found.push((await res.json()).id);
    }
    return found.slice(0, count);
  } finally {
    await api.dispose();
  }
}

test.beforeAll(async () => {
  seed = await seedIds();
  ids = await machinesAtSpareUnit(PER_SHEET + 1);
});

test("15 labels fill one sheet; 16 make two sheets", async ({ page }) => {
  await asPerson(page, "engineer", `/labels?ids=${ids.slice(0, PER_SHEET).join(",")}&parts=0`);
  await expect(page.getByText("15 labels on 1 sheet")).toBeVisible();
  await expect(page.locator(".sheet")).toHaveCount(1);
  await expect(page.locator(".sheet .label")).toHaveCount(PER_SHEET);

  await page.goto(`/labels?ids=${ids.join(",")}&parts=0`);
  await expect(page.getByText("16 labels on 2 sheets")).toBeVisible();
  await expect(page.locator(".sheet")).toHaveCount(2);
  await expect(page.locator(".sheet").nth(0).locator(".label")).toHaveCount(PER_SHEET);
  await expect(page.locator(".sheet").nth(1).locator(".label")).toHaveCount(1);
  // Each label: its QR code, the code and site whole, the name
  const first = page.locator(".sheet .label").first();
  await expect(first.locator(".qr svg")).toBeVisible();
  await expect(first.locator(".label-site")).toHaveText("SMTW");
});

test("labels printed from the equipment list's ticks", { tag: "@device" }, async ({ page }) => {
  test.skip(page.viewportSize().width < 768, "the label ticks and Print labels are hidden on a phone (S064 D12)");
  await asPerson(page, "engineer", "/equipment");
  await page.getByLabel(`Select ${seed.extruder.code} for labels`).check();
  const [labelsTab] = await Promise.all([
    page.context().waitForEvent("page"),
    page.getByRole("button", { name: "Print labels (1)" }).click(),
  ]);
  await expect(labelsTab.getByText("1 label on 1 sheet")).toBeVisible();
  await expect(labelsTab.locator(".label-code")).toHaveText([seed.extruder.code]);
  await labelsTab.close();
});

test("the equipment page prints a node's label with its parts", async ({ page }) => {
  test.setTimeout(20_000);
  await asPerson(page, "engineer", `/equipment/${seed.extruder.id}`);
  await page.getByRole("button", { name: /Print label/ }).click();
  const [withParts] = await Promise.all([
    page.context().waitForEvent("page"),
    page.getByRole("button", { name: "This node and all its parts" }).click({ timeout: 5_000 }),
  ]);
  await expect(withParts.getByText("2 labels on 1 sheet")).toBeVisible();
  await expect(withParts.locator(".label-code")).toHaveText([seed.extruder.code, seed.gearbox.code]);
});

test("a label's link /e/<code> opens the equipment page", async ({ page }) => {
  await asPerson(page, "operator", `/e/${seed.extruder.code}`);
  await expect(page).toHaveURL(new RegExp(`/equipment/${seed.extruder.id}$`));
  await expect(page.getByRole("heading", { name: `${seed.extruder.code} — ${seed.extruder.name}` })).toBeVisible();
});

// S064 UX-03: a printed label exists, so a code the user may not open is never "doesn't exist"
test("S064: /e/<code> of a machine outside the user's units shows the code, not found or not at your units, and Go to equipment list", async ({ page, consoleWatch }) => {
  consoleWatch.allowFailedRequest("/api/equipment/by-code/", 404);
  await asPerson(page, "operator", `/e/${seed.mcc1Mill.code.toLowerCase()}`); // the operator reads MCC2 only
  const block = page.locator('[data-test="code-not-found"]');
  await expect(block.getByRole("heading", { name: seed.mcc1Mill.code, exact: true })).toBeVisible();
  await expect(block).toContainText("Not found, or not at your units. Ask your engineer if you should see it.");
  await expect(page.getByText("doesn't exist in Yantra")).toHaveCount(0);
  await block.getByRole("link", { name: "Go to equipment list" }).click();
  await expect(page).toHaveURL(/\/equipment$/);
});

// S064 UX-07: labels are printed by the office
test("S064: Print label is hidden for a technician and shown for an engineer on the equipment page", async ({ page }) => {
  await asPerson(page, "technician", `/equipment/${seed.extruder.id}`);
  await expect(page.getByRole("heading", { name: `${seed.extruder.code} — ${seed.extruder.name}` })).toBeVisible();
  await expect(page.getByRole("button", { name: /Print label/ })).toHaveCount(0);
  await asPerson(page, "engineer", `/equipment/${seed.extruder.id}`);
  await expect(page.getByRole("button", { name: /Print label/ })).toBeVisible();
});
