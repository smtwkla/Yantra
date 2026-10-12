import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { readFileSync } from "fs";

// Inject app version from the root VERSION file (single source of truth)
const appVersion = readFileSync("../VERSION", "utf-8").trim();

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "jsdom",
  },
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
  },
  server: {
    host: "0.0.0.0",
    port: 5176,
    proxy: {
      "/api": {
        target: "http://localhost:5001",
        changeOrigin: true,
      },
    },
  },
});
