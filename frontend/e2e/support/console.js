// watchConsole(page) — a browser test fails on what a person would not see but a broken screen
// leaves behind (S024 § 5.3): any console.error, any Vue warning, any uncaught page error.
// The allow-list is exactly two sources, so any new warning still fails:
// - the auth store's own "Auth bypass: DEV_AUTH_BYPASS enabled on backend." line;
// - Vite's client messages ("[vite] ...").
// A test that expects a refused request (a 403 or 404 page) names it with
// allowFailedRequest(urlPart, status): the browser's "Failed to load resource" line for that
// request only, matched by URL and status.

const ALLOWED = [
  (text) => text.includes("Auth bypass: DEV_AUTH_BYPASS enabled on backend."),
  (text) => text.startsWith("[vite]"),
];
const FAILED_RESOURCE = "Failed to load resource";

export function watchConsole(page) {
  const problems = [];
  const expectedFailures = [];

  const expectedFailure = (msg) => {
    if (!msg.text().includes(FAILED_RESOURCE)) return false;
    const url = msg.location()?.url ?? "";
    return expectedFailures.some(({ urlPart, status }) => url.includes(urlPart) && msg.text().includes(String(status)));
  };

  page.on("console", (msg) => {
    const text = msg.text();
    if (ALLOWED.some((allowed) => allowed(text))) return;
    const vueWarning = msg.type() === "warning" && text.startsWith("[Vue warn]");
    if ((msg.type() === "error" || vueWarning) && !expectedFailure(msg)) {
      problems.push(`console.${msg.type()}: ${text} (${msg.location()?.url ?? "?"})`);
    }
  });
  page.on("pageerror", (err) => problems.push(`uncaught error: ${err.message}`));

  return {
    allowFailedRequest(urlPart, status) {
      expectedFailures.push({ urlPart, status });
    },
    problems,
  };
}
