// Browser tests (S024): a real browser drives the real screens against the e2e backend
// (tooling/e2e/e2e_backend.py, port 5002, a throw-away database rebuilt at every start)
// through its own Vite (5177), so the dev servers on 5001 / 5176 keep running untouched.
// Run with tooling/run-e2e-tests.bat.  Report, traces and screenshots: scratch/e2e-report/.
import { defineConfig, devices } from "@playwright/test";
import { BACKEND_URL, FRONTEND_URL } from "./e2e/support/stack.js";

const REPORT_DIR = "../scratch/e2e-report";

export default defineConfig({
  testDir: "./e2e",
  // One database for the whole run: one file at a time, so tests cannot race (§ 5.2)
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  globalSetup: "./e2e/setup/global-setup.js",
  outputDir: `${REPORT_DIR}/results`,
  reporter: [["list"], ["html", { outputFolder: `${REPORT_DIR}/html`, open: "never" }]],
  use: {
    baseURL: FRONTEND_URL,
    // The plant and its phones are in IST, and the server reads typed times as IST
    timezoneId: "Asia/Kolkata",
    locale: "en-IN",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "phone-chromium", use: { ...devices["Pixel 7"] } },
    // WebKit is Safari's engine, not iOS Safari itself: no on-screen keyboard, no camera (§ 7.7)
    { name: "phone-webkit", use: { ...devices["iPhone 14"] } },
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 768 } } },
  ],
  // Never reused: a server left running has not been reset
  webServer: [
    {
      command: "uv run --project ../backend python ../tooling/e2e/e2e_backend.py > ../scratch/e2e-backend.log 2>&1",
      url: `${BACKEND_URL}/api/health`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npx vite --host 127.0.0.1 --port 5177 --strictPort",
      url: FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { YANTRA_API_URL: BACKEND_URL },
    },
  ],
});
