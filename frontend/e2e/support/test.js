// The browser tests' own `test`: Playwright's, with the console watched on every page
// (watchConsole, § 5.3).  Specs import { test, expect } from here.
import { test as base, expect } from "@playwright/test";
import { watchConsole } from "./console.js";

export const test = base.extend({
  // Auto: a WebKit window must be as wide as its device (S045).  With Windows display scaling
  // above 100 %, Playwright's WebKit makes the window narrower (125 % gives 312 px, not the
  // iPhone 14's 390), and a focus scroll then puts a dialog's buttons off screen, which a real
  // phone cannot do.  Such a run proves nothing, so stop it with the reason.
  windowWidthGuard: [
    async ({ page, browserName }, use, testInfo) => {
      const expected = testInfo.project.use.viewport?.width;
      if (browserName === "webkit" && expected) {
        // A page with a device-width viewport: a bare about:blank reports a wider, unscaled width
        await page.setContent('<meta name="viewport" content="width=device-width, initial-scale=1">');
        const actual = await page.evaluate(() => window.innerWidth);
        if (actual !== expected) {
          throw new Error(
            `The ${testInfo.project.name} window is ${actual} px wide, not ${expected}. `
            + "Set Windows display scale to 100 % and sign in again.");
        }
      }
      await use();
    },
    { auto: true },
  ],

  // Auto: every test's page is watched, and the test fails at its end on any problem
  consoleWatch: [
    async ({ page }, use) => {
      const watch = watchConsole(page);
      await use(watch);
      expect(watch.problems, "console errors, Vue warnings or uncaught errors on the page").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };
