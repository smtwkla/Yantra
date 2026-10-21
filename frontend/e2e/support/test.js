// The browser tests' own `test`: Playwright's, with the console watched on every page
// (watchConsole, § 5.3).  Specs import { test, expect } from here.
import { test as base, expect } from "@playwright/test";
import { watchConsole } from "./console.js";

export const test = base.extend({
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
