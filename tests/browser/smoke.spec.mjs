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

  // Changing settings or clicking again while a run is going.
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

// Old, hand-edited or broken links.
test("a link with invalid settings falls back to the defaults and says why", async ({ page }) => {
  await page.goto("index.html?w=99&styles=nope");
  await ready(page);
  await expect(page.locator("#notices")).toContainText("aren't valid (width must be 6 to 40, got 99)");
  await expect(page.locator("#width")).toHaveValue("16");
  await expect(page.locator("#preview .tile")).toHaveCount(30);
});

test("a link with an unknown style falls back to the defaults and says why", async ({ page }) => {
  await page.goto("index.html?styles=nope");
  await ready(page);
  await expect(page.locator("#notices")).toContainText("aren't valid (unknown style(s): nope)");
  await expect(page.locator("#styles input:checked")).not.toHaveCount(0);
  await expect(page.locator("#preview .tile")).toHaveCount(30);
});

test("a link with nan or infinite numbers falls back to the defaults and says why", async ({ page }) => {
  await page.goto("index.html?seed=nan&w=inf");
  await ready(page);
  await expect(page.locator("#notices")).toContainText("aren't valid (seed must be a whole number, got 'nan')");
  await expect(page.locator("#seed")).toHaveValue("42");
  await expect(page.locator("#preview .tile")).toHaveCount(30);
});

test("with no style selected there is nothing to preview or generate", async ({ page }) => {
  await page.goto("index.html?n=3,1,1");
  await ready(page);
  await expect(page.locator("#preview .tile")).toHaveCount(30);
  await page.locator("#no-styles").click();
  await expect(page.locator("#preview-message")).toHaveText("Select at least one style.");
  await expect(page.locator("#preview .tile")).toHaveCount(0);
  await expect(page.locator("#generate")).toBeDisabled();
});

test("after a size change, the link names exactly the styles in use", async ({ page }) => {
  await page.goto("index.html?n=3,1,1");
  await ready(page);
  const big = page.locator('#styles input[value="figlet:big"]');
  await big.uncheck();
  await big.check();                                          // an explicit choice: every style at 16x10
  await page.locator("#preset").selectOption("24x14");
  await expect(page.locator('#styles input[value="ttf:creepster"]')).toBeEnabled();   // the 24x14 list is in
  const inUse = await page.locator("#styles input:checked")
    .evaluateAll((boxes) => boxes.map((box) => box.value).sort().join(","));
  await expect.poll(() => (new URL(page.url()).searchParams.get("styles") || "").split(",").sort().join(","))
    .toBe(inUse);
});

test("a double-click on Generate starts one run and keeps the form locked", async ({ page }) => {
  await page.goto("index.html?n=100,20,20");
  await ready(page);
  await expect(page.locator("#preview .tile")).toHaveCount(30);
  await page.evaluate(() => {
    window.statuses = [];
    new MutationObserver(() => window.statuses.push(document.querySelector("#status").textContent))
      .observe(document.querySelector("#status"), { childList: true, characterData: true, subtree: true });
  });
  await page.locator("#generate").dblclick();
  await expect(page.locator("#status")).toHaveText("Done.", { timeout: 60_000 });
  const statuses = await page.evaluate(() => window.statuses);
  expect(statuses.filter((text) => text.startsWith("Stopped"))).toEqual([]);
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

// People double-click index.html instead of starting a server.
test("opening the file directly explains how to serve it", async ({ page }) => {
  await page.goto(pathToFileURL(join(process.cwd(), "..", "..", "index.html")).href);
  await expect(page.locator("#problem")).toContainText("python3 -m http.server 8000");
});
