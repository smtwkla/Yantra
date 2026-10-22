// Merges the lanes' blob reports into the one HTML report (tooling/e2e/run_lanes.py:
// npx playwright merge-reports --config playwright.merge.config.js <blobs>).  The line
// reporter prints the failures and the totals once, for all lanes.
export default {
  testDir: "./e2e",
  reporter: [["line"], ["html", { outputFolder: "../scratch/e2e-report/html", open: "never" }]],
};
