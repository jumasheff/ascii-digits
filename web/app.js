// The page: settings form, URL state, preview, generate / cancel / download.
// All generation happens in web/worker.js; this file never renders digits itself.
import { VERSION } from "./version.js";

const $ = (selector) => document.querySelector(selector);
const RANGES = ["noise", "rotation", "shift", "size_jitter", "ink_swap"];
// URL parameter -> setting. Short keys keep shared links readable.
const URL_KEYS = {
  seed: "seed", w: "width", h: "height", n: "per_digit", split: "split_mode", styles: "styles",
  ink: "ink_modes", noise: "noise", rot: "rotation", shift: "shift", sj: "size_jitter", swap: "ink_swap",
};
const LIST_SETTINGS = new Set(["per_digit", "styles", "ink_modes"]);

const state = {
  worker: null, defaults: null, styles: [], selected: null,   // selected: Set of ids, or null = all available
  pending: new Map(), nextId: 1, previewId: 0, previewTimer: null, generating: false, downloadUrl: null,
};

start();

function start() {
  $("#version").textContent = VERSION;
  if (location.protocol === "file:") return;         // index.html's inline script explains
  if (typeof WebAssembly !== "object" || typeof Worker !== "function") {
    return problem("This browser can't run the generator (it needs WebAssembly and Web Workers). Try a current Chrome, Firefox, Safari or Edge.");
  }
  $("#retry").addEventListener("click", () => location.reload());
  bindForm();
  startWorker();
}

// ---- worker ----------------------------------------------------------------

function startWorker() {
  state.worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
  state.worker.onmessage = ({ data }) => onWorkerMessage(data);
  state.worker.onerror = (event) => problem(`The generator failed to start: ${event.message || "unknown error"}`, true);
  state.worker.postMessage({ type: "init" });
}

function request(type, payload) {
  const id = state.nextId++;
  return new Promise((resolve, reject) => {
    state.pending.set(id, { resolve, reject });
    state.worker.postMessage({ type, id, ...payload });
  });
}

function onWorkerMessage(msg) {
  if (msg.type === "loading") {
    $("#loading-text").textContent = `${msg.step}… (${msg.part} of ${msg.parts})`;
    $("#loading-bar").value = msg.part - 1;
  } else if (msg.type === "ready") {
    onReady(msg.defaults);
  } else if (msg.type === "reply" || (msg.type === "error" && state.pending.has(msg.id))) {
    const waiter = state.pending.get(msg.id);
    state.pending.delete(msg.id);
    if (msg.type === "reply") waiter.resolve(msg.result);
    else waiter.reject(new Error(msg.message));
  } else if (msg.type === "started") {
    showNotices(msg.info.notices);
    $("#progress").max = msg.info.total;
  } else if (msg.type === "progress") {
    $("#progress").value = msg.done;
    $("#status").textContent = `${msg.done.toLocaleString()} of ${msg.total.toLocaleString()} samples`;
  } else if (msg.type === "done") {
    finishGeneration(msg.zip, msg.filename);
  } else if (msg.type === "cancelled") {
    endGeneration("Cancelled.");
  } else if (msg.type === "error") {
    if (msg.where === "init") problem(`The generator failed to load: ${msg.message}`, true);
    else if (msg.where === "generate") endGeneration(`Stopped: ${msg.message}`);
    else problem(msg.message);
  }
}

// ---- startup ---------------------------------------------------------------

async function onReady(defaults) {
  state.defaults = defaults;
  $("#loading").hidden = true;
  $("#form").hidden = false;
  setUpControls(defaults);
  const params = new URLSearchParams(location.search);
  const linkVersion = params.get("v");
  if (linkVersion && linkVersion !== VERSION) {
    const shown = escapeHtml(linkVersion);
    notice(`This link was made with generator version ${shown}; this page is ${VERSION}, so the same ` +
      `settings may give a different dataset. <a href="${escapeHtml(versionedPage(linkVersion))}">Open version ${shown}</a>.`);
  }
  let settings = defaults.settings;
  const fromUrl = settingsFromUrl(params);
  if (Object.keys(fromUrl).length) {
    const check = await request("validate", { settings: fromUrl });
    if (check.ok) settings = check.settings;
    else notice(`This link's settings aren't valid (${escapeHtml(check.error)}), so the defaults are shown instead.`);
  }
  state.selected = settings.styles.length ? new Set(settings.styles) : null;
  writeForm(settings);
  await refreshStyles();
  onChange();
}

function setUpControls(defaults) {
  const preset = $("#preset");
  for (const [name, [w, h]] of Object.entries(defaults.presets)) {
    preset.add(new Option(`${w} × ${h}`, name));
  }
  preset.add(new Option("Custom", "custom"));
  const { width, height } = defaults.limits;
  Object.assign($("#width"), { min: width[0], max: width[1] });
  Object.assign($("#height"), { min: height[0], max: height[1] });
  for (const name of RANGES) {
    const [low, high] = defaults.limits[name];
    Object.assign($(`#${name}`), { min: low, max: high });
  }
}

// ---- form <-> settings -----------------------------------------------------

function bindForm() {
  $("#form").addEventListener("input", (event) => {
    if (event.target.id === "preset") applyPreset();
    if (event.target.id === "width" || event.target.id === "height") syncPreset();
    onChange(event.target.id === "preset" || event.target.id === "width" || event.target.id === "height");
  });
  $("#form").addEventListener("submit", (event) => { event.preventDefault(); generate(); });
  $("#cancel").addEventListener("click", () => {
    state.worker.postMessage({ type: "cancel" });
    $("#status").textContent = "Cancelling…";
  });
  $("#new-seed").addEventListener("click", () => {
    $("#seed").value = Math.floor(Math.random() * 2 ** 31);
    onChange();
  });
  $("#all-styles").addEventListener("click", () => { state.selected = null; renderStyles(); onChange(); });
  $("#no-styles").addEventListener("click", () => { state.selected = new Set(); renderStyles(); onChange(); });
}

function applyPreset() {
  const name = $("#preset").value;
  if (name === "custom") return;
  const [w, h] = state.defaults.presets[name];
  $("#width").value = w;
  $("#height").value = h;
}

function syncPreset() {
  const size = `${$("#width").value}x${$("#height").value}`;
  $("#preset").value = size in state.defaults.presets ? size : "custom";
}

function readForm() {
  const available = state.styles.filter((s) => !s.reason).map((s) => s.id);
  const styles = state.selected === null ? [] : available.filter((id) => state.selected.has(id));
  return {
    seed: Number($("#seed").value),
    width: Number($("#width").value),
    height: Number($("#height").value),
    per_digit: ["#train", "#val", "#test"].map((id) => Number($(id).value)),
    split_mode: document.querySelector('input[name="split"]:checked').value,
    styles: state.selected !== null && styles.length === available.length ? [] : styles,
    ink_modes: [...document.querySelectorAll('input[name="ink"]:checked')].map((box) => box.value),
    ...Object.fromEntries(RANGES.map((name) => [name, Number($(`#${name}`).value)])),
  };
}

function writeForm(s) {
  $("#seed").value = s.seed;
  $("#width").value = s.width;
  $("#height").value = s.height;
  syncPreset();
  ["#train", "#val", "#test"].forEach((id, i) => { $(id).value = s.per_digit[i]; });
  document.querySelector(`input[name="split"][value="${s.split_mode}"]`).checked = true;
  for (const box of document.querySelectorAll('input[name="ink"]')) box.checked = s.ink_modes.includes(box.value);
  for (const name of RANGES) $(`#${name}`).value = s[name];
  updateOutputs();
}

function updateOutputs() {
  for (const name of RANGES) $(`output[for="${name}"]`).textContent = $(`#${name}`).value;
  const s = readForm();
  const total = 10 * s.per_digit.reduce((a, b) => a + b, 0);
  $("#total").textContent = `${total.toLocaleString()} samples`;
}

function onChange(sizeChanged = false) {
  if (!state.defaults) return;
  updateOutputs();
  history.replaceState(null, "", `?${settingsToUrl(readForm())}`);
  clearTimeout(state.previewTimer);
  state.previewTimer = setTimeout(async () => {
    if (sizeChanged) await refreshStyles();
    preview();
  }, 300);
}

// ---- URL -------------------------------------------------------------------

function settingsFromUrl(params) {
  const settings = {};
  for (const [key, name] of Object.entries(URL_KEYS)) {
    if (!params.has(key)) continue;
    const value = params.get(key);
    settings[name] = LIST_SETTINGS.has(name) ? value.split(",").filter(Boolean) : value;
  }
  return settings;
}

function settingsToUrl(s) {
  const params = new URLSearchParams({ v: VERSION });
  const defaults = state.defaults.settings;
  for (const [key, name] of Object.entries(URL_KEYS)) {
    const value = LIST_SETTINGS.has(name) ? s[name].join(",") : String(s[name]);
    const fallback = LIST_SETTINGS.has(name) ? defaults[name].join(",") : String(defaults[name]);
    if (value !== fallback) params.set(key, value);
  }
  return params.toString();
}

// Old links open the matching release, kept under <site>/v<version>/.
function versionedPage(version) {
  const root = location.pathname.replace(/v\d+\.\d+\.\d+\/(index\.html)?$/, "").replace(/index\.html$/, "");
  return `${root}v${encodeURIComponent(version)}/${location.search}`;
}

// ---- styles ----------------------------------------------------------------

async function refreshStyles() {
  const width = Number($("#width").value);
  const height = Number($("#height").value);
  try {
    state.styles = await request("styles", { width, height });
  } catch (error) {
    state.styles = [];
  }
  renderStyles();
}

function renderStyles() {
  const box = $("#styles");
  box.replaceChildren();
  const families = {};
  for (const style of state.styles) (families[style.family] ||= []).push(style);
  for (const [family, styles] of Object.entries(families)) {
    const group = document.createElement("div");
    group.className = "family";
    group.innerHTML = `<h3>${escapeHtml(family)}</h3>`;
    for (const style of styles) {
      const label = document.createElement("label");
      const input = Object.assign(document.createElement("input"), {
        type: "checkbox", value: style.id, disabled: Boolean(style.reason),
        checked: !style.reason && (state.selected === null || state.selected.has(style.id)),
      });
      input.addEventListener("change", () => {
        if (state.selected === null) {
          state.selected = new Set(state.styles.filter((s) => !s.reason).map((s) => s.id));
        }
        if (input.checked) state.selected.add(style.id); else state.selected.delete(style.id);
        onChange();
      });
      label.append(input, ` ${style.name}`);
      if (style.reason) {
        label.className = "unavailable";
        label.append(Object.assign(document.createElement("span"), { className: "reason hint", textContent: style.reason }));
      }
      group.append(label);
    }
    box.append(group);
  }
}

// ---- preview ---------------------------------------------------------------

async function preview() {
  if (state.generating) return;
  const id = ++state.previewId;
  const settings = readForm();
  try {
    const samples = await request("preview", { settings });
    if (id !== state.previewId) return;                // a newer preview is on its way
    $("#preview-message").textContent = "";
    $("#preview").replaceChildren(...samples.map(tile));
  } catch (error) {
    if (id !== state.previewId) return;
    $("#preview-message").textContent = `No preview: ${error.message}`;
    $("#preview").replaceChildren();
  }
}

function tile(sample) {
  const figure = document.createElement("figure");
  figure.className = "tile";
  const pre = document.createElement("pre");
  pre.textContent = sample.rows.join("\n");
  const caption = document.createElement("figcaption");
  caption.textContent = `${sample.label} · ${sample.name}`;
  figure.append(pre, caption);
  return figure;
}

// ---- generate --------------------------------------------------------------

async function generate() {
  if (state.generating) return;
  const settings = readForm();
  const check = await request("validate", { settings });
  if (!check.ok) {
    $("#status").textContent = `Can't generate: ${check.error}`;
    return;
  }
  state.generating = true;
  $("#settings").disabled = true;
  $("#generate").disabled = true;
  $("#cancel").hidden = false;
  Object.assign($("#progress"), { hidden: false, value: 0 });
  $("#download").hidden = true;
  $("#notices").replaceChildren();
  $("#status").textContent = "Starting…";
  state.worker.postMessage({ type: "generate", settings: check.settings });
}

function finishGeneration(zip, filename) {
  if (state.downloadUrl) URL.revokeObjectURL(state.downloadUrl);
  state.downloadUrl = URL.createObjectURL(new Blob([zip], { type: "application/zip" }));
  Object.assign($("#download"), {
    href: state.downloadUrl, download: filename, hidden: false,
    textContent: `Download ${filename} (${(zip.byteLength / 1048576).toFixed(1)} MB)`,
  });
  endGeneration("Done.");
}

function endGeneration(message) {
  state.generating = false;
  $("#settings").disabled = false;
  $("#generate").disabled = false;
  $("#cancel").hidden = true;
  $("#progress").hidden = true;
  $("#status").textContent = message;
}

// ---- messages --------------------------------------------------------------

function problem(message, canRetry = false) {
  $("#loading").hidden = true;
  $("#problem").hidden = false;
  $("#problem-text").textContent = message;
  $("#retry").hidden = !canRetry;
}

function notice(html) {
  const p = document.createElement("p");
  p.innerHTML = html;
  $("#notices").append(p);
}

function showNotices(notices) {
  for (const text of notices) notice(`Note: ${escapeHtml(text)}.`);
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}
