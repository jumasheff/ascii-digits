// Not part of the smoke tests: measures generation time and the cell cap.
//   npx playwright test timing.spec.mjs --reporter=line
import { expect, test } from "@playwright/test";

for (const [name, query] of [
  ["default dataset, 7,000 samples at 16x10", "index.html"],
  ["largest allowed run, 8,330 samples at 40x24", "index.html?w=40&h=24&n=633,100,100"],
]) {
  test(name, async ({ page }) => {
    test.setTimeout(900_000);
    await page.goto(query);
    await expect(page.locator("#form")).toBeVisible();
    const started = Date.now();
    await page.locator("#generate").click();
    await expect(page.locator("#download")).toBeVisible({ timeout: 900_000 });
    const seconds = (Date.now() - started) / 1000;
    console.log(`${name}: ${seconds.toFixed(1)} s`);
  });
}
