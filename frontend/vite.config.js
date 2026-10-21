import { defineConfig } from "vite";
import { configDefaults } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import { readFileSync } from "fs";

// Inject app version from the root VERSION file (single source of truth)
const appVersion = readFileSync("../VERSION", "utf-8").trim();

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "jsdom",
    // e2e/ holds the Playwright browser tests (S024), run by tooling/run-e2e-tests.bat
    exclude: [...configDefaults.exclude, "e2e/**"],
  },
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
  },
  server: {
    host: "0.0.0.0",
    port: 5176,
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
