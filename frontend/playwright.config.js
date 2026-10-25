// Browser tests (S024): a real browser drives the real screens against the e2e backend
// (tooling/e2e/e2e_backend.py, port 5002, a throw-away database rebuilt at every start)
// through its own Vite (5177), so the dev servers on 5001 / 5176 keep running untouched.
// Run with tooling/run-e2e-tests.bat.  Report, traces and screenshots: scratch/e2e-report/.
// Lanes (tooling/e2e/run_lanes.py): with E2E_LANE=<n> this run is one lane of several, on its
// own stack (stack.js); it writes a blob report that the runner merges into the one HTML report.
// Levels (S047, S055): E2E_LEVEL (set by run_lanes.py when the level chose the projects) runs only
// the @device tests on desktop-chromium at normal, and on desktop-chromium and phone-webkit at
// full; the logic tests run on phone-chromium.  E2E_LANE_PLAN (JSON {project: [spec files]},
// run_lanes.py's plan for this lane) keeps only the plan's projects, each with its own files.
import { defineConfig, devices } from "@playwright/test";
import { BACKEND_URL, FRONTEND_PORT, FRONTEND_URL, LANE_NAME } from "./e2e/support/stack.js";

const REPORT_DIR = "../scratch/e2e-report";
const LANE_SUFFIX = LANE_NAME ? `-${LANE_NAME}` : "";
const LANE_PLAN = process.env.E2E_LANE_PLAN ? JSON.parse(process.env.E2E_LANE_PLAN) : null;
const DEVICE_ONLY_BY_LEVEL = {
  normal: ["desktop-chromium"],
  full: ["desktop-chromium", "phone-webkit"],
};
const DEVICE_ONLY = DEVICE_ONLY_BY_LEVEL[process.env.E2E_LEVEL] ?? [];

const PROJECTS = [
  { name: "phone-chromium", use: { ...devices["Pixel 7"] } },
  // WebKit is Safari's engine, not iOS Safari itself: no on-screen keyboard, no camera (§ 7.7)
  // With E2E_WEBKIT_WS (set by run_lanes.py, S046) the browser runs in a Linux container, where
  // the window is exactly 390 px; exposeNetwork carries its requests to 127.0.0.1 back to the host
  {
    name: "phone-webkit",
    use: {
      ...devices["iPhone 14"],
      ...(process.env.E2E_WEBKIT_WS
        ? { connectOptions: { wsEndpoint: process.env.E2E_WEBKIT_WS, exposeNetwork: "<loopback>" } }
        : {}),
    },
  },
  { name: "desktop-chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 768 } } },
]
  .map((project) => (DEVICE_ONLY.includes(project.name) ? { ...project, grep: /@device/ } : project))
  .filter((project) => !LANE_PLAN || project.name in LANE_PLAN)
  // A plain file name in testMatch matches as **/<name>
  .map((project) => (LANE_PLAN ? { ...project, testMatch: LANE_PLAN[project.name] } : project));

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
  projects: PROJECTS,
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
      // Its own dependency cache per stack (vite.config.js cacheDir, S047)
      env: { YANTRA_API_URL: BACKEND_URL, E2E_VITE_CACHE_DIR: `../scratch/e2e-vite${LANE_SUFFIX}` },
    },
  ],
});
