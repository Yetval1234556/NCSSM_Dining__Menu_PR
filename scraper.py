"""
Playwright scraper that explicitly interacts with the Date and Period dropdowns
on https://menus.campus-dining.com/eliorna/d1031 to collect the first 10 dates
and all three meal periods (Breakfast, Lunch, Dinner). Results are written to
menus_dropdown.json with structure:
[
  {
    "date": "Monday, December 8",
    "period": "Breakfast",
    "sections": [
      {"title": "Station Name", "items": ["Item 1", "Item 2"]}
    ]
  },
  ...
]
"""

import json
import time
from typing import List, Dict

from playwright.sync_api import sync_playwright, Page, Frame


URL = "https://menus.campus-dining.com/eliorna/d1031"
PERIODS = ["Breakfast", "Lunch", "Dinner"]
MAX_DATES = 10


def build_sections(items: List[Dict]) -> List[Dict]:
    """Convert Ten Kites items list into ordered sections with recipe names."""
    sections = []
    lookup = {}
    for item in items:
        item_type = item.get("itemType", "")
        if item_type.startswith("section"):
            section = {
                "id": item.get("sectionGuid"),
                "title": item.get("sectionName", "Section"),
                "items": [],
            }
            sections.append(section)
            lookup[section["id"]] = section
        elif item_type == "recipe":
            sec_id = item.get("sectionGuid")
            section = lookup.get(sec_id)
            if not section:
                section = {"id": sec_id, "title": "Section", "items": []}
                lookup[sec_id] = section
                sections.append(section)
            section["items"].append(item.get("recipeName", "Untitled"))
    return [{"title": s["title"], "items": s["items"]} for s in sections]


def wait_for_date(page: Page, expected_text: str):
    print(f"Waiting for date to become: {expected_text}")
    try:
        page.wait_for_function(
            "(expected) => document.querySelector('.k10-menu-date-selector__name')?.textContent?.trim() === expected",
            arg=expected_text,
            timeout=5000
        )
    except Exception as e:
        print(f"Time out waiting for date text update. Current: {page.eval_on_selector('.k10-menu-date-selector__name', 'e => e.textContent')} Error: {e}")


def wait_for_period(page: Page, expected_text: str):
    page.wait_for_function(
        "(expected) => document.querySelector('.k10-menu-selector__name')?.textContent?.trim() === expected",
        arg=expected_text,
    )


def select_date(page: Page, date_text: str):
    print(f"Selecting date: {date_text}")
    date_panel = page.locator(".k10-menu-date-selector__panel").first
    for attempt in range(2):
        print(f"  Attempt {attempt+1} to open date panel...")
        date_panel.click()
        # Wait for options
        try:
            page.wait_for_selector(".k10-menu-date-selector__week-day", state="attached", timeout=3000)
        except:
            print("  Date options not found, retrying click...")
            continue
            
        print(f"  Clicking date option: {date_text}")
        found = page.evaluate(
            """(targetText) => {
                const el = Array.from(document.querySelectorAll('.k10-menu-date-selector__week-day'))
                  .find(o => o.textContent.trim() === targetText);
                if (el) {
                    el.dispatchEvent(new MouseEvent('click', {bubbles:true}));
                    return true;
                }
                return false;
            }""",
            date_text,
        )
        if not found:
            print(f"  Date option '{date_text}' NOT found in DOM!")
        
        try:
            wait_for_date(page, date_text)
            return
        except Exception:
            if attempt == 1:
                print("Failed to select date after retries.")
                raise
            # retry once if the click didn't stick


def select_period_and_get_json(page: Page, period_text: str) -> str:
    print(f"Selecting period: {period_text}")
    
    # Target the VISIBLE panel
    # We use a locator that filters for visibility
    period_panel_locator = page.locator(".k10-menu-selector__panel >> visible=true")
    
    count = period_panel_locator.count()
    print(f"  Found {count} visible period panels.")
    
    if count == 0:
        # Debug: list all panels
        total = page.locator(".k10-menu-selector__panel").count()
        print(f"  No visible panels found! Total panels: {total}")
        # Try finding the one with the current text
        # But if none are visible, we might need to wait
        try:
             page.wait_for_selector(".k10-menu-selector__panel", state="visible", timeout=5000)
             period_panel_locator = page.locator(".k10-menu-selector__panel >> visible=true")
        except:
             print("  Wait for visible panel failed.")

    previous_json = page.eval_on_selector("[data-menu-json]", "el => el.getAttribute('data-menu-json')") or ""
    
    for attempt in range(3):
        print(f"  Attempt {attempt+1}...")
        
        try:
            print("  Clicking visible period panel (via JS)...")
            # standard click might be failing to trigger listener, use JS
            period_panel_locator.first.evaluate("el => el.click()")
            # verification click
            # period_panel_locator.first.click(force=True)
        except Exception as e:
            print(f"  Clicking panel failed: {e}")

        # Wait for options to exist
        print(f"  Pre-wait check: {page.locator('.k10-menu-selector__option').count()} options in DOM.")
        try:
            # We also want the options container to be visible potentially
            page.wait_for_selector(".k10-menu-selector__option", state="attached", timeout=5000)
            print("  Options found in DOM.")
        except Exception:
            print("  Options NOT found, retrying loop...")
            # Capture debug artifacts
            timestamp = int(time.time())
            page.screenshot(path=f"debug_screenshot_{attempt}_{timestamp}.png")
            with open(f"debug_html_{attempt}_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print(f"  Saved debug screenshot and HTML for attempt {attempt+1}")
            
            time.sleep(1)

        print(f"  Clicking period option: {period_text}")
        found = page.evaluate(
            """(targetText) => {
                const el = Array.from(document.querySelectorAll('.k10-menu-selector__option'))
                  .find(o => o.textContent.trim() === targetText);
                if (el) {
                    el.dispatchEvent(new MouseEvent('click', {bubbles:true}));
                    return true;
                }
                return false;
            }""",
            period_text,
        )
        
        if not found:
            print(f"  Period option '{period_text}' NOT found in DOM list!")
            all_opts = page.eval_on_selector_all(".k10-menu-selector__option", "els => els.map(e => e.textContent.trim())")
            print(f"  Available options: {all_opts}")
            # If we missed the window or it closed, loop again
            continue

        try:
            print("  Waiting for update...")
            page.wait_for_function(
                """
                (args) => {
                    const targetText = args[0];
                    const oldJson = args[1];
                    const name = document.querySelector('.k10-menu-selector__name')?.textContent?.trim();
                    const el = document.querySelector('[data-menu-json]');
                    if (!el) return false;
                    const cur = el.getAttribute('data-menu-json') || '';
                    const nameReady = name === targetText;
                    
                    // Special case: if we want what we already have, we just ensure names match
                    // But usually we want diff data.
                    if (nameReady && cur) return true;
                    
                    return false; 
                }
                """,
                arg=[period_text, previous_json],
                timeout=5000,
            )
            print("  Update detected!")
            time.sleep(0.5) # stability
            return page.eval_on_selector("[data-menu-json]", "el => el.getAttribute('data-menu-json')")
        except Exception as e:
            print(f"  Wait for update failed: {e}")
            # Check if it actually worked
            curr_name = page.eval_on_selector(".k10-menu-selector__name", "e => e.textContent.trim()")
            if curr_name == period_text:
                print("  Name matches target, assuming success despite timeout.")
                return page.eval_on_selector("[data-menu-json]", "el => el.getAttribute('data-menu-json')")
            
            if attempt == 2:
                # If we are stuck on Breakfast and wanted Breakfast, maybe it's fine?
                if current_label == period_text:
                     print("  Already on target period.")
                     return page.eval_on_selector("[data-menu-json]", "el => el.getAttribute('data-menu-json')")
                raise


def collect_date_options(page: Page) -> List[str]:
    print("Collecting date options...")
    date_panel = page.locator(".k10-menu-date-selector__panel").first
    date_panel.click()
    page.wait_for_selector(".k10-menu-date-selector__week-day", state="attached")
    
    # Get all options primarily, then filter
    options = page.locator(".k10-menu-date-selector__week-day")
    count = options.count()
    all_dates = []
    for i in range(count):
        txt = options.nth(i).inner_text().strip()
        all_dates.append(txt)
    
    print(f"  Found raw dates: {all_dates}")
    
    # close dropdown
    date_panel.click()
    
    # Filter for >= today
    # Date format example: "Monday, December 1"
    # We need to handle year wrapping if necessary, but usually menus are near-term.
    # We'll use current year.
    from datetime import datetime
    
    today = datetime.now().date()
    valid_dates = []
    
    for d_str in all_dates:
        # Parse "Monday, December 1"
        # We can split by ',' then parse " December 1"
        try:
            parts = d_str.split(',')
            if len(parts) < 2:
                continue
            month_day = parts[1].strip() # "December 1"
            
            # Parse with current year
            dt_obj = datetime.strptime(f"{month_day} {today.year}", "%B %d %Y").date()
            
            # Heuristic for year wrap: if today is Dec and date is Jan, add 1 year
            if today.month == 12 and dt_obj.month == 1:
                dt_obj = dt_obj.replace(year=today.year + 1)
            # If today is Jan and date is Dec, subtract 1 year (unlikely for "future" menus but good for safety)
            elif today.month == 1 and dt_obj.month == 12:
                dt_obj = dt_obj.replace(year=today.year - 1)
                
            if dt_obj >= today:
                valid_dates.append(d_str)
        except Exception as e:
            print(f"  Error parsing date '{d_str}': {e}")
            
    # Take up to MAX_DATES
    final_dates = valid_dates[:MAX_DATES]
    print(f"  Filtered to {len(final_dates)} future/today dates: {final_dates}")
    return final_dates


def scrape():
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(45000)
        print(f"Navigating to {URL}...")
        page.goto(URL, wait_until="networkidle")

        print("Waiting for initial selectors...")
        page.wait_for_selector(".k10-menu-date-selector__panel", state="attached")
        page.wait_for_selector(".k10-menu-selector__panel", state="attached")
        page.wait_for_selector("[data-menu-json]", state="attached")

        dates = collect_date_options(page)
        results = []

        for date_text in dates:
            print(f"--- Processing {date_text} ---")
            try:
                select_date(page, date_text)
            except Exception as e:
                print(f"Failed to select date {date_text}: {e}")
                continue
            
            # Check if periods are available
            time.sleep(1) # wait for potential reload
            
            # Check for "No menu currently available" message
            # There might be multiple elements, check if any is visible
            not_available = page.locator(".k10-course_not_available")
            is_empty = False
            for i in range(not_available.count()):
                if not_available.nth(i).is_visible():
                    is_empty = True
                    break
            
            if is_empty:
                print(f"No menu available for {date_text}, skipping.")
                continue

            # Check if period options exist (even if hidden)
            # We need to click the panel to populate them potentially?
            # Or usually they are in DOM if available.
            # But from debug HTML, the options container was empty.
            # Let's try to check the container content
            options_count = page.locator(".k10-menu-selector__option").count()
            if options_count == 0:
                print(f"No period options found for {date_text} (likely no menu), skipping.")
                continue

            for period in PERIODS:
                try:
                    menu_json = select_period_and_get_json(page, period)
                    if not menu_json:
                        print(f"Got empty JSON for {period}, skipping.")
                        continue
                    payload = json.loads(menu_json)
                    sections = build_sections(payload.get("items", []))
                    results.append(
                        {
                            "date": date_text,
                            "period": period,
                            "sections": sections,
                        }
                    )
                except Exception as e:
                    print(f"Failed to scrape {period} for {date_text}: {e}")

        browser.close()

    with open("menus_dropdown.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(results)} menu entries to menus_dropdown.json")


if __name__ == "__main__":
    scrape()
