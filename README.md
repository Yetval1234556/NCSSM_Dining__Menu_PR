# NCSSM Dining Hall Scraper & Dashboard

A modern, full-stack solution to scrape and visualize dining hall menus from the NCSSM website.

## Features

- **Robust Scraping**: `scraper.py` uses Playwright to intelligently navigate the Ten Kites menu interface, handling date selection and dynamic loading automatically. It specifically targets the *next 10 days* starting from today.
- **Resilient**: Automatically handles empty days, "no menu available" states, and network timeouts.
- **Ultra Premium Dashboard**: Generates a high-performance, dark-mode HTML dashboard (`page.html`) with:
  - **Crisp Typography**: Inter font family with strict antialiasing.
  - **Search**: Instant client-side search for menu items.
  - **Filtering**: Toggle between Breakfast, Lunch, and Dinner.
  - **Auto-Hosting**: Automatically finds an open port and serves the dashboard locally.

## Logic Overview

1.  **Scrape**: The script launches a headless browser, goes to the menu URL, and collects data for upcoming days.
2.  **Process**: It filters out past dates to ensure relevance.
3.  **Generate**: It constructs a single-file HTML application with embedded CSS and JS.
4.  **Serve**: It starts a local HTTP server and opens your browser.

## usage

### Prerequisites

- Python 3.8+
- Playwright

```bash
pip install playwright
playwright install chromium
```

### Run

Simply execute the AIO script:

```bash
python run_all.py
```

This will scrape the data and open the dashboard in your default browser.

## File Structure

- `run_all.py`: Main entry point. Handles orchestration, HTML generation, and local serving.
- `scraper.py`: The core scraping logic (Playwright).
- `menus_dropdown.json`: (Generated) The raw data output.
- `page.html`: (Generated) The dashboard file.
