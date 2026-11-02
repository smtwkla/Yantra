// The Help tour (S103): screenshots of the app on lane 9 for help/. The servers, the data and the
// lock are tooling/help/tour.py's; run it with tooling/help-shots.bat, not this file alone.
// Everything is written under scratch/help-shots/ (shots, data.json, Playwright's outputDir).
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "*.tour.js",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  outputDir: "../../scratch/help-shots/results",
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5189",
    timezoneId: "Asia/Kolkata",
    locale: "en-IN",
    serviceWorkers: "block",
    actionTimeout: 8000,
    navigationTimeout: 20000,
  },
  projects: [
    { name: "phone", testMatch: /phone.*\.tour\.js/, use: { ...devices["Pixel 7"], deviceScaleFactor: 2 } },
    {
      name: "desktop",
      testMatch: /desktop.*\.tour\.js/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 768 }, deviceScaleFactor: 1.5 },
    },
    {
      name: "documents",
      testMatch: /documents.*\.tour\.js/,
      use: { ...devices["Pixel 7"], deviceScaleFactor: 2 },
    },
  ],
});
