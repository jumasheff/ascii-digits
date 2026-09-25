// Web Worker: runs the asciidigits Python package inside Pyodide.
//
// In:  {type: "init"}
//      {type: "styles" | "validate" | "preview", id, ...}   -> {type: "reply", id, result}
//      {type: "generate", settings}  -> "started", "progress"..., then "done" or "cancelled"
//      {type: "cancel"}              (checked between chunks)
// Out: {type: "loading", step, part, parts}, {type: "ready", defaults}, {type: "error", id, where, message},
//      {type: "busy"} (a "generate" while one runs: ignored, the running one carries on)
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";
import { VERSION } from "./version.js";

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const SITE = new URL("../", import.meta.url);          // the folder that holds index.html
// Every module the browser needs (tests/test_web_contract.py keeps this in sync with the package).
const PACKAGE_FILES = [
  "__init__.py", "augment.py", "dataset.py", "export.py", "figlet_render.py", "font_render.py",
  "outline.py", "rng.py", "sample.py", "settings.py", "splits.py", "styles.py", "webapi.py",
  "data/styles.json",
];
const CHUNK = 200;
const QUIET = { messageCallback: () => {} };

let pyodide = null;
let api = null;
let generating = false;
let cancelRequested = false;

self.onmessage = async ({ data: msg }) => {
  try {
    if (msg.type === "init") await init();
    else if (msg.type === "styles") reply(msg, api.styles_json(msg.width, msg.height));
    else if (msg.type === "validate") reply(msg, api.validate_json(JSON.stringify(msg.settings)));
    else if (msg.type === "preview") reply(msg, api.preview_json(JSON.stringify(msg.settings), 30));
    else if (msg.type === "generate") await generate(msg.settings);
    else if (msg.type === "cancel") cancelRequested = true;
  } catch (error) {
    self.postMessage({ type: "error", id: msg.id, where: msg.type, message: shortMessage(error) });
  }
};

function reply(msg, json) {
  self.postMessage({ type: "reply", id: msg.id, result: JSON.parse(json) });
}

// Python errors arrive with the whole traceback; the page shows only the last line.
function shortMessage(error) {
  const text = String(error && error.message ? error.message : error).trim();
  const last = text.split("\n").filter((line) => line.trim()).pop() || text;
  return last.replace(/^[\w.]*(SettingsError|FontMissingError|ValueError|RuntimeError): /, "");
}

async function fetchOk(path) {
  const response = await fetch(new URL(path, SITE));
  if (!response.ok) throw new Error(`could not load ${path} (HTTP ${response.status})`);
  return response;
}

function loading(step, part, parts) {
  self.postMessage({ type: "loading", step, part, parts });
}

async function init() {
  const parts = 5;
  loading("Loading Python", 1, parts);
  pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
  loading("Loading numpy and fontTools", 2, parts);
  await pyodide.loadPackage(["numpy", "fonttools"], QUIET);
  loading("Loading pyfiglet", 3, parts);
  await pyodide.loadPackage(new URL("wheels/pyfiglet-1.0.4-py3-none-any.whl", SITE).href, QUIET);
  loading("Loading the generator", 4, parts);
  pyodide.FS.mkdirTree("/home/pyodide/asciidigits/data");
  const sources = await Promise.all(PACKAGE_FILES.map(async (file) => (await fetchOk(`asciidigits/${file}`)).text()));
  PACKAGE_FILES.forEach((file, i) => pyodide.FS.writeFile(`/home/pyodide/asciidigits/${file}`, sources[i]));
  loading("Loading fonts", 5, parts);
  const manifest = await (await fetchOk("assets/fonts/manifest.json")).json();
  pyodide.FS.mkdirTree("/home/pyodide/fonts");
  const fonts = await Promise.all(manifest.fonts.map(async (font) => (await fetchOk(`assets/fonts/${font.file}`)).arrayBuffer()));
  manifest.fonts.forEach((font, i) => pyodide.FS.writeFile(`/home/pyodide/fonts/${font.file}`, new Uint8Array(fonts[i])));
  pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide')");
  api = pyodide.pyimport("asciidigits.webapi");
  api.configure("/home/pyodide/fonts");
  const defaults = JSON.parse(api.defaults_json());
  if (defaults.version !== VERSION) {
    throw new Error(`page ${VERSION} and generator ${defaults.version} differ: reload the page`);
  }
  self.postMessage({ type: "ready", defaults, pyodide: pyodide.version });
}

async function generate(settings) {
  if (generating) return self.postMessage({ type: "busy" });
  generating = true;
  cancelRequested = false;
  try {
    const info = JSON.parse(api.start(JSON.stringify(settings)));
    self.postMessage({ type: "started", info });
    let done = 0;
    while (done < info.total) {
      done = api.step(CHUNK);
      self.postMessage({ type: "progress", done, total: info.total });
      await new Promise((resolve) => setTimeout(resolve, 0));    // lets a "cancel" message in
      if (cancelRequested) {
        api.cancel();
        self.postMessage({ type: "cancelled" });
        return;
      }
    }
    const proxy = api.finish(`browser; pyodide ${pyodide.version}; ${self.navigator.userAgent}`);
    const zip = proxy.toJs().slice().buffer;
    proxy.destroy();
    self.postMessage({ type: "done", zip, filename: info.filename }, [zip]);
  } finally {
    generating = false;
  }
}
