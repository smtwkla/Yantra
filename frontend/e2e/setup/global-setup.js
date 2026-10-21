// Loads the seed (tooling/e2e/seed_e2e.py) into the e2e backend, which Playwright has
// started on an empty database (webServer), once before the tests.
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { BACKEND_URL } from "../support/stack.js";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

export default function globalSetup() {
  const result = spawnSync(
    "uv",
    ["run", "--project", "../backend", "python", "../tooling/e2e/seed_e2e.py", BACKEND_URL],
    { cwd: FRONTEND, stdio: "inherit", shell: true },
  );
  if (result.status !== 0) throw new Error(`The e2e seed failed (exit ${result.status}); see the lines above.`);
}
