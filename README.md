# ASCII digit generator

A webpage (and a command-line tool) that generates labelled train /
validation / test sets of ASCII-art digits in many styles: cursive, comic and
handwriting, wild display fonts, and FIGlet ASCII fonts. Everything runs in
the visitor's browser: Python via [Pyodide](https://pyodide.org), no server.

## Run the page locally

```bash
python3 -m http.server 8000
# open http://localhost:8000/
```

Opening `index.html` directly (a `file://` address) doesn't work: browsers
won't run the page's scripts from files. The page says so.

The first visit downloads about 13 MB: Python, numpy, fontTools and
pyfiglet. The browser caches it afterwards.

## Command line

The CLI produces the same data files as the page (see "Reproducibility").

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt

python -m asciidigits generate --seed 42                 # ascii-digits-42.zip, default settings
python -m asciidigits generate --seed 7 --size 24x14 --split random --per-digit 200 50 50
python -m asciidigits styles --size 8x6                  # which styles fit a grid, and why not
```

## The download

`ascii-digits-<seed>.zip` contains `train.jsonl`, `val.jsonl`, `test.jsonl`,
`metadata.json` and `README.txt`. One sample per line:

```json
{"id": "train-000123", "label": 7, "style": "figlet:big", "family": "figlet", "rows": ["...16 characters...", "...10 rows..."]}
```

- `rows` always has exactly `height` strings of exactly `width` characters.
- `metadata.json` records the settings, the styles in each split, the counts,
  `dataset_sha256`, and where and when it was made.

## Loading a set

`README.txt` inside every zip has a 12-line, standard-library loader. It turns
each sample into `(vector, label)` pairs: blank -> 0, any other character -> 1.

## Reproducibility

The same seed, settings and generator version give byte-identical
`train.jsonl`, `val.jsonl` and `test.jsonl`. That holds in every browser and
from the CLI on Linux and macOS (see "Windows").

- **How it's checked:** CI enforces it with `tests/golden/expected.json`.
- **How it works:** glyphs are filled by our own numpy code (`outline.py`)
  from the fonts' unhinted outlines, not by FreeType. FreeType versions
  differ between platforms and rendered hinted fonts differently.
- **What does differ:** the zip file and `metadata.json`'s `provenance` block
  (runtime, time) can differ. To compare two datasets, compare
  `dataset_sha256`.

Links carry the generator version (`?v=1.0.0`). Every release stays online
under `/v<version>/`, so an old link still produces its original data.

## Windows

Windows isn't supported for now.

- **The page** works in a browser on Windows like anywhere else: every
  browser runs the same WebAssembly build.
- **The command line** isn't tested on Windows, and CI doesn't run there, so
  its output on Windows isn't checked against the reference hashes. Use the
  page, or the CLI on Linux or macOS.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q                                   # unit, CLI, CPython golden
(cd tests/golden && npm ci) && python -m pytest -q    # adds the Pyodide golden test (needs Node.js)
(cd tests/browser && npm ci && npx playwright install chromium && npx playwright test)   # the page
(cd tests/browser && npx playwright test timing.spec.mjs --reporter=line)               # speed
```

If an intentional change alters the output (new styles, a rendering fix),
regenerate the reference and review the diff:

```bash
cd tests/golden && node golden.mjs > expected.json
```

## Curating styles

A style ships only after a person has checked it's readable at each grid
preset.

1. Screen the FIGlet fonts: `python tools/screen_figlet.py` writes
   `tools/figlet_candidates.json`.
2. Write one sheet per preset:
   ```bash
   python -m asciidigits sheet --size 16x10 --ignore-presets --figlet-candidates tools/figlet_candidates.json --out sheets/16x10.txt
   ```
   Do the same for 8x6, 12x8 and 24x14.
3. Record the decisions in `tools/curation.json`. For each TTF style, list
   the presets where all ten digits are readable in the clean row and both
   damaged rows. List up to 40 FIGlet fonts, varied, without near-duplicates.
4. Apply them: `python tools/apply_curation.py` rewrites
   `asciidigits/data/styles.json` and prints the styles per family at each
   preset.
5. Regenerate the golden reference (see "Tests"), run the tests, and commit.

## Fonts

- **Source:** the 17 TTF fonts in `assets/fonts/` come from
  [google/fonts](https://github.com/google/fonts), at the commit pinned in
  `assets/fonts/manifest.json`. They are unmodified.
- **Licenses:** OFL 1.1 or Apache 2.0, each with its license in
  `assets/fonts/licenses/`.
- **Re-downloading:** `python tools/fetch_fonts.py` downloads them again and
  checks every SHA-256.
- **FIGlet fonts:** they come with pyfiglet 1.0.4 (`wheels/`).

## Deploy

The site is static. `python tools/build_site.py` assembles `dist/` with this
release at the root and under `/v<version>/`, plus every earlier release. A
release is a git tag named `asciidigits-v<version>`, and a tagged version is
always published from its tag.

- **GitHub Pages:** `.github/workflows/pages.yml` builds `dist/` and deploys
  it to https://jumasheff.github.io/ascii-digits/ when a release tag is
  pushed. It stops if the tag doesn't match `__version__`. To retry a failed
  deploy, re-run it from the Actions tab. Set up once, in the repository's
  settings:
  1. Pages: set Source to "GitHub Actions".
  2. Environments > github-pages > Deployment branches and tags: add a tag
     rule `asciidigits-v*`. By default only the default branch may deploy,
     so a tag push would be refused.
- **Any other static host:** run `python tools/build_site.py` and upload
  `dist/`. The page uses relative paths only, so it works under any path
  prefix.

The only external request is Pyodide from jsdelivr, pinned to 314.0.7.
Pyodide checks its packages' SHA-256 itself. To remove the CDN entirely:
1. Copy Pyodide 314.0.7's files, plus its numpy and fonttools wheels, into
   `dist/pyodide/`.
2. Point `PYODIDE_URL` in `web/worker.js` at `new URL("pyodide/", SITE)`.

## Releasing a new version

1. Bump `__version__` in `asciidigits/__init__.py` and `VERSION` in
   `web/version.js`. A test checks they match.
2. Commit, then `git tag asciidigits-v<version>`.
3. Push the commit and the tag. The Pages workflow builds and deploys the site.

## Results

Measured for v1.0.0, with 51 curated styles (16 TTF, 35 FIGlet).

- **Speed (Chromium, once Python has loaded):**
  - the default dataset, 7,000 samples at 16x10: 4.3 s;
  - the largest allowed run, 8,330 samples at 40x24: 49.1 s.
- **Styles per grid preset:**

  | Preset | Cursive | Comic | Display | FIGlet |
  |--------|---------|-------|---------|--------|
  | 8x6    | 0       | 1     | 0       | 5      |
  | 12x8   | 2       | 1     | 1       | 30     |
  | 16x10  | 5       | 5     | 4       | 35     |
  | 24x14  | 5       | 5     | 6       | 2      |

  The held-out split needs at least 3 styles in a family to put that family
  in every split. At the default 16x10, every family reaches every split. At
  8x6 and 12x8 the TTF families are smaller than that, and at 24x14 FIGlet
  is. The page, the CLI and `metadata.json` each note which splits such a
  family reaches.
