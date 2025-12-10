"""
AIO Script: Scrapes NCSSM Morganton dining menus and generates a beautiful HTML report.

Steps:
1. Runs scrape_dropdowns_v2.py to fetch latest data to menus_dropdown.json.
2. Reads menus_dropdown.json.
3. specifices a dark-themed, responsive HTML page (page.html) with dropdowns for days/meals.
"""

import json
import sys
import html
from pathlib import Path
import subprocess

# Import the scraper function directly if possible, or run as subprocess
# Running as subprocess is safer to avoid pollution, but importing is cleaner for AIO.
# Let's run as subprocess to ensure clean state for Playwright.
SCRAPER_SCRIPT = "scraper.py"
OUTPUT_JSON = "menus_dropdown.json"
OUTPUT_HTML = "page.html"

def run_scraper():
    print(f"=== Step 1: Running Scraper ({SCRAPER_SCRIPT}) ===")
    try:
        # We use sys.executable to ensure we use the same python environment
        cmd = [sys.executable, SCRAPER_SCRIPT]
        subprocess.run(cmd, check=True)
        print("[OK] Scraper completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Scraper failed with exit code {e.returncode}")
        # We might continue if the JSON exists from a previous run? 
        # But usually we strictly want new data.
        # Let's check if JSON exists
        if not Path(OUTPUT_JSON).exists():
             print("Critical: No menu data file found. Exiting.")
             sys.exit(1)
        print("[WARN] Using existing menu data file despite scraper error.")

def load_data():
    print(f"=== Step 2: Loading Data ({OUTPUT_JSON}) ===")
    path = Path(OUTPUT_JSON)
    if not path.exists():
        print(f"[ERROR] File {OUTPUT_JSON} not found!")
        sys.exit(1)
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"[OK] Loaded {len(data)} entries.")
    return data

def transform_data(flat_data):
    """
    Transform flat list:
    [ {date, period, sections: []}, ... ]
    into:
    [ 
      { 
        "label": "Monday, December 8", 
        "meals": [ 
          { "label": "Breakfast", "sections": [...] }, 
          ... 
        ] 
      }, ...
    ]
    """
    days_map = {} # date_str -> { label: date_str, meals: { period_name: sections } }
    
    # helper to sort periods
    period_order = {"Breakfast": 0, "Lunch": 1, "Dinner": 2}
    
    for entry in flat_data:
        d = entry.get("date")
        p = entry.get("period")
        secs = entry.get("sections", [])
        
        if d not in days_map:
            days_map[d] = {"label": d, "meals_map": {}}
        
        days_map[d]["meals_map"][p] = secs

    # Convert to list and sort? 
    # The scraper collects dates in order, so preserving insertion order is usually enough 
    # if we iterate the map (Python 3.7+ dicts preserve order).
    
    final_days = []
    for d, info in days_map.items():
        meals_list = []
        # Sort meals by fixed order
        sorted_periods = sorted(info["meals_map"].keys(), key=lambda x: period_order.get(x, 99))
        
        for p_name in sorted_periods:
            meals_list.append({
                "label": p_name,
                "sections": info["meals_map"][p_name]
            })
            
        final_days.append({
            "label": info["label"],
            "meals": meals_list
        })
        
    return final_days

def render_html(days):
    print(f"=== Step 3: Generating HTML ({OUTPUT_HTML}) ===")
    
    # Ultra Premium Design: Sharp, High-Contrast, Dashboard Style
    css = """
    :root {
        --bg-body: #09090b; /* Zinc 950 */
        --bg-card: #18181b; /* Zinc 900 */
        --bg-element: #27272a; /* Zinc 800 */
        --border-subtle: #3f3f46; /* Zinc 700 */
        
        --text-main: #fafafa;
        --text-muted: #a1a1aa;
        
        --color-breakfast: #fb923c; /* Orange 400 */
        --color-lunch: #38bdf8; /* Sky 400 */
        --color-dinner: #a78bfa; /* Violet 400 */
        --color-accent: #2dd4bf; /* Teal 400 */
        
        --font-stack: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    * { box-sizing: border-box; }
    
    body {
        font-family: var(--font-stack);
        background-color: var(--bg-body);
        color: var(--text-main);
        margin: 0;
        padding: 0;
        min-height: 100vh;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        background-image: 
            radial-gradient(circle at 50% 0%, rgba(45, 212, 191, 0.05), transparent 40%),
            linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.5) 100%);
    }
    
    .wrap {
        max-width: 960px;
        margin: 0 auto;
        padding: 40px 24px 100px 24px;
    }
    
    /* Header */
    header {
        text-align: center;
        margin-bottom: 48px;
        padding-top: 20px;
    }
    
    .brand-badge {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding: 6px 16px;
        border-radius: 99px;
        background: rgba(45, 212, 191, 0.1);
        color: var(--color-accent);
        margin-bottom: 16px;
        border: 1px solid rgba(45, 212, 191, 0.2);
    }
    
    h1 {
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.03em;
        line-height: 1.1;
        background: linear-gradient(180deg, #fff 0%, #a1a1aa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .subtitle {
        color: var(--text-muted);
        font-size: 1.125rem;
        margin-top: 12px;
        margin-bottom: 32px;
    }
    
    /* Controls Bar */
    .controls-bar {
        position: sticky;
        top: 20px;
        z-index: 100;
        background: rgba(24, 24, 27, 0.85); /* Zinc 900 */
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 12px;
        margin-bottom: 40px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
    }
    
    .filter-group {
        display: flex;
        gap: 8px;
        background: var(--bg-body);
        padding: 4px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    .btn {
        background: transparent;
        border: none;
        color: var(--text-muted);
        padding: 8px 16px;
        border-radius: 8px;
        font-family: inherit;
        font-weight: 600;
        font-size: 0.875rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .btn:hover { color: var(--text-main); }
    
    .btn.active {
        background: var(--bg-element);
        color: var(--text-main);
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    
    /* Branding specific buttons */
    #btn-breakfast.active { background: rgba(251, 146, 60, 0.15); color: var(--color-breakfast); }
    #btn-lunch.active { background: rgba(56, 189, 248, 0.15); color: var(--color-lunch); }
    #btn-dinner.active { background: rgba(167, 139, 250, 0.15); color: var(--color-dinner); }
    
    .search-container {
        position: relative;
        flex-grow: 1;
        max-width: 300px;
    }
    
    .search-input {
        width: 100%;
        background: var(--bg-body);
        border: 1px solid var(--border-subtle);
        color: var(--text-main);
        padding: 10px 16px 10px 36px;
        border-radius: 10px;
        font-family: inherit;
        font-size: 0.9rem;
        transition: border-color 0.2s;
    }
    
    .search-input:focus {
        outline: none;
        border-color: var(--text-muted);
    }
    
    .search-icon {
        position: absolute;
        left: 12px;
        top: 50%;
        transform: translateY(-50%);
        width: 16px;
        height: 16px;
        fill: var(--text-muted);
        pointer-events: none;
    }
    
    /* Content Layout */
    .day-card {
        margin-bottom: 48px;
        animation: fadeIn 0.6s ease-out;
    }
    
    .day-header {
        display: flex;
        align-items: baseline;
        gap: 16px;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--border-subtle);
    }
    
    .day-header h2 {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        color: var(--text-main);
    }
    
    .day-date {
        font-size: 1rem;
        font-weight: 500;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .meals-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 20px;
    }
    
    .meal-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        overflow: hidden;
        transition: transform 0.2s, box-shadow 0.2s;
        display: flex;
        flex-direction: column;
    }
    
    .meal-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 20px -8px rgba(0, 0, 0, 0.3);
        border-color: rgba(255,255,255,0.1);
    }
    
    .meal-header {
        padding: 20px;
        border-bottom: 1px solid rgba(255,255,255,0.03);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .meal-title {
        font-size: 1.1rem;
        font-weight: 700;
    }
    
    /* Meal Badges */
    .badge {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        padding: 4px 10px;
        border-radius: 6px;
        letter-spacing: 0.05em;
    }
    .badge-breakfast { background: rgba(251, 146, 60, 0.1); color: var(--color-breakfast); box-shadow: 0 0 0 1px rgba(251, 146, 60, 0.2); }
    .badge-lunch { background: rgba(56, 189, 248, 0.1); color: var(--color-lunch); box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.2); }
    .badge-dinner { background: rgba(167, 139, 250, 0.1); color: var(--color-dinner); box-shadow: 0 0 0 1px rgba(167, 139, 250, 0.2); }
    
    .meal-body {
        padding: 20px;
        flex-grow: 1;
    }
    
    .section { margin-bottom: 24px; }
    .section:last-child { margin-bottom: 0; }
    
    .section-name {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-muted);
        margin-bottom: 12px;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .section-name::after {
        content: '';
        flex-grow: 1;
        height: 1px;
        background: var(--border-subtle);
    }
    
    .item-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .menu-item {
        font-size: 0.95rem;
        font-weight: 500;
        color: #e4e4e7; /* Zinc 200 */
        padding: 6px 10px;
        margin: 0 -10px;
        border-radius: 8px;
        transition: background 0.15s;
    }
    
    .menu-item:hover {
        background: rgba(255,255,255,0.05);
        color: #fff;
    }
    
    .item-match {
        background: rgba(45, 212, 191, 0.15) !important;
        color: var(--color-accent) !important;
    }

    .empty-state {
        color: var(--text-muted);
        font-style: italic;
        text-align: center;
        padding: 20px 0;
        font-size: 0.9rem;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @media (max-width: 600px) {
        h1 { font-size: 2.5rem; }
        .controls-bar { top: 10px; flex-direction: column; align-items: stretch; }
        .search-container { max-width: none; }
    }
    """
    
    js = """
    function filterMeals(type) {
        document.querySelectorAll('.btn.filter').forEach(b => b.classList.remove('active'));
        const btn = document.getElementById('btn-' + type) || document.getElementById('btn-all');
        btn.classList.add('active');
        
        const meals = document.querySelectorAll('.meal-card');
        meals.forEach(m => {
            const mType = m.getAttribute('data-type');
            if(type === 'all' || mType === type) {
                m.style.display = '';
            } else {
                m.style.display = 'none';
            }
        });
    }
    
    function searchItems(query) {
        query = query.toLowerCase();
        const items = document.querySelectorAll('.menu-item');
        
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if(query && text.includes(query)) {
                item.classList.add('item-match');
            } else {
                item.classList.remove('item-match');
            }
        });
        
        // Hide meals with no matches if searching? 
        // Or just highlight? Let's hide sections that don't match if query is long enough
        if(query.length < 2) {
            document.querySelectorAll('.day-card, .meal-card, .section').forEach(el => el.style.display = '');
            return;
        }
        
        // Hierarchical hiding could be complex, for now simplest is highlight.
        // But the user asked for INTERACTIVE.
        // Let's filter meal cards. If a meal card has NO matches, dim it?
        
        const mealCards = document.querySelectorAll('.meal-card');
        mealCards.forEach(card => {
            const hasMatch = card.querySelector('.item-match');
            if(hasMatch) {
                card.style.opacity = '1';
                card.style.borderColor = 'var(--color-accent)';
            } else {
                card.style.opacity = '0.3';
                card.style.borderColor = '';
            }
        });
    }
    """

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        "<title>NCSSM Dining</title>",
        f"<style>{css}</style>",
        "</head>",
        "<body>",
        "<div class='wrap'>",
        "<header>",
        "<span class='brand-badge'>Live Menu Data</span>",
        "<h1>On The Menu</h1>",
        "<div class='subtitle'>Fresh, nutritious meals for the NCSSM community.</div>",
        "</header>",
        
        "<div class='controls-bar'>",
        "<div class='filter-group'>",
        "<button id='btn-all' class='btn filter active' onclick=\"filterMeals('all')\">All</button>",
        "<button id='btn-breakfast' class='btn filter' onclick=\"filterMeals('breakfast')\">Breakfast</button>",
        "<button id='btn-lunch' class='btn filter' onclick=\"filterMeals('lunch')\">Lunch</button>",
        "<button id='btn-dinner' class='btn filter' onclick=\"filterMeals('dinner')\">Dinner</button>",
        "</div>",
        "<div class='search-container'>",
        "<svg class='search-icon' viewBox='0 0 24 24'><path d='M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' stroke='currentColor' stroke-width='2' fill='none'/></svg>",
        "<input type='text' class='search-input' placeholder='Find food (e.g. Pizza)...' oninput='searchItems(this.value)'>",
        "</div>",
        "</div>",
        
        "<div class='main-content'>"
    ]

    for i, day in enumerate(days):
        # Split label
        label_parts = day['label'].split(',')
        day_name = label_parts[0]
        date_val = label_parts[1] if len(label_parts) > 1 else ""
        
        html_parts.append(f"<div class='day-card'>")
        html_parts.append(f"<div class='day-header'><h2>{day_name}</h2><div class='day-date'>{date_val}</div></div>")
        
        if not day['meals']:
             html_parts.append("<div class='empty-state'>No meals scheduled.</div>")
        else:
            html_parts.append("<div class='meals-grid'>")
            for meal in day['meals']:
                m_label = meal['label']
                m_type = m_label.lower().split()[0] # breakfast, lunch, dinner
                if m_type not in ['breakfast', 'lunch', 'dinner']: m_type = 'lunch' # fallback
                
                html_parts.append(f"<div class='meal-card' data-type='{m_type}'>")
                html_parts.append(f"<div class='meal-header'>")
                html_parts.append(f"<div class='meal-title'>{html.escape(m_label)}</div>")
                html_parts.append(f"<span class='badge badge-{m_type}'>{m_type}</span>")
                html_parts.append(f"</div>")
                
                html_parts.append("<div class='meal-body'>")
                
                if not meal['sections']:
                    html_parts.append("<div class='empty-state'>Menu not posting.</div>")
                else:
                    for section in meal['sections']:
                        html_parts.append("<div class='section'>")
                        html_parts.append(f"<div class='section-name'>{html.escape(section.get('title', 'General'))}</div>")
                        html_parts.append("<div class='item-list'>")
                        for item_name in section.get('items', []):
                             html_parts.append(f"<div class='menu-item'>{html.escape(item_name)}</div>")
                        html_parts.append("</div></div>")
                
                html_parts.append("</div>") # end meal-body
                html_parts.append("</div>") # end meal-card
            html_parts.append("</div>") # end meals-grid

        html_parts.append("</div>") # end day-card

    html_parts.append("</div>") # end main-content
    html_parts.append(f"<script>{js}</script>")
    html_parts.append("</div></body></html>")
    
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write("".join(html_parts))
    print(f"[OK] HTML generated at: {Path(OUTPUT_HTML).absolute()}")

def serve_locally():
    import http.server
    import socketserver
    import webbrowser

    PORT = 8000
    Handler = http.server.SimpleHTTPRequestHandler
    
    # Try to find a free port
    while True:
        try:
            with socketserver.TCPServer(("", PORT), Handler) as httpd:
                url = f"http://localhost:{PORT}/{OUTPUT_HTML}"
                print(f"\n=== Step 4: Starting Local Server ===")
                print(f"Serving at {url}")
                print("Press Ctrl+C to stop the server.")
                
                webbrowser.open(url)
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\nServer stopped.")
                break
        except OSError as e:
            if e.errno == 10048:
                print(f"Port {PORT} is busy, trying {PORT+1}...")
                PORT += 1
            else:
                raise

def main():
    run_scraper()
    data = load_data()
    days = transform_data(data)
    render_html(days)
    serve_locally()

if __name__ == "__main__":
    main()
