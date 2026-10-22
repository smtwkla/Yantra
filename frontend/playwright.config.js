// Browser tests (S024): a real browser drives the real screens against the e2e backend
// (tooling/e2e/e2e_backend.py, port 5002, a throw-away database rebuilt at every start)
// through its own Vite (5177), so the dev servers on 5001 / 5176 keep running untouched.
// Run with tooling/run-e2e-tests.bat.  Report, traces and screenshots: scratch/e2e-report/.
// Lanes (tooling/e2e/run_lanes.py): with E2E_LANE=<n> this run is one shard of several, on its
// own stack (stack.js); it writes a blob report that the runner merges into the one HTML report.
import { defineConfig, devices } from "@playwright/test";
import { BACKEND_URL, FRONTEND_PORT, FRONTEND_URL, LANE_NAME } from "./e2e/support/stack.js";

const REPORT_DIR = "../scratch/e2e-report";
const LANE_SUFFIX = LANE_NAME ? `-${LANE_NAME}` : "";

export default defineConfig({
  testDir: "./e2e",
  // One database per stack: one file at a time on it, so tests cannot race (§ 5.2); lanes
  // give the speed instead, each with its own database
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  globalSetup: "./e2e/setup/global-setup.js",
  outputDir: LANE_NAME ? `${REPORT_DIR}/results/${LANE_NAME}` : `${REPORT_DIR}/results`,
  reporter: LANE_NAME
    ? [["list"], ["blob", { outputDir: `${REPORT_DIR}/blobs/${LANE_NAME}` }]]
    : [["list"], ["html", { outputFolder: `${REPORT_DIR}/html`, open: "never" }]],
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
      command: `uv run --project ../backend python ../tooling/e2e/e2e_backend.py > ../scratch/e2e-backend${LANE_SUFFIX}.log 2>&1`,
      url: `${BACKEND_URL}/api/health`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npx vite --host 127.0.0.1 --port ${FRONTEND_PORT} --strictPort`,
      url: FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { YANTRA_API_URL: BACKEND_URL },
    },
  ],
});
