import json
import time
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_HTML_PATH = Path("index.html")
REFRESH_RATE_MINUTES = 10
WINDOW_DAYS = 3  # Past 3 days, Next 3 days

# --- THE CLUBHOUSE (STRICT ADMITTANCE) ---
# Only teams in this set get displayed.
# We use partial matches that are unique enough to avoid false positives.

CLUBHOUSE = {
    # --- ARIZONA ---
    "Arizona Cardinals", "Phoenix Suns", "Arizona Diamondbacks", "Arizona State", 
    "Arizona Wildcats", "Phoenix Mercury", "Tucson", "Sun Devils",
    
    # --- CALIFORNIA ---
    "Los Angeles Lakers", "LA Lakers", "Los Angeles Clippers", "LA Clippers",
    "Golden State Warriors", "Sacramento Kings", 
    "Los Angeles Dodgers", "San Francisco Giants", "San Diego Padres", "Los Angeles Angels",
    "Los Angeles Rams", "Los Angeles Chargers", "San Francisco 49ers",
    "USC Trojans", "UCLA Bruins", "California Golden Bears", "Stanford Cardinal",
    "San Jose Sharks", "Anaheim Ducks", "LA Galaxy", "Los Angeles FC",

    # --- TEXAS ---
    "Dallas Cowboys", "Houston Texans", "Dallas Mavericks", "Houston Rockets", "San Antonio Spurs",
    "Texas Rangers", "Houston Astros", "Dallas Stars",
    "Texas Longhorns", "Texas A&M Aggies", "Texas Tech Red Raiders", "Baylor Bears", 
    "TCU Horned Frogs", "SMU Mustangs", "Houston Cougars",

    # --- ILLINOIS ---
    "Chicago Bears", "Chicago Bulls", "Chicago Blackhawks", "Chicago Cubs", "Chicago White Sox",
    "Illinois Fighting Illini", "Northwestern Wildcats",

    # --- GEORGIA ---
    "Atlanta Falcons", "Atlanta Hawks", "Atlanta Braves", "Atlanta United",
    "Georgia Bulldogs", "Georgia Tech Yellow Jackets",

    # --- DMV ---
    "Washington Commanders", "Washington Wizards", "Washington Capitals", "Washington Nationals",
    "Baltimore Ravens", "Baltimore Orioles", "Maryland Terrapins", 
    "Virginia Cavaliers", "Virginia Tech Hokies", "Georgetown Hoyas",

    # --- INTERNATIONAL SOCCER ---
    "Fulham", "Leeds United", "Barcelona", "FC Barcelona",

    # --- INDIAN PREMIER LEAGUE (IPL) ---
    "Chennai Super Kings", "Delhi Capitals", "Gujarat Titans", "Kolkata Knight Riders",
    "Lucknow Super Giants", "Mumbai Indians", "Punjab Kings", "Rajasthan Royals",
    "Royal Challengers", "Sunrisers Hyderabad",

    # --- MAJOR LEAGUE CRICKET (MLC) ---
    "Los Angeles Knight Riders", "MI New York", "San Francisco Unicorns",
    "Seattle Orcas", "Texas Super Kings", "Washington Freedom",

    # --- NATIONAL CRICKET TEAMS ---
    "India Men", "India Women", "United States", "USA Cricket"
}

def is_clubhouse_team(name):
    """
    Returns True if the team is in our Clubhouse.
    Checks if any defined clubhouse string is IN the API name.
    """
    # Special safety check: Ensure "Indiana" (Pacers/Hoosiers) doesn't trigger "India" matches
    if "India" in name and "Indiana" in name:
        return False 
        
    for member in CLUBHOUSE:
        # We check if the unique member string is inside the API name
        if member.lower() in name.lower():
            return True
    return False

# --- ENGINE ROOM ---

def get_az_time(utc_str):
    """Converts ESPN UTC string to Arizona Time (MST, UTC-7)."""
    try:
        # ESPN Time: 2023-11-20T20:00Z
        clean = utc_str.replace("Z", "")
        dt_utc = datetime.fromisoformat(clean)
        dt_az = dt_utc - timedelta(hours=7)
        return dt_az
    except:
        return datetime.now()

def fetch_wire():
    print("  -> Pinging the satellites...")
    
    # The endpoints we care about
    sources = [
        ("basketball", "nba"),
        ("football", "nfl"),
        ("football", "college-football"),
        ("basketball", "mens-college-basketball"),
        ("baseball", "mlb"),
        ("soccer", "eng.1"), # Prem
        ("soccer", "esp.1"), # La Liga
        ("soccer", "eng.2"), # Championship (Leeds)
        ("cricket", "ipl"),  # Specific IPL endpoint
        ("cricket", None)    # Global Cricket (Catches MLC & Internationals)
    ]
    
    dashboard = []
    processed_ids = set() # To prevent duplicates if we hit same game in multiple endpoints

    for sport, league in sources:
        base = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard" if league else f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard"
        
        try:
            data = requests.get(base, timeout=4).json()
        except:
            continue
            
        for e in data.get('events', []):
            if e['id'] in processed_ids: continue

            # 1. Clubhouse Check (The Bouncer)
            try:
                c = e['competitions'][0]
                h_team = c['competitors'][0]['team']['displayName']
                a_team = c['competitors'][1]['team']['displayName']
            except: continue
            
            # If NEITHER team is in the clubhouse, skip it.
            if not is_clubhouse_team(h_team) and not is_clubhouse_team(a_team):
                continue
            
            processed_ids.add(e['id'])

            # 2. Date Check (Window)
            az_dt = get_az_time(e['date'])
            days_diff = (az_dt.date() - datetime.now().date()).days # Compare dates only
            
            if abs(days_diff) > WINDOW_DAYS:
                continue

            # 3. Data Extraction
            status = c['status']['type']['state'] # pre, in, post
            clock = c['status']['type']['detail'] # "Final", "Top 4th", "10:00"
            
            # TV Channel
            broadcast = ""
            if 'broadcasts' in c:
                for b in c['broadcasts']:
                    broadcast = b.get('names', [''])[0]
                    break
            
            # Determine correct league display
            league_disp = (league or sport).upper()
            if "CRICKET" in league_disp and "IPL" not in league_disp:
                # Try to detect MLC or specific leagues from context if needed
                if "Major League" in e.get('name', ''): league_disp = "MLC"

            game = {
                "id": e['id'],
                "sport": league_disp,
                "dt": az_dt,
                "date_str": az_dt.strftime("%a %d"),
                "time_str": az_dt.strftime("%I:%M %p"),
                "status": status,
                "clock": clock,
                "tv": broadcast,
                "home": {
                    "name": h_team,
                    "score": c['competitors'][0].get('score', ''),
                    "logo": c['competitors'][0]['team'].get('logo', '')
                },
                "away": {
                    "name": a_team,
                    "score": c['competitors'][1].get('score', ''),
                    "logo": c['competitors'][1]['team'].get('logo', '')
                }
            }
            dashboard.append(game)
            
    return dashboard

# --- DASHBOARD RENDERER ---

def render_dashboard(games):
    games.sort(key=lambda x: x['dt'])
    
    # Group by Date Headers
    html_rows = ""
    current_date = ""
    
    for g in games:
        # Date Header Logic
        g_date = g['dt'].strftime("%A, %B %d")
        if g_date != current_date:
            html_rows += f"<div class='date-header'>{g_date}</div>"
            current_date = g_date
            
        # Status Styling
        status_class = "future"
        status_dot = "upcoming-dot"
        if g['status'] == 'in': 
            status_class = "live"
            status_dot = "live-dot"
        elif g['status'] == 'post': 
            status_class = "final"
            status_dot = "final-dot"
            
        # Score Logic (Hide scores if game hasn't started)
        h_score = g['home']['score'] if g['status'] != 'pre' else ""
        a_score = g['away']['score'] if g['status'] != 'pre' else ""
        
        # Highlight Logic (Bold the user's team)
        h_class = "my-team" if is_clubhouse_team(g['home']['name']) else "opp-team"
        a_class = "my-team" if is_clubhouse_team(g['away']['name']) else "opp-team"

        html_rows += f"""
        <div class="match-row {status_class}">
            <div class="time-col">
                <div class="time">{g['time_str']}</div>
                <div class="league">{g['sport']}</div>
            </div>
            
            <div class="game-info">
                <div class="team-line">
                    <img src="{g['away']['logo']}" class="logo" onerror="this.style.display='none'">
                    <span class="name {a_class}">{g['away']['name']}</span>
                    <span class="score">{a_score}</span>
                </div>
                <div class="team-line">
                    <img src="{g['home']['logo']}" class="logo" onerror="this.style.display='none'">
                    <span class="name {h_class}">{g['home']['name']}</span>
                    <span class="score">{h_score}</span>
                </div>
            </div>
            
            <div class="status-col">
                <div class="status-indicator">
                    <div class="dot {status_dot}"></div>
                    <span>{g['clock']}</span>
                </div>
                <div class="tv-channel">{g['tv']}</div>
            </div>
        </div>
        """

    if not html_rows:
        html_rows = "<div class='empty-state'>The wires are silent. No games found for your teams.</div>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Clubhouse</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="300">
        <style>
            :root {{
                --bg: #121212; --card: #1e1e1e; --text: #e0e0e0;
                --accent: #bb86fc; --border: #333;
                --live: #cf6679; --green: #03dac6;
            }}
            body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; }}
            
            .header {{ padding: 20px; border-bottom: 1px solid var(--border); background: #1f1f1f; position: sticky; top: 0; z-index: 10; }}
            h1 {{ margin: 0; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 2px; color: var(--accent); }}
            .sub {{ font-size: 0.8rem; color: #777; margin-top: 5px; }}
            
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
            
            .date-header {{ 
                margin: 25px 0 10px 0; 
                font-size: 0.9rem; 
                font-weight: bold; 
                color: #888; 
                text-transform: uppercase; 
                border-bottom: 1px solid var(--border); 
                padding-bottom: 5px;
            }}
            
            .match-row {{ 
                display: flex; 
                align-items: center; 
                background: var(--card); 
                margin-bottom: 12px; 
                padding: 15px; 
                border-radius: 8px; 
                border: 1px solid var(--border);
            }}
            
            .match-row.live {{ border: 1px solid var(--live); box-shadow: 0 0 10px rgba(207, 102, 121, 0.2); }}
            
            .time-col {{ width: 80px; text-align: center; border-right: 1px solid #333; padding-right: 15px; margin-right: 15px; }}
            .time {{ font-weight: bold; font-size: 0.9rem; }}
            .league {{ font-size: 0.6rem; color: #666; margin-top: 4px; overflow: hidden; white-space: nowrap; }}
            
            .game-info {{ flex: 1; }}
            .team-line {{ display: flex; align-items: center; margin: 4px 0; justify-content: space-between; }}
            .logo {{ width: 24px; height: 24px; margin-right: 10px; object-fit: contain; }}
            .name {{ font-size: 1rem; flex: 1; }}
            .name.my-team {{ font-weight: bold; color: #fff; }}
            .name.opp-team {{ color: #aaa; }}
            .score {{ font-weight: bold; font-family: monospace; font-size: 1.1rem; }}
            
            .status-col {{ width: 100px; text-align: right; padding-left: 15px; border-left: 1px solid #333; margin-left: 15px; }}
            .status-indicator {{ display: flex; align-items: center; justify-content: flex-end; font-size: 0.8rem; gap: 6px; }}
            .dot {{ width: 8px; height: 8px; border-radius: 50%; }}
            .live-dot {{ background: var(--live); animation: pulse 1.5s infinite; }}
            .upcoming-dot {{ background: #555; }}
            .final-dot {{ background: #333; }}
            
            .tv-channel {{ font-size: 0.7rem; color: #666; margin-top: 5px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; }}
            
            @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} 100% {{ opacity: 1; }} }}
            
            @media (max-width: 500px) {{
                .match-row {{ flex-wrap: wrap; }}
                .status-col {{ width: 100%; border-left: none; margin-left: 0; margin-top: 10px; padding-top: 10px; border-top: 1px solid #333; text-align: left; display: flex; justify-content: space-between; }}
                .time-col {{ width: 60px; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="container" style="padding:0">
                <h1>Clubhouse Wire</h1>
                <div class="sub">Tempe, AZ • {datetime.now().strftime("%I:%M %p MST")}</div>
            </div>
        </div>
        
        <div class="container">
            {html_rows}
        </div>
    </body>
    </html>
    """
    
    with open(OUTPUT_HTML_PATH, "w", encoding='utf-8') as f: f.write(html)
    print(f"✅ Dashboard Updated: {OUTPUT_HTML_PATH}")

if __name__ == "__main__":
    if os.environ.get('CI') == 'true':
        render_dashboard(fetch_wire())
    else:
        while True:
            render_dashboard(fetch_wire())
            print(f"Sleeping {REFRESH_RATE_MINUTES}m...")
            time.sleep(REFRESH_RATE_MINUTES * 60)
