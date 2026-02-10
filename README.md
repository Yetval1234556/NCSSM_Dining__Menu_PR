# NCSSM Dining Hall Scraper & Dashboard

A Python + Playwright project that scrapes NCSSM dining menus and generates a modern, searchable dashboard.

## Features

- **Reliable scraping** (`scraper.py`)
  - Scrapes the next **10 upcoming days**.
  - Handles days with no menu data.
  - Uses resilient date/meal-period selection logic for the Ten Kites UI.
- **Single-file dashboard output** (`index.html`)
  - Dark mode layout with responsive cards.
  - Meal filters (All / Breakfast / Lunch / Dinner).
  - Client-side search with highlighting.
  - Quick day-jump chips and summary stats.
- **Simple orchestration** (`run_all.py`)
  - Runs scraper, transforms data, builds HTML, and can serve locally.

## How it works

1. `scraper.py` opens the dining site with Playwright and collects menu JSON payloads.
2. The data is written to `menus_dropdown.json`.
3. `run_all.py` transforms that data into grouped day/meal structure.
4. `run_all.py` renders `index.html` (and compatibility `page.html`) with embedded CSS/JS.
5. (Optional) It starts a local web server and opens the page in your browser.

## Prerequisites

- Python 3.10+
- Playwright + Chromium

```bash
pip install playwright
playwright install chromium
# If Chromium launch fails on Linux, run:
playwright install-deps chromium
```

## Usage

### Full pipeline (scrape + render + local serve)

```bash
python run_all.py
```

### Scrape only

```bash
python scraper.py
```

### Render HTML from existing JSON (no server)

```bash
python - <<'PY'
import run_all
run_all.render_html(run_all.transform_data(run_all.load_data()))
PY
```

## Generated files

- `menus_dropdown.json` — raw scraped entries (`date`, `period`, `sections`)
- `index.html` — generated dashboard (primary)
- `page.html` — compatibility alias of the same dashboard

## Project files

- `scraper.py` — Playwright scraper logic
- `run_all.py` — orchestration + HTML generation + local server
- `README.md` — project documentation

## Notes / troubleshooting

- If HTTPS certificate issues appear in some environments, the scraper already creates a browser context with HTTPS errors ignored.
- If push to GitHub fails with `could not read Username`, configure GitHub auth (PAT or SSH) before pushing.
