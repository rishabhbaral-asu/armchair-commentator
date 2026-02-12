import json
import time
import os
import requests
import calendar
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_HTML_PATH = Path("index.html")
REFRESH_RATE_MINUTES = 15
WINDOW_DAYS = 3  # Look 3 days back/forward

# --- STRICT ALLOWLIST (The "Bouncer") ---
# We match strictly on distinct team names/mascots to avoid "North Texas" or "California Baptist" junk.
# Format: "Keyword": "Region Label"

STRICT_TEAMS = {
    # ARIZONA (Complete)
    "Arizona Cardinals": "AZ", "Phoenix Suns": "AZ", "Arizona Diamondbacks": "AZ", 
    "Arizona Coyotes": "AZ", "Phoenix Mercury": "AZ", "Arizona State": "AZ", 
    "Sun Devils": "AZ", "Arizona Wildcats": "AZ", "Tucson": "AZ",

    # CALIFORNIA (Major Only)
    "Los Angeles Lakers": "CA", "LA Lakers": "CA", "L.A. Lakers": "CA",
    "Los Angeles Clippers": "CA", "LA Clippers": "CA", "L.A. Clippers": "CA",
    "Golden State Warriors": "CA", "Sacramento Kings": "CA",
    "Los Angeles Dodgers": "CA", "San Francisco Giants": "CA", "San Diego Padres": "CA", 
    "Los Angeles Angels": "CA", "Oakland Athletics": "CA",
    "Los Angeles Rams": "CA", "Los Angeles Chargers": "CA", "San Francisco 49ers": "CA",
    "USC Trojans": "CA", "UCLA Bruins": "CA", "California Golden Bears": "CA", "Cal Bears": "CA", 
    "Stanford Cardinal": "CA", "San Jose Sharks": "CA", "Anaheim Ducks": "CA",
    "LA Galaxy": "CA", "Los Angeles FC": "CA", "San Jose Earthquakes": "CA",

    # TEXAS (The "Big" Teams Only)
    "Dallas Cowboys": "TX", "Houston Texans": "TX",
    "Dallas Mavericks": "TX", "Houston Rockets": "TX", "San Antonio Spurs": "TX",
    "Texas Rangers": "TX", "Houston Astros": "TX",
    "Dallas Stars": "TX",
    "Texas Longhorns": "TX", "Texas A&M Aggies": "TX", "Texas Tech Red Raiders": "TX", 
    "Baylor Bears": "TX", "TCU Horned Frogs": "TX", "SMU Mustangs": "TX", "Houston Cougars": "TX",

    # ILLINOIS
    "Chicago Bears": "IL", "Chicago Bulls": "IL", "Chicago Blackhawks": "IL", 
    "Chicago Cubs": "IL", "Chicago White Sox": "IL", "Illinois Fighting Illini": "IL", 
    "Northwestern Wildcats": "IL",

    # GEORGIA
    "Atlanta Falcons": "GA", "Atlanta Hawks": "GA", "Atlanta Braves": "GA", 
    "Atlanta United": "GA", "Georgia Bulldogs": "GA", "Georgia Tech Yellow Jackets": "GA",

    # DMV (DC/MD/VA)
    "Washington Commanders": "DC", "Washington Wizards": "DC", "Washington Capitals": "DC", 
    "Washington Nationals": "DC", "Baltimore Ravens": "MD", "Baltimore Orioles": "MD",
    "Maryland Terrapins": "MD", "Virginia Cavaliers": "VA", "Virginia Tech Hokies": "VA", 
    "Georgetown Hoyas": "DC",

    # INTERNATIONAL / SPECIFIC
    "Fulham": "EPL", "Leeds United": "EFL", "FC Barcelona": "LIGA",
    "India": "INTL", "Mumbai Indians": "IPL", "Chennai Super Kings": "IPL",
    "USA Cricket": "USA", "United States": "USA"
}

def get_team_region(name):
    """Checks if the team name (or part of it) is in our strict list."""
    # Check exact full matches or strict substring matches from our keys
    for key, region in STRICT_TEAMS.items():
        if key.lower() in name.lower():
            return region
    return None

# --- TIMEZONE ENGINE (Fixed) ---

def parse_game_time(date_str):
    """
    Parses ESPN's ISO-8601 UTC string and converts specifically to Arizona Time (MST).
    Arizona is UTC-7. 
    """
    try:
        # 1. Parse strictly as UTC
        # ESPN format example: "2023-11-20T01:00Z"
        if date_str.endswith("Z"):
            date_str = date_str.replace("Z", "+00:00")
        
        dt_utc = datetime.fromisoformat(date_str)
        
        # 2. Convert to AZT (UTC-7) manually to avoid system locale issues
        # We subtract 7 hours from the UTC timestamp
        dt_az = dt_utc - timedelta(hours=7)
        
        # 3. Format
        time_display = dt_az.strftime("%I:%M %p") # e.g. 06:30 PM
        date_display = dt_az.strftime("%a, %b %d") # e.g. Mon, Nov 20
        
        return dt_az, date_display, time_display
    except Exception as e:
        print(f"Time parse error for {date_str}: {e}")
        return datetime.now(), "Date TBD", "TBD"

# --- FETCH & PROCESS ---

def fetch_games():
    print("  -> Scraping the wires...")
    
    endpoints = [
        ("basketball", "nba"),
        ("football", "nfl"),
        ("football", "college-football"),
        ("basketball", "mens-college-basketball"),
        ("baseball", "mlb"),
        ("soccer", "eng.1"), 
        ("soccer", "esp.1"),
        ("cricket", None)
    ]
    
    valid_games = []
    
    for sport, league in endpoints:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard" if league else f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard"
        
        try:
            data = requests.get(url, timeout=5).json()
        except:
            continue
            
        for e in data.get('events', []):
            # 1. Competitors
            try:
                c = e['competitions'][0]
                h = c['competitors'][0]
                a = c['competitors'][1]
                h_name = h['team']['displayName']
                a_name = a['team']['displayName']
            except: continue

            # 2. Strict Filtering
            h_region = get_team_region(h_name)
            a_region = get_team_region(a_name)
            
            if not h_region and not a_region:
                continue # Kills games like "North Texas vs UAB"

            # 3. Time Processing
            dt_obj, date_disp, time_disp = parse_game_time(e['date'])
            
            # Window Check (keep only recent/soon games)
            now = datetime.now() - timedelta(hours=7) # Approx AZ time
            if abs((dt_obj.replace(tzinfo=None) - now).days) > WINDOW_DAYS:
                continue

            # 4. Game Details
            status_state = c['status']['type']['state'] # pre, in, post
            status_detail = c['status']['type']['detail'] # "Final", "10:34 4th"
            
            # Quarter Scores (if available)
            h_lines = [x.get('value') for x in h.get('linescores', [])]
            a_lines = [x.get('value') for x in a.get('linescores', [])]
            
            # Headlines/Notes
            note = ""
            if 'headlines' in e and e['headlines']:
                note = e['headlines'][0].get('shortLinkText') or e['headlines'][0].get('description')
            
            game = {
                "id": e['id'],
                "sport": (league or sport).upper().replace("MENS-COLLEGE-", "NCAA "),
                "sort_dt": dt_obj,
                "date": date_disp,
                "time": time_disp,
                "status_state": status_state,
                "status_detail": status_detail,
                "note": note,
                "home": {
                    "name": h_name,
                    "score": h.get('score', '0'),
                    "record": h.get('records', [{}])[0].get('summary', ''),
                    "logo": h['team'].get('logo', ''),
                    "lines": h_lines
                },
                "away": {
                    "name": a_name,
                    "score": a.get('score', '0'),
                    "record": a.get('records', [{}])[0].get('summary', ''),
                    "logo": a['team'].get('logo', ''),
                    "lines": a_lines
                }
            }
            valid_games.append(game)

    return valid_games

# --- HTML GENERATOR ---

def generate_box_score_html(g):
    """Creates a mini table for quarter/inning scores."""
    if not g['home']['lines']: return ""
    
    # Header row (1, 2, 3, 4...)
    th_cells = "".join([f"<th>{i+1}</th>" for i in range(len(g['home']['lines']))])
    
    # Data rows
    a_cells = "".join([f"<td>{x}</td>" for x in g['away']['lines']])
    h_cells = "".join([f"<td>{x}</td>" for x in g['home']['lines']])
    
    return f"""
    <table class="linescore">
        <thead><tr><th></th>{th_cells}</tr></thead>
        <tbody>
            <tr><td class="tm-code">{g['away']['name'][:3].upper()}</td>{a_cells}</tr>
            <tr><td class="tm-code">{g['home']['name'][:3].upper()}</td>{h_cells}</tr>
        </tbody>
    </table>
    """

def publish(games):
    games.sort(key=lambda x: x['sort_dt'])
    
    cards_html = ""
    for g in games:
        state_class = g['status_state'] # pre, in, post
        
        # Dynamic "Action Button"
        action_btn = ""
        if state_class == 'post':
            action_btn = f"<div class='story-btn'>Read Recap</div>"
        elif state_class == 'in':
            action_btn = f"<div class='story-btn live-pulse'>Live Updates</div>"
        else:
            action_btn = f"<div class='story-btn'>Preview</div>"
            
        # Box Score (only if live/post)
        linescore = generate_box_score_html(g) if state_class != 'pre' else ""
        
        cards_html += f"""
        <article class="game-card {state_class}">
            <div class="card-top">
                <span class="league-tag">{g['sport']}</span>
                <span class="game-time">{g['date']} @ {g['time']} AZT</span>
            </div>
            
            <div class="matchup">
                <div class="team away">
                    <img src="{g['away']['logo']}" onerror="this.style.display='none'">
                    <div class="tm-info">
                        <div class="tm-name">{g['away']['name']}</div>
                        <div class="tm-record">{g['away']['record']}</div>
                    </div>
                    <div class="tm-score">{g['away']['score']}</div>
                </div>
                
                <div class="game-meta">
                    <div class="status">{g['status_detail']}</div>
                    {linescore}
                </div>

                <div class="team home">
                    <div class="tm-score">{g['home']['score']}</div>
                    <div class="tm-info">
                        <div class="tm-name">{g['home']['name']}</div>
                        <div class="tm-record">{g['home']['record']}</div>
                    </div>
                    <img src="{g['home']['logo']}" onerror="this.style.display='none'">
                </div>
            </div>
            
            <div class="card-footer">
                <div class="game-note">{g['note'] or "Regional Coverage"}</div>
                <details>
                    <summary>{action_btn}</summary>
                    <div class="full-story">
                        <p><strong>{g['away']['name']} vs {g['home']['name']}</strong></p>
                        <p>Detailed stats and play-by-play data would populate here in the full version.</p>
                    </div>
                </details>
            </div>
        </article>
        """
        
    if not cards_html:
        cards_html = "<div class='empty'>No games found for your teams in the current window.</div>"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>The Tempe Torch</title>
        <meta http-equiv="refresh" content="300">
        <style>
            :root {{
                --bg: #eef2f5; --card: #ffffff; --text: #111; 
                --gray: #666; --border: #e0e0e0;
                --az-red: #B1063A; --accent: #2c3e50;
            }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: var(--bg); margin: 0; padding: 20px; }}
            
            h1 {{ text-align: center; font-family: 'Georgia', serif; color: var(--accent); margin-bottom: 5px; }}
            .header-info {{ text-align: center; color: var(--gray); font-size: 0.9rem; margin-bottom: 30px; font-style: italic; }}

            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; max-width: 1400px; margin: 0 auto; }}
            
            .game-card {{ background: var(--card); border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid var(--border); }}
            
            /* Status Colors */
            .game-card.in {{ border-left: 5px solid #d32f2f; }} /* Live */
            .game-card.post {{ border-left: 5px solid #333; }} /* Final */
            .game-card.pre {{ border-left: 5px solid #1976d2; }} /* Future */

            .card-top {{ background: #f8f9fa; padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); }}
            .league-tag {{ font-weight: 800; font-size: 0.7rem; letter-spacing: 1px; color: var(--gray); text-transform: uppercase; }}
            .game-time {{ font-weight: 600; font-size: 0.85rem; color: var(--accent); }}

            .matchup {{ padding: 20px; display: flex; align-items: center; justify-content: space-between; }}
            
            .team {{ display: flex; align-items: center; gap: 15px; flex: 1; }}
            .team.away {{ justify-content: flex-start; }}
            .team.home {{ justify-content: flex-end; text-align: right; }}
            .team img {{ height: 40px; width: 40px; object-fit: contain; }}
            
            .tm-info {{ display: flex; flex-direction: column; }}
            .tm-name {{ font-weight: 700; font-size: 1.1rem; line-height: 1.1; }}
            .tm-record {{ font-size: 0.75rem; color: var(--gray); margin-top: 2px; }}
            .tm-score {{ font-size: 2rem; font-weight: 800; color: #000; font-variant-numeric: tabular-nums; }}

            .team.away .tm-score {{ margin-left: auto; padding-right: 15px; }}
            .team.home .tm-score {{ margin-right: auto; padding-left: 15px; }}

            .game-meta {{ display: flex; flex-direction: column; align-items: center; min-width: 100px; }}
            .status {{ font-size: 0.8rem; font-weight: bold; color: var(--az-red); margin-bottom: 5px; text-transform: uppercase; }}
            
            /* Box Score Mini Table */
            .linescore {{ border-collapse: collapse; font-size: 0.7rem; color: var(--gray); }}
            .linescore td, .linescore th {{ padding: 2px 5px; text-align: center; border: 1px solid #eee; }}
            .tm-code {{ font-weight: bold; color: #000; }}

            .card-footer {{ padding: 10px 20px; background: #fff; border-top: 1px solid #f0f0f0; }}
            .game-note {{ font-size: 0.85rem; color: #555; margin-bottom: 10px; font-style: italic; min-height: 1.2em; }}
            
            details summary {{ list-style: none; outline: none; }}
            details summary::-webkit-details-marker {{ display: none; }}
            
            .story-btn {{ 
                display: block; width: 100%; text-align: center; 
                background: #f1f3f4; padding: 8px 0; border-radius: 6px; 
                font-weight: 600; font-size: 0.9rem; color: #333; cursor: pointer; transition: 0.2s; 
            }}
            .story-btn:hover {{ background: #e0e0e0; }}
            .story-btn.live-pulse {{ background: #ffebee; color: #c62828; animation: pulse 2s infinite; }}

            .full-story {{ padding: 15px; background: #fafafa; margin-top: 10px; border-radius: 8px; font-size: 0.9rem; color: #444; }}

            @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} 100% {{ opacity: 1; }} }}
            
            @media (max-width: 600px) {{
                .matchup {{ flex-direction: column; gap: 15px; }}
                .team {{ width: 100%; justify-content: space-between !important; }}
                .team.home {{ flex-direction: row-reverse; }}
                .team.away .tm-score {{ margin: 0; }}
                .team.home .tm-score {{ margin: 0; }}
            }}
        </style>
    </head>
    <body>
        <h1>The Tempe Torch</h1>
        <div class="header-info">
            Strict Geofence Active • All Times Arizona (MST) • Updated {datetime.now().strftime('%I:%M %p')}
        </div>
        <div class="grid">
            {cards_html}
        </div>
    </body>
    </html>
    """
    
    with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Published {len(games)} games to {OUTPUT_HTML_PATH}")

if __name__ == "__main__":
    if os.environ.get('CI') == 'true':
        publish(fetch_games())
    else:
        while True:
            publish(fetch_games())
            print(f"Sleeping {REFRESH_RATE_MINUTES}m...")
            time.sleep(REFRESH_RATE_MINUTES * 60)
