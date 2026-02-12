"""
THE TEMPE TORCH — GLOBAL DESK EDITION
-------------------------------------
1. SCOPE: Games +/- 7 Days.
2. LOGIC: Home/Away/Venue checks for AZ, CA, TX, IL, GA, MD, VA, DC teams.
3. PLUS: International coverage for Prem, La Liga, and World Cricket.
"""

import json
import time
import os
import requests
from datetime import datetime, timezone
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_HTML_PATH = Path("index.html")
REFRESH_RATE_MINUTES = 30
WINDOW_DAYS = 7 

# --- THE WATCH LIST ---
# If a team name contains ANY of these strings, we track them.

WATCH_LIST_KEYWORDS = {
    # --- USA: SOUTHWEST & WEST ---
    "Arizona", "Sun Devils", "Wildcats", "Cardinals", "Suns", "Diamondbacks", "D-backs", "Coyotes", "Mercury",
    "California", "Cal", "Stanford", "UCLA", "USC", "Los Angeles", "Lakers", "Clippers", "Dodgers", "Angels", 
    "Rams", "Chargers", "Kings", "Ducks", "San Francisco", "49ers", "Giants", "Warriors", "San Diego", "Padres", 
    "Sacramento", "Sharks", "Earthquakes", "Galaxy", "LAFC",

    # --- USA: TEXAS ---
    "Texas", "Longhorns", "Aggies", "Texas A&M", "Houston", "Rockets", "Texans", "Astros", "Dallas", "Cowboys", 
    "Mavericks", "Stars", "San Antonio", "Spurs", "Rangers", "TCU", "Baylor", "Tech", "SMU",

    # --- USA: MIDWEST & EAST ---
    "Illinois", "Chicago", "Bears", "Bulls", "Blackhawks", "Cubs", "White Sox", "Northwestern", "Fighting Illini",
    "Georgia", "Bulldogs", "Falcons", "Hawks", "Braves", "United", "Tech", "Yellow Jackets",
    "Maryland", "Terrapins", "Baltimore", "Ravens", "Orioles", "Washington", "Commanders", "Wizards", "Capitals", 
    "Nationals", "Virginia", "Cavaliers", "Hokies", "Virginia Tech", "Georgetown", "Hoyas",

    # --- EUROPEAN FOOTBALL ---
    "Fulham", "Cottagers",       # Premier League
    "Leeds", "Leeds United",     # Prem/Championship
    "Barcelona", "Barca", "Blaugrana", # La Liga

    # --- CRICKET: INDIA (National + IPL Affiliates) ---
    "India", "Men in Blue", 
    "Mumbai Indians", "Chennai Super Kings", "Royal Challengers", "Kolkata Knight Riders", 
    "Delhi Capitals", "Punjab Kings", "Rajasthan Royals", "Sunrisers", "Lucknow Super Giants", "Gujarat Titans",

    # --- CRICKET: USA (National + MLC Affiliates) ---
    "United States", "USA Cricket", "Monank Patel",
    "Texas Super Kings", "Los Angeles Knight Riders", "MI New York", 
    "San Francisco Unicorns", "Seattle Orcas", "Washington Freedom"
}

# Strict Venue Safety Net (US Only)
TARGET_STATES = {"AZ", "CA", "TX", "IL", "GA", "MD", "VA", "DC"}

# --- FETCHING ---

def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        return r.json() if r.status_code == 200 else None
    except: return None

def is_in_window(date_str):
    if not date_str: return False
    try:
        # Handle variations in ESPN date formats (sometimes ends in Z, sometimes not)
        clean_date = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_date)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        return abs((dt - now).days) <= WINDOW_DAYS
    except: return False

def is_relevant_game(event):
    """
    Decides if a game matters based on:
    1. Venue (US States)
    2. Identity (Watch List)
    """
    c = event['competitions'][0]
    
    # 1. VENUE CHECK (US Only)
    venue = c.get('venue', {}).get('address', {})
    if venue.get('state') in TARGET_STATES:
        return True
        
    # 2. TEAM IDENTITY CHECK (Global)
    h_name = c['competitors'][0]['team']['displayName']
    a_name = c['competitors'][1]['team']['displayName']
    
    # Check strict keyword match
    for key in WATCH_LIST_KEYWORDS:
        if key.lower() in h_name.lower(): return True
        if key.lower() in a_name.lower(): return True
        
    return False

# --- STORY ENGINE ---

class StoryEngine:
    def __init__(self, game_data):
        self.g = game_data
        self.h = game_data['home']
        self.a = game_data['away']
        
    def generate(self):
        if self.g['status_state'] == 'in': return self.write_live_blog()
        elif self.g['status_state'] == 'post': return self.write_recap()
        else: return self.write_preview()

    def write_preview(self):
        return f"""
        <p class="dateline">{self.g['city'].upper()} (Preview) —</p>
        <p>The {self.h['name']} prepare to host the {self.a['name']} at {self.g['venue']}.</p>
        <p>This matchup draws eyes from fans expecting a high-stakes contest. 
        Vegas has set the line at {self.g['odds']}, suggesting a tight battle.</p>
        """

    def write_recap(self):
        if self.g.get('headline_description'):
            return f"""
            <p class="dateline">{self.g['city'].upper()} (AP) —</p>
            <p>{self.g['headline_description']}</p>
            <hr>
            <p style="font-size:0.9em"><em>{self.get_stat_block()}</em></p>
            """
        
        # Generic Fallback
        winner = self.h if int(self.h['score'] or 0) > int(self.a['score'] or 0) else self.a
        return f"""
        <p class="dateline">{self.g['city'].upper()} —</p>
        <p>The {winner['name']} secured a victory over the {self.a['name'] if winner==self.h else self.h['name']} 
        with a final score of {self.h['score']}-{self.a['score']}.</p>
        <p>{self.get_stat_block()}</p>
        """

    def write_live_blog(self):
        return f"""
        <p class="dateline" style="color:#d32f2f">LIVE • {self.g['time_display']} —</p>
        <p><strong>{self.a['name']} {self.a['score']}</strong> @ <strong>{self.h['name']} {self.h['score']}</strong></p>
        <p>{self.g['status_detail']}</p>
        """

    def get_stat_block(self):
        if not self.g['leaders']: return "Check box score for details."
        return "Key Performers: " + ", ".join(self.g['leaders'])

# --- MAIN LOOP ---

def process_game(e, sport, league):
    c = e['competitions'][0]
    h = next((x for x in c['competitors'] if x['homeAway']=='home'), {})
    a = next((x for x in c['competitors'] if x['homeAway']=='away'), {})
    
    # Headlines
    headline_desc = None
    if 'headlines' in e and len(e['headlines']) > 0:
        headline_desc = e['headlines'][0].get('description') or e['headlines'][0].get('shortLinkText')

    # Leaders (Generic parser for different sports structures)
    leaders = []
    if 'leaders' in c:
        for l in c['leaders']:
            if l.get('leaders'):
                ath = l['leaders'][0]['athlete']['displayName']
                val = l['leaders'][0]['displayValue']
                leaders.append(f"{ath} ({val})")

    # Score cleaning (Cricket scores can be complex strings like "145/2")
    # For sorting, we just take the raw string.
    
    return {
        "id": e['id'],
        "date": datetime.strptime(e['date'].replace("Z", ""), "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc),
        "time_display": datetime.fromisoformat(e['date'].replace("Z", "")).strftime("%I:%M %p"),
        "status_state": c['status']['type']['state'], 
        "status_detail": c['status']['type']['detail'],
        "venue": c.get('venue', {}).get('fullName', 'Stadium'),
        "city": c.get('venue', {}).get('address', {}).get('city', 'Unknown'),
        "odds": c.get('odds', [{}])[0].get('details', 'N/A'),
        "headline_description": headline_desc,
        "leaders": leaders,
        "home": {
            "name": h['team']['displayName'],
            "score": h.get('score', '0'),
            "record": h.get('records', [{}])[0].get('summary', '')
        },
        "away": {
            "name": a['team']['displayName'],
            "score": a.get('score', '0'),
            "record": a.get('records', [{}])[0].get('summary', '')
        }
    }

def run_newsroom():
    print(f"  -> Scraping Global Sports ({WINDOW_DAYS} day window)...")
    
    # Source List: (Sport, League_Slug)
    # Note: 'None' for league means we use the global scoreboard for that sport (useful for Cricket)
    sources = [
        # US Sports
        ("basketball", "nba"), 
        ("football", "nfl"), 
        ("football", "college-football"), 
        ("basketball", "mens-college-basketball"),
        
        # International Football
        ("soccer", "eng.1"),   # Premier League
        ("soccer", "eng.2"),   # Championship (Leeds/Fulham safety net)
        ("soccer", "esp.1"),   # La Liga
        
        # Global Cricket (All Leagues/Intl)
        ("cricket", None)      # None = global scoreboard
    ]
    
    sections = {}
    
    for sport, league in sources:
        # Dynamic URL construction
        if league:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        else:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard"
            
        data = fetch_json(url)
        if not data: continue
        
        for e in data.get('events', []):
            if not is_in_window(e['date']): continue
            
            if is_relevant_game(e):
                g = process_game(e, sport, league or "global")
                writer = StoryEngine(g)
                
                story = {
                    "headline": f"{g['away']['name']} vs {g['home']['name']}",
                    "body": writer.generate(),
                    "date_display": g['date'].strftime("%a %b %d"),
                    "status": g['status_detail']
                }
                
                # Naming Logic
                if league: 
                    cat = league.replace("mens-", "").replace("college-", "NCAA ").replace("eng.1", "Premier League").replace("eng.2", "Championship").replace("esp.1", "La Liga").upper()
                else:
                    cat = sport.upper() # "CRICKET"
                    
                if cat not in sections: sections[cat] = []
                sections[cat].append(story)
                
    return sections

def publish_html(sections):
    print("  -> Generating HTML...")
    content = ""
    
    # Sort keys to put Cricket/Soccer at the top or bottom as you prefer. 
    # Currently alphabetical.
    for cat, stories in sorted(sections.items()):
        stories.sort(key=lambda x: x['date_display'])
        grid_html = ""
        for s in stories:
            grid_html += f"""
            <article class="story-card">
                <div class="meta">{cat} • {s['date_display']} • {s['status']}</div>
                <h3>{s['headline']}</h3>
                <div class="body">{s['body']}</div>
            </article>
            """
        content += f"<h2 class='section-title'>{cat}</h2><div class='grid'>{grid_html}</div>"
        
    if not content: content = "<div style='text-align:center'>No games found. The team buses are empty.</div>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>The Tempe Torch</title>
        <meta http-equiv="refresh" content="1800">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Merriweather:wght@300;400;700&display=swap');
            body {{ background: #fdfbf7; color: #111; font-family: 'Merriweather', serif; padding: 40px; }}
            h1 {{ font-family: 'Playfair Display'; font-size: 4rem; text-align: center; margin-bottom: 10px; }}
            .subhead {{ text-align: center; font-style: italic; color: #555; margin-bottom: 50px; border-bottom: 1px solid #ccc; padding-bottom: 20px; }}
            
            .section-title {{ border-bottom: 2px solid #800000; color: #800000; font-family: 'Playfair Display'; margin-top: 40px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 40px; }}
            
            .story-card {{ background: #fff; padding: 30px; border: 1px solid #eee; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            .story-card h3 {{ font-family: 'Playfair Display'; font-size: 1.8rem; margin: 10px 0; }}
            .meta {{ font-size: 0.8rem; text-transform: uppercase; color: #888; font-weight: bold; letter-spacing: 1px; }}
            .body {{ font-size: 1rem; line-height: 1.7; color: #333; }}
            .body p {{ margin-bottom: 15px; }}
            .dateline {{ font-weight: bold; font-family: sans-serif; font-size: 0.85rem; color: #444; text-transform: uppercase; }}
        </style>
    </head>
    <body>
        <h1>The Tempe Torch</h1>
        <div class="subhead">Global Edition (Tempe • London • Barcelona • Mumbai) • {datetime.now().strftime('%B %d, %Y')}</div>
        {content}
    </body>
    </html>
    """
    with open(OUTPUT_HTML_PATH, "w") as f: f.write(html)
    print(f"✅ Published to {OUTPUT_HTML_PATH}")

if __name__ == "__main__":
    if os.environ.get('CI') == 'true':
        publish_html(run_newsroom())
    else:
        while True:
            publish_html(run_newsroom())
            print(f"Sleeping {REFRESH_RATE_MINUTES}m...")
            time.sleep(REFRESH_RATE_MINUTES * 60)
