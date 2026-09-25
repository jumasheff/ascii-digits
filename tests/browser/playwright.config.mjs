import { defineConfig } from "@playwright/test";

// Serves the repository root and runs the smoke tests in Chromium.
// Pyodide itself comes from jsdelivr, so these tests need the internet.
export default defineConfig({
  testDir: ".",
  timeout: 240_000,
  expect: { timeout: 180_000 },
  workers: 1,
  use: { baseURL: "http://127.0.0.1:8123/" },
  webServer: {
    command: "python3 -m http.server 8123 --bind 127.0.0.1 --directory ../..",
    url: "http://127.0.0.1:8123/index.html",
    reuseExistingServer: true,
  },
});
