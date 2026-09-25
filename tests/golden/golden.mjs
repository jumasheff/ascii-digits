// Runs asciidigits.selfcheck inside Pyodide (the same runtime as the web page)
// and prints the hashes as JSON. tests/test_golden.py compares them with
// tests/golden/expected.json.
import { loadPyodide } from "pyodide";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const GENERATOR = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const quiet = { messageCallback: () => {} };

function copyTree(py, from, to) {
  py.FS.mkdirTree(to);
  for (const name of readdirSync(from)) {
    if (name === "__pycache__") continue;
    const source = join(from, name);
    if (statSync(source).isDirectory()) copyTree(py, source, `${to}/${name}`);
    else py.FS.writeFile(`${to}/${name}`, readFileSync(source));
  }
}

const py = await loadPyodide();
await py.loadPackage(["numpy", "fonttools"], quiet);
await py.loadPackage(join(GENERATOR, "wheels", "pyfiglet-1.0.4-py3-none-any.whl"), quiet);
copyTree(py, join(GENERATOR, "asciidigits"), "/home/pyodide/asciidigits");
copyTree(py, join(GENERATOR, "assets", "fonts"), "/home/pyodide/fonts");
const hashes = py.runPython(`
import json, sys
sys.path.insert(0, "/home/pyodide")
from asciidigits.selfcheck import self_check
json.dumps(self_check("/home/pyodide/fonts"), sort_keys=True)
`);
console.log(JSON.stringify(JSON.parse(hashes), null, 2));
