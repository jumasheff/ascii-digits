import { execFileSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { expect, test } from "@playwright/test";

const ready = (page) => expect(page.locator("#form")).toBeVisible();

function zipNames(path) {
  const out = execFileSync("python3", ["-c", "import sys, zipfile; print(','.join(sorted(zipfile.ZipFile(sys.argv[1]).namelist())))", path]);
  return out.toString().trim();
}

test.describe.serial("one loaded page", () => {
  let page;
  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto("index.html?n=3,1,1&seed=5");
    await ready(page);
  });
  test.afterAll(async () => page.close());

  test("shows 30 preview samples", async () => {
    await expect(page.locator("#preview .tile")).toHaveCount(30);
    const text = await page.locator("#preview .tile pre").first().textContent();
    expect(text.split("\n")).toHaveLength(10);
  });

  test("generates a small dataset and downloads a valid zip", async () => {
    const download = page.waitForEvent("download");
    await page.locator("#generate").click();
    await expect(page.locator("#download")).toBeVisible();
    await page.locator("#download").click();
    const path = join(mkdtempSync(join(tmpdir(), "digits-")), "set.zip");
    await (await download).saveAs(path);
    expect(zipNames(path)).toBe("README.txt,metadata.json,test.jsonl,train.jsonl,val.jsonl");
    expect((await download).suggestedFilename()).toBe("ascii-digits-5.zip");
  });

  // Review focus: changing settings or clicking again while a run is going.
  test("locks the settings during a run, and Cancel stops it", async () => {
    await page.locator("#train").fill("500");
    await page.locator("#val").fill("100");
    await page.locator("#test").fill("100");
    await page.locator("#generate").click();
    await expect(page.locator("#width")).toBeDisabled();      // every control in the settings fieldset
    await expect(page.locator("#generate")).toBeDisabled();
    await expect(page.locator("#status")).toContainText("of 7,000 samples", { timeout: 60_000 });
    await page.locator("#cancel").click();
    await expect(page.locator("#status")).toHaveText("Cancelled.");
    await expect(page.locator("#width")).toBeEnabled();
    await expect(page.locator("#download")).toBeHidden();
  });

  test("keeps the settings in the URL", async () => {
    await page.locator("#seed").fill("77");
    await expect(page).toHaveURL(/seed=77/);
    await expect(page).toHaveURL(/v=1\.0\.0/);
  });
});

// Review focus: old, hand-edited or broken links.
test("a link with invalid settings falls back to the defaults and says why", async ({ page }) => {
  await page.goto("index.html?w=99&styles=nope");
  await ready(page);
  await expect(page.locator("#notices")).toContainText("aren't valid (width must be 6 to 40, got 99)");
  await expect(page.locator("#width")).toHaveValue("16");
  await expect(page.locator("#preview .tile")).toHaveCount(30);
});

test("a link from another version points to that version's page", async ({ page }) => {
  await page.goto("index.html?v=0.9.0&seed=3");
  await ready(page);
  const link = page.locator("#notices a");
  await expect(link).toHaveText("Open version 0.9.0");
  await expect(link).toHaveAttribute("href", "/v0.9.0/?v=0.9.0&seed=3");
});

test("a font that fails to load stops with a clear message", async ({ page }) => {
  await page.route("**/assets/fonts/Caveat.ttf", (route) => route.fulfill({ status: 404, body: "" }));
  await page.goto("index.html");
  await expect(page.locator("#problem")).toContainText("could not load assets/fonts/Caveat.ttf (HTTP 404)");
  await expect(page.locator("#retry")).toBeVisible();
});

// Review focus: people double-click index.html instead of starting a server.
test("opening the file directly explains how to serve it", async ({ page }) => {
  await page.goto(pathToFileURL(join(process.cwd(), "..", "..", "index.html")).href);
  await expect(page.locator("#problem")).toContainText("python3 -m http.server 8000");
});
