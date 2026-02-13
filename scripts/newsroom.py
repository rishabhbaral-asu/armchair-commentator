import json
import time
import os
import requests
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_HTML_PATH = Path("index.html")
REFRESH_RATE_MINUTES = 10
WINDOW_DAYS_BACK = 30
WINDOW_DAYS_FWD = 14

# --- 1. LEAGUE VAULT (Automatic Approval) ---
# Games in these leagues are ALWAYS approved, regardless of team name.
SAFE_LEAGUES = {
    # SOCCER - EUROPE
    "eng.1", "esp.1", "ger.1", "fra.1", 
    "uefa.champions", "uefa.europa", "uefa.euro",
    
    # SOCCER - INTERNATIONAL / AMERICAS
    "fifa.world", "conmebol.america", "concacaf.gold",
    "usa.1", "usa.nwsl", "ind.isl",
    
    # CRICKET
    "ind.ipl", "usa.mlc", "icc.worldcup", "icc.t20worldcup", "icc.ct"
}

# --- 2. PRECISE GEO-FILTERS ---
# We ONLY match if the team name contains a specific City, State, or Unique School Name.
# Generic nicknames (Ducks, Sharks, Tigers) are BANNED to prevent false positives.

US_LOCATIONS = {
    # CALIFORNIA (Cities & Unique Schools)
    "California", "Cal Poly", "Stanford", "UCLA", "USC", "San Diego", "San Francisco", 
    "Los Angeles", "L.A.", "Sacramento", "Oakland", "San Jose", "Fresno", "Anaheim",
    "Golden State", "Angel City", "Santa Barbara", "Irvine", "Long Beach", "Davis", 
    "Riverside", "St. Mary's", "Pepperdine", "Santa Clara", "Loyola Marymount", "Pacific",

    # ARIZONA
    "Arizona", "Phoenix", "Tempe", "Tucson", "Grand Canyon", "GCU", "NAU",

    # TEXAS
    "Texas", "Houston", "Dallas", "Austin", "San Antonio", "Fort Worth", "El Paso",
    "Arlington", "Lubbock", "Waco", "College Station", "Rice", "SMU", "TCU", "Baylor", 
    "UTEP", "UTSA", "Corpus Christi", "Abilene",

    # ILLINOIS
    "Illinois", "Chicago", "Northwestern", "Evanston", "Champaign", "DePaul", "Loyola",
    "Bradley", "Peoria", "Carbondale", "Northern Illinois", "Southern Illinois",

    # GEORGIA
    "Georgia", "Atlanta", "Athens", "Macon", "Statesboro", "Kennesaw", "Mercer",
    "Valdosta", "Savannah",

    # DMV (DC, MD, VA)
    "Washington", "D.C.", "District of Columbia", "Maryland", "Virginia", "Baltimore",
    "Richmond", "Norfolk", "Fairfax", "Charlottesville", "Blacksburg", "Arlington",
    "Navy", "Towson", "Mount St. Mary's", "Morgan State", "Coppin State",
    "Georgetown", "George Mason", "George Washington", "American Univ", 
    "James Madison", "JMU", "Liberty", "Old Dominion", "VCU", "William & Mary", 
    "Hampton", "Radford", "VMI"
}

# --- 3. GLOBAL CLUB WATCHLIST ---
# Major clubs to catch in friendlies/inter-league play.
GLOBAL_CLUBS = {
    # ENGLAND
    "Arsenal", "Aston Villa", "Chelsea", "Everton", "Liverpool", "Man City", 
    "Manchester City", "Man Utd", "Manchester United", "Newcastle", "Tottenham", "Spurs", 
    "West Ham", "Leeds",
    
    # EUROPE GIANTS
    "Real Madrid", "Barcelona", "Atlético", "Bayern", "Dortmund", "Leverkusen", 
    "PSG", "Paris Saint-Germain", "Marseille", "Juventus", "AC Milan", "Inter Milan",

    # INDIA (IPL/ISL Brands)
    "Chennai Super Kings", "CSK", "Mumbai Indians", "MI", "RCB", "Royal Challengers", 
    "Kolkata Knight Riders", "KKR", "Gujarat Titans", "Sunrisers", "Delhi Capitals", 
    "Rajasthan Royals", "Lucknow Super Giants", "Punjab Kings", "Mohun Bagan", "East Bengal"
}

# --- 4. NATIONAL TEAMS ---
TARGET_COUNTRIES = {
    "USA", "United States", "USMNT", "USWNT",
    "India", "Men in Blue",
    "England", "Three Lions",
    "Spain", "La Roja",
    "Germany", "Die Mannschaft",
    "France", "Les Bleus",
    "Mexico", "El Tri",
    "Canada", "Brazil", "Argentina"
}

# --- EXCLUSION LIST ---
# Safety net for ambiguous names.
BLACKLIST = {
    "Washington State", # WA
    "Eastern Washington", # WA
    "Central Washington", # WA
    "West Virginia", # WV
    "Western Illinois" # IL (Technically in IL, remove if you want them!)
}

def is_clubhouse_game(event, league_slug):
    # 1. League Whitelist (The "Golden Ticket")
    if league_slug in SAFE_LEAGUES:
        return True

    # 2. Competitor Scan
    try:
        c = event['competitions'][0]
        teams = [c['competitors'][0]['team']['displayName'], c['competitors'][1]['team']['displayName']]
    except: return False
    
    for team in teams:
        clean_team = team.strip()
        
        # A. National Team Check
        if any(re.search(rf"\b{country}\b", clean_team, re.IGNORECASE) for country in TARGET_COUNTRIES):
            if "Indiana" in clean_team and "India" not in clean_team: pass
            else: return True

        # B. Global Club Whitelist
        if any(club.lower() in clean_team.lower() for club in GLOBAL_CLUBS):
            return True

        # C. US Geographic Check (Strict Mode)
        for loc in US_LOCATIONS:
            if loc.lower() in clean_team.lower():
                # Check Blacklist
                if any(bad.lower() in clean_team.lower() for bad in BLACKLIST):
                    continue
                return True
                
    return False

# --- STORYTELLER ENGINE ---

class Storyteller:
    def __init__(self, game):
        self.g = game
        self.h = game['home']
        self.a = game['away']
        self.city = game['city'].upper() if game['city'] else "THE STADIUM"
        
    def write_body(self):
        if self.g['status'] == 'pre': 
            return f"""<div class='story-container'><h2 class='story-headline'>{self.a['name']} at {self.h['name']}</h2><p><strong>{self.city}</strong> — The {self.h['name']} host the {self.a['name']} at {self.g['venue']}. TV: {self.g['tv'] or 'N/A'}.</p></div>"""
        elif self.g['status'] == 'in':
            return f"""<div class='story-container'><h2 class='story-headline'><span style='color:#ef4444'>●</span> LIVE: {self.h['name']} {self.h['score']} - {self.a['score']} {self.a['name']}</h2><p>Action is underway at {self.g['venue']}. Clock: {self.g['clock']}</p></div>"""
        else:
            try:
                h_s, a_s = int(self.h['score']), int(self.a['score'])
                winner = self.h if h_s > a_s else self.a
                loser = self.a if h_s > a_s else self.h
                return f"""<div class='story-container'><h2 class='story-headline'>{winner['name']} Wins {winner['score']}-{loser['score']}</h2><p><strong>{self.city}</strong> — The {winner['name']} defeated the {loser['name']} at {self.g['venue']}.</p></div>"""
            except: return "Game Complete"

# --- DATA FETCHING ---

def get_az_time(utc_str):
    try:
        clean = utc_str.replace("Z", "")
        dt_utc = datetime.fromisoformat(clean).replace(tzinfo=timezone.utc)
        dt_az = dt_utc - timedelta(hours=7)
        return dt_az, dt_utc.timestamp() * 1000
    except: return datetime.now(), 0

def fetch_wire():
    print("  -> Polling Worldwide Sports Data...")
    sources = [
        ("soccer", "eng.1"), ("soccer", "esp.1"), ("soccer", "ger.1"), ("soccer", "fra.1"),
        ("soccer", "uefa.champions"), ("soccer", "uefa.europa"), ("soccer", "usa.1"), 
        ("soccer", "usa.nwsl"), ("soccer", "ind.isl"), ("soccer", "fifa.world"),
        ("cricket", "ipl"), ("cricket", "icc"), ("cricket", "usa.mlc"),
        ("basketball", "nba"), ("football", "nfl"), ("baseball", "mlb"),
        ("football", "college-football"), ("basketball", "mens-college-basketball"),
        ("basketball", "womens-college-basketball")
    ]
    
    dashboard = []
    seen_ids = set()

    for sport, league in sources:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        try:
            data = requests.get(url, params={'limit': '900'}, timeout=5).json()
        except: continue
            
        for e in data.get('events', []):
            if e['id'] in seen_ids: continue
            if not is_clubhouse_game(e, league): continue

            seen_ids.add(e['id'])
            c = e['competitions'][0]
            az_dt, utc_ts = get_az_time(e['date'])
            
            days_diff = (az_dt.date() - datetime.now().date()).days
            if days_diff < -WINDOW_DAYS_BACK or days_diff > WINDOW_DAYS_FWD: continue

            game = {
                "id": e['id'],
                "sport": (league or sport).upper().replace("COLLEGE-", "NCAA "),
                "dt": az_dt,
                "utc_ts": utc_ts,
                "time_str": az_dt.strftime("%I:%M %p"),
                "status": c['status']['type']['state'],
                "clock": c['status']['type']['detail'],
                "venue": c.get('venue', {}).get('fullName', 'Stadium'),
                "city": c.get('venue', {}).get('address', {}).get('city', ''),
                "tv": c.get('broadcasts', [{}])[0].get('names', [''])[0] if c.get('broadcasts') else "",
                "home": { "name": c['competitors'][0]['team']['displayName'], "score": c['competitors'][0].get('score','0'), "logo": c['competitors'][0]['team'].get('logo','') },
                "away": { "name": c['competitors'][1]['team']['displayName'], "score": c['competitors'][1].get('score','0'), "logo": c['competitors'][1]['team'].get('logo','') }
            }
            
            story = Storyteller(game)
            game['story_html'] = story.write_body()
            dashboard.append(game)
            
    return dashboard

# --- RENDERER ---

def render_dashboard(games):
    live = sorted([g for g in games if g['status'] == 'in'], key=lambda x: x['dt'])
    pre = sorted([g for g in games if g['status'] == 'pre'], key=lambda x: x['dt'])
    post = sorted([g for g in games if g['status'] == 'post'], key=lambda x: x['dt'], reverse=True)
    sorted_games = live + pre + post
    
    html_rows = ""
    current_date = ""
    
    for g in sorted_games:
        g_date = g['dt'].strftime("%A, %B %d")
        if g_date != current_date:
            html_rows += f"<div class='date-header'>{g_date}</div>"
            current_date = g_date
            
        status_class = "live" if g['status'] == 'in' else "final" if g['status'] == 'post' else "pre"
        html_rows += f"""
        <details class="match-card {status_class}">
            <summary class="match-summary">
                <div class="time-col">{g['time_str']}<br><span style="font-size:0.6em">{g['sport']}</span></div>
                <div class="score-col">
                    <div class="team-row"><img src="{g['away']['logo']}" class="logo"> {g['away']['name']} <span class="score">{g['away']['score']}</span></div>
                    <div class="team-row"><img src="{g['home']['logo']}" class="logo"> {g['home']['name']} <span class="score">{g['home']['score']}</span></div>
                </div>
                <div class="status-col">{g['clock'] if g['status']=='in' else g['status'].upper()}</div>
            </summary>
            <div class="article-content">{g['story_html']}</div>
        </details>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Clubhouse Wire</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="600">
        <style>
            body {{ background: #111; color: #eee; font-family: sans-serif; margin: 0; padding-bottom: 50px; }}
            .header {{ background: #000; padding: 10px; text-align: center; color: #3b82f6; border-bottom: 1px solid #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 10px; }}
            .date-header {{ margin: 20px 0 5px; color: #888; font-size: 0.8rem; border-bottom: 1px solid #333; }}
            .match-card {{ background: #1a1a1a; margin-bottom: 8px; border-radius: 6px; border: 1px solid #333; }}
            .match-card.live {{ border-left: 4px solid #ef4444; }}
            .match-summary {{ display: flex; padding: 10px; cursor: pointer; align-items: center; }}
            .match-summary::-webkit-details-marker {{ display: none; }}
            .time-col {{ width: 50px; font-size: 0.75rem; color: #aaa; text-align: center; border-right: 1px solid #333; margin-right: 10px; }}
            .score-col {{ flex: 1; }}
            .team-row {{ display: flex; align-items: center; justify-content: space-between; margin: 2px 0; }}
            .logo {{ width: 16px; height: 16px; margin-right: 5px; }}
            .score {{ font-weight: bold; font-family: monospace; }}
            .status-col {{ font-size: 0.7rem; color: #aaa; width: 60px; text-align: right; }}
            .article-content {{ padding: 15px; background: #222; border-top: 1px solid #333; }}
            .story-headline {{ margin: 0 0 10px; font-size: 1.1rem; }}
        </style>
    </head>
    <body>
        <div class="header"><h1>CLUBHOUSE WIRE</h1></div>
        <div class="container">{html_rows or "<div style='text-align:center;padding:20px'>No Games Found</div>"}</div>
    </body>
    </html>
    """
    with open(OUTPUT_HTML_PATH, "w", encoding='utf-8') as f: f.write(html)
    print(f"✅ Dashboard Updated at {datetime.now()}")

if __name__ == "__main__":
    if os.environ.get('CI') == 'true': render_dashboard(fetch_wire())
    else:
        while True:
            render_dashboard(fetch_wire())
            print(f"Sleeping {REFRESH_RATE_MINUTES}m...")
            time.sleep(REFRESH_RATE_MINUTES * 60)
