"""Scrape NCSSM dining menus into menus_dropdown.json.

This version keeps interactions simple and resilient:
- opens date dropdown and iterates upcoming dates
- opens period dropdown for each date and scrapes available periods
- waits for menu payload changes before parsing
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from html import unescape
from urllib.request import urlopen
from datetime import datetime
from typing import Dict, List

try:
    from playwright.sync_api import Page, TimeoutError, sync_playwright
except ModuleNotFoundError:
    Page = object  # type: ignore[assignment]

    class TimeoutError(Exception):
        """Fallback timeout type when Playwright is unavailable."""

    sync_playwright = None

URL = "https://menus.campus-dining.com/eliorna/d1031"
OUTPUT_JSON = "menus_dropdown.json"
MAX_DATES = 10
PERIOD_ORDER = {"Breakfast": 0, "Lunch": 1, "Dinner": 2}


def try_install_playwright_stack() -> bool:
    """Best-effort install of Playwright package, browser binary and OS deps."""
    commands = [
        [sys.executable, "-m", "pip", "install", "playwright"],
        # Ensure the browser binary exists for the active Playwright version.
        [sys.executable, "-m", "playwright", "install", "chromium"],
        # Ensure Linux shared-library deps exist when needed.
        [sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"],
    ]
    for command in commands:
        try:
            print(f"Bootstrapping dependency: {' '.join(command)}")
            subprocess.run(command, check=True)
        except Exception as exc:
            print(f"Dependency bootstrap failed: {exc}")
            return False
    return True


def build_sections(items: List[Dict]) -> List[Dict]:
    """Group recipe rows under their section names."""
    sections: List[Dict] = []
    by_id: Dict[str, Dict] = {}

    for item in items:
        item_type = item.get("itemType", "")
        if item_type.startswith("section"):
            section = {
                "id": item.get("sectionGuid"),
                "title": item.get("sectionName", "Section"),
                "items": [],
            }
            sections.append(section)
            by_id[section["id"]] = section
        elif item_type == "recipe":
            section_id = item.get("sectionGuid")
            section = by_id.get(section_id)
            if section is None:
                section = {"id": section_id, "title": "Section", "items": []}
                by_id[section_id] = section
                sections.append(section)
            section["items"].append(item.get("recipeName", "Untitled"))

    return [{"title": section["title"], "items": section["items"]} for section in sections]


def get_menu_json(page: Page) -> str:
    return page.get_attribute("[data-menu-json]", "data-menu-json") or ""


def wait_menu_ready(page: Page, previous_json: str, expected_period: str | None = None) -> None:
    """Wait until menu JSON exists and (preferably) has changed."""

    def ready() -> bool:
        current_json = get_menu_json(page)
        if not current_json:
            return False

        period_name = (page.text_content(".k10-menu-selector__name") or "").strip()
        period_ok = expected_period is None or period_name == expected_period

        if expected_period is None:
            return current_json != previous_json
        return period_ok and current_json != previous_json

    deadline = time.time() + 8
    while time.time() < deadline:
        if ready():
            return
        time.sleep(0.2)

    raise TimeoutError("Menu payload did not update in time")


def collect_date_options(page: Page) -> List[str]:
    """Return up to MAX_DATES valid date labels from the dropdown."""
    date_panel = page.locator(".k10-menu-date-selector__panel").first
    date_panel.click()
    page.wait_for_selector(".k10-menu-date-selector__week-day", state="attached", timeout=6000)

    all_labels = [
        page.locator(".k10-menu-date-selector__week-day").nth(i).inner_text().strip()
        for i in range(page.locator(".k10-menu-date-selector__week-day").count())
    ]

    # close dropdown after collecting labels
    date_panel.click()

    today = datetime.now().date()
    valid: List[str] = []
    for label in all_labels:
        try:
            parts = label.split(",")
            if len(parts) < 2:
                continue
            month_day = parts[1].strip()
            candidate = datetime.strptime(f"{month_day} {today.year}", "%B %d %Y").date()

            # year-wrap guardrails
            if today.month == 12 and candidate.month == 1:
                candidate = candidate.replace(year=today.year + 1)
            elif today.month == 1 and candidate.month == 12:
                candidate = candidate.replace(year=today.year - 1)

            if candidate >= today:
                valid.append(label)
        except ValueError:
            continue

    return valid[:MAX_DATES]


def select_date(page: Page, date_label: str) -> bool:
    """Select a date option. Returns False if unavailable."""
    date_panel = page.locator(".k10-menu-date-selector__panel").first
    previous_json = get_menu_json(page)

    for _ in range(2):
        date_panel.click()
        options = page.locator(".k10-menu-date-selector__week-day")
        try:
            page.wait_for_selector(".k10-menu-date-selector__week-day", state="attached", timeout=4000)
        except TimeoutError:
            continue

        found = page.evaluate(
            """(label) => {
                const option = Array.from(document.querySelectorAll('.k10-menu-date-selector__week-day'))
                  .find((el) => el.textContent.trim() === label);
                if (!option) return false;
                option.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                return true;
            }""",
            date_label,
        )
        if not found:
            date_panel.click()
            continue

        try:
            page.wait_for_function(
                "(expected) => document.querySelector('.k10-menu-date-selector__name')?.textContent?.trim() === expected",
                arg=date_label,
                timeout=5000,
            )
            wait_menu_ready(page, previous_json)
            return True
        except TimeoutError:
            continue

    return False


def available_periods(page: Page) -> List[str]:
    """Read currently available period options from dropdown."""
    panel = page.locator(".k10-menu-selector__panel").first
    panel.click()
    page.wait_for_selector(".k10-menu-selector__option", state="attached", timeout=5000)

    options = [
        page.locator(".k10-menu-selector__option").nth(i).inner_text().strip()
        for i in range(page.locator(".k10-menu-selector__option").count())
    ]

    # close to avoid overlay issues
    panel.click()

    return sorted(set(options), key=lambda p: PERIOD_ORDER.get(p, 99))


def select_period(page: Page, period_label: str) -> bool:
    panel = page.locator(".k10-menu-selector__panel").first
    previous_json = get_menu_json(page)

    for _ in range(2):
        panel.click()
        try:
            page.wait_for_selector(".k10-menu-selector__option", state="attached", timeout=4000)
        except TimeoutError:
            continue

        found = page.evaluate(
            """(label) => {
                const option = Array.from(document.querySelectorAll('.k10-menu-selector__option'))
                  .find((el) => el.textContent.trim() === label);
                if (!option) return false;
                option.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                return true;
            }""",
            period_label,
        )
        if not found:
            panel.click()
            return False

        try:
            wait_menu_ready(page, previous_json, expected_period=period_label)
            return True
        except TimeoutError:
            continue

    return False


def has_no_menu_message(page: Page) -> bool:
    locator = page.locator(".k10-course_not_available")
    for i in range(locator.count()):
        if locator.nth(i).is_visible():
            return True
    return False


def scrape(attempted_bootstrap: bool = False) -> None:
    global sync_playwright, Page, TimeoutError
    results: List[Dict] = []

    try:
        if sync_playwright is None:
            raise ModuleNotFoundError("playwright is not installed")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            page.set_default_timeout(45000)

            print(f"Navigating to {URL}...")
            page.goto(URL, wait_until="domcontentloaded")
            page.wait_for_selector(".k10-menu-date-selector__panel", state="attached")
            page.wait_for_selector(".k10-menu-selector__panel", state="attached")
            page.wait_for_selector("[data-menu-json]", state="attached")

            dates = collect_date_options(page)
            print(f"Found {len(dates)} upcoming dates")

            for date_label in dates:
                print(f"Processing {date_label}")
                if not select_date(page, date_label):
                    print(f"  - Failed selecting date {date_label}")
                    continue

                if has_no_menu_message(page):
                    print("  - No menu available")
                    continue

                try:
                    periods = available_periods(page)
                except TimeoutError:
                    print("  - No periods found")
                    continue

                for period in periods:
                    if not select_period(page, period):
                        print(f"  - Failed selecting period {period}")
                        continue

                    payload_raw = get_menu_json(page)
                    if not payload_raw:
                        continue

                    try:
                        payload = json.loads(payload_raw)
                    except json.JSONDecodeError:
                        print(f"  - Invalid JSON payload for {period}")
                        continue

                    results.append(
                        {
                            "date": date_label,
                            "period": period,
                            "sections": build_sections(payload.get("items", [])),
                        }
                    )

            context.close()
            browser.close()
    except Exception as exc:
        missing_runtime = (
            "playwright is not installed" in str(exc)
            or "error while loading shared libraries" in str(exc)
            or "Executable doesn't exist" in str(exc)
            or "Executable doesn’t exist" in str(exc)
        )
        if missing_runtime and not attempted_bootstrap:
            print("Playwright runtime unavailable. Attempting automatic dependency bootstrap...")
            if try_install_playwright_stack():
                if sync_playwright is None:
                    from playwright.sync_api import Page, TimeoutError, sync_playwright
                return scrape(attempted_bootstrap=True)

        print(f"Playwright run failed ({exc}). Falling back to static HTML scrape for current menu.")

        html = urlopen(URL, timeout=25).read().decode("utf-8", "ignore")
        date_match = re.search(r'k10-menu-date-selector__name">\s*([^<]+)', html)
        period_match = re.search(r'k10-menu-selector__name">\s*([^<]+)', html)
        payload_match = re.search(r'data-menu-json="([^"]+)"', html)

        if date_match and period_match and payload_match:
            payload = json.loads(unescape(payload_match.group(1)))
            results.append(
                {
                    "date": date_match.group(1).strip(),
                    "period": period_match.group(1).strip(),
                    "sections": build_sections(payload.get("items", [])),
                }
            )

            print(
                "Fallback collected current menu only. "
                "For full multi-date scraping, ensure Playwright and Chromium dependencies are installed."
            )
        else:
            raise RuntimeError("Fallback scrape failed: could not parse menu HTML") from exc

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    print(f"Wrote {len(results)} entries to {OUTPUT_JSON}")


if __name__ == "__main__":
    scrape()
