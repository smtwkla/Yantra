import { defineConfig, searchForWorkspaceRoot } from "vite";
import { configDefaults } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import { readFileSync, realpathSync } from "fs";
import { fileURLToPath } from "url";

// tooling/release-tests.bat links node_modules into its worktree by a junction (S047: the
// release runs the browser tests there).  Vite serves a dependency's files (the icon fonts) by
// their real path, which is then in the working folder, outside the worktree, and refuses them
// with 403.  So the real node_modules is allowed too; in a normal checkout it is inside the root.
const nodeModules = realpathSync(new URL("./node_modules", import.meta.url));

// Inject app version from the root VERSION file (single source of truth)
const appVersion = readFileSync("../VERSION", "utf-8").trim();
// The change log (S048): required, like VERSION; the Docker build copies it too
const appChangelog = readFileSync("../CHANGELOG.md", "utf-8");

export default defineConfig({
  plugins: [vue()],
  // The browser tests give each lane's Vite its own dependency cache (playwright.config.js, S047):
  // six servers optimising into one node_modules/.vite at once race on its rename (EPERM), and a
  // release worktree would rewrite the working folder's cache through its node_modules junction
  cacheDir: process.env.E2E_VITE_CACHE_DIR || "node_modules/.vite",
  test: {
    environment: "jsdom",
    // e2e/ holds the Playwright browser tests (S024), run by tooling/run-e2e-tests.bat
    exclude: [...configDefaults.exclude, "e2e/**"],
  },
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
    __APP_CHANGELOG__: JSON.stringify(appChangelog),
  },
  server: {
    host: "0.0.0.0",
    port: 5176,
    // from the config's own folder, not the process's: a start from the repo root must not
    // serve the whole repo (backend/secrets_app.py) on a server bound to 0.0.0.0
    fs: { allow: [searchForWorkspaceRoot(fileURLToPath(new URL(".", import.meta.url))), nodeModules] },
    proxy: {
      "/api": {
        // The e2e run points it at its own backend (S024: 127.0.0.1, as Node may resolve
        // localhost to ::1 and the backend binds IPv4 only)
        target: process.env.YANTRA_API_URL || "http://localhost:5001",
        changeOrigin: true,
      },
    },
  },
});
