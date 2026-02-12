"""
THE TEMPE TORCH — PROFESSIONAL EDITION
--------------------------------------
1. STRICT FILTERING: Only shows games involving teams from the target list (Home or Away).
2. LAYOUT: "Lede" paragraph + Clickable "Read Full Dispatch" for deep dives.
3. CONTENT: Expanded storytelling with stats, quarters, and analysis.
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

# --- THE STUBBORN EDITOR (Strict Watch List) ---
# We map keywords to their "Home Desk" to ensure we only grab relevant teams.

WATCH_LIST = {
    # ARIZONA
    "Arizona": "AZ", "Sun Devils": "AZ", "Wildcats": "AZ", "Cardinals": "AZ", 
    "Suns": "AZ", "Diamondbacks": "AZ", "D-backs": "AZ", "Coyotes": "AZ", "Mercury": "AZ",
    
    # CALIFORNIA
    "California": "CA", "Cal": "CA", "Stanford": "CA", "UCLA": "CA", "USC": "CA", 
    "Los Angeles": "CA", "Lakers": "CA", "Clippers": "CA", "Dodgers": "CA", "Angels": "CA", 
    "Rams": "CA", "Chargers": "CA", "Kings": "CA", "Ducks": "CA", "San Francisco": "CA", 
    "49ers": "CA", "Giants": "CA", "Warriors": "CA", "San Diego": "CA", "Padres": "CA", 
    "Sacramento": "CA", "Sharks": "CA", "Earthquakes": "CA", "Galaxy": "CA", "LAFC": "CA",
    
    # TEXAS
    "Texas": "TX", "Longhorns": "TX", "Aggies": "TX", "Texas A&M": "TX", "Houston": "TX", 
    "Rockets": "TX", "Texans": "TX", "Astros": "TX", "Dallas": "TX", "Cowboys": "TX", 
    "Mavericks": "TX", "Stars": "TX", "San Antonio": "TX", "Spurs": "TX", "Rangers": "TX", 
    "TCU": "TX", "Baylor": "TX", "Tech": "TX", "SMU": "TX",
    
    # ILLINOIS
    "Illinois": "IL", "Chicago": "IL", "Bears": "IL", "Bulls": "IL", "Blackhawks": "IL", 
    "Cubs": "IL", "White Sox": "IL", "Northwestern": "IL", "Fighting Illini": "IL",
    
    # GEORGIA
    "Georgia": "GA", "Bulldogs": "GA", "Falcons": "GA", "Hawks": "GA", "Braves": "GA", 
    "United": "GA", "Yellow Jackets": "GA",
    
    # DMV (DC/MD/VA)
    "Maryland": "MD", "Terrapins": "MD", "Baltimore": "MD", "Ravens": "MD", "Orioles": "MD", 
    "Washington": "DC", "Commanders": "DC", "Wizards": "DC", "Capitals": "DC", "Nationals": "DC", 
    "Virginia": "VA", "Cavaliers": "VA", "Hokies": "VA", "Georgetown": "DC", "Hoyas": "DC",

    # INTERNATIONAL / SPECIFIC CLUBS
    "Fulham": "UK", "Leeds": "UK", "Barcelona": "ESP",
    "India": "IND", "Mumbai Indians": "IND", "Chennai": "IND", "Royal Challengers": "IND",
    "United States": "USA", "USA Cricket": "USA", "Super Kings": "USA", "MI New York": "USA"
}

# --- FETCHING ---

def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        return r.json() if r.status_code == 200 else None
    except: return None

def is_in_window(date_str):
    if not date_str: return False
    try:
        clean_date = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_date)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return abs((dt - now).days) <= WINDOW_DAYS
    except: return False

def get_team_identity(team_name):
    """Returns the region code if the team is in our watchlist, else None."""
    for key, region in WATCH_LIST.items():
        if key.lower() in team_name.lower():
            return region
    return None

def is_relevant_game(event):
    """
    STRICT FILTER: Game is relevant ONLY if Home or Away team is in the watchlist.
    Venue location is ignored to prevent random neutral site games.
    """
    c = event['competitions'][0]
    h_name = c['competitors'][0]['team']['displayName']
    a_name = c['competitors'][1]['team']['displayName']
    
    if get_team_identity(h_name) or get_team_identity(a_name):
        return True
    return False

# --- PRO STORY ENGINE ---

class StoryEngine:
    def __init__(self, game_data):
        self.g = game_data
        self.h = game_data['home']
        self.a = game_data['away']
        self.region = get_team_identity(self.h['name']) or get_team_identity(self.a['name']) or "Global"
        
    def generate_html(self):
        """Returns a tuple: (Lede HTML, Full Body HTML)"""
        status = self.g['status_state']
        
        if status == 'in': 
            lede = self.live_lede()
            body = self.live_details()
        elif status == 'post': 
            lede = self.recap_lede()
            body = self.recap_details()
        else: 
            lede = self.preview_lede()
            body = self.preview_details()
            
        return lede, body

    # --- PREVIEWS ---
    def preview_lede(self):
        return f"""
        <p class="lede-text"><span class="dateline">{self.g['city'].upper()} —</span> 
        The <strong>{self.h['name']}</strong> ({self.h['record']}) prepare to defend their home turf against the 
        incoming <strong>{self.a['name']}</strong> ({self.a['record']}). Tip-off/Kickoff is set for {self.g['time_display']}.</p>
        """

    def preview_details(self):
        return f"""
        <div class="stat-box">
            <h4>Tale of the Tape</h4>
            <ul>
                <li><strong>Venue:</strong> {self.g['venue']}</li>
                <li><strong>Odds:</strong> {self.g['odds']}</li>
                <li><strong>Broadcast:</strong> Check local listings</li>
            </ul>
        </div>
        <p>Analysts are circling this matchup as a potential pivoting point for both squads. 
        With the {self.h['name']} looking to establish dominance at {self.g['venue']}, the pressure is on the visitors 
        to disrupt the rhythm early.</p>
        """

    # --- RECAPS ---
    def recap_lede(self):
        winner = self.h if float(self.h['score'] or 0) > float(self.a['score'] or 0) else self.a
        loser = self.a if winner == self.h else self.h
        margin = float(winner['score']) - float(loser['score'])
        
        verb = "edged out" if margin < 7 else "dominated"
        if margin > 20: verb = "crushed"
        
        return f"""
        <p class="lede-text"><span class="dateline">{self.g['city'].upper()} —</span> 
        The <strong>{winner['name']}</strong> {verb} the <strong>{loser['name']}</strong> with a final score of 
        <strong>{winner['score']}-{loser['score']}</strong>, moving to {winner['record']} on the season.</p>
        """

    def recap_details(self):
        # Construct a box score table if linescores exist
        box_html = ""
        if self.g['h_linescores'] and self.g['a_linescores']:
            headers = "".join([f"<th>{i+1}</th>" for i in range(len(self.g['h_linescores']))])
            h_row = "".join([f"<td>{s}</td>" for s in self.g['h_linescores']])
            a_row = "".join([f"<td>{s}</td>" for s in self.g['a_linescores']])
            box_html = f"""
            <table class="box-score">
                <thead><tr><th>Team</th>{headers}<th>T</th></tr></thead>
                <tbody>
                    <tr><td>{self.a['abbrev']}</td>{a_row}<td><strong>{self.a['score']}</strong></td></tr>
                    <tr><td>{self.h['abbrev']}</td>{h_row}<td><strong>{self.h['score']}</strong></td></tr>
                </tbody>
            </table>
            """

        leaders_html = ""
        if self.g['leaders']:
            leaders_html = "<h4>Key Performers</h4><ul class='leader-list'>" + \
                           "".join([f"<li>{l}</li>" for l in self.g['leaders']]) + "</ul>"

        return f"""
        {box_html}
        {leaders_html}
        <div class="notebook">
            <h4>Reporter's Notebook</h4>
            <p>{self.g['headline_description'] or "Both teams battled hard, but execution in the final minutes proved to be the difference maker."}</p>
        </div>
        """

    # --- LIVE ---
    def live_lede(self):
        return f"""
        <p class="lede-text" style="border-left: 4px solid #d32f2f; padding-left: 10px;">
        <strong style="color:#d32f2f">LIVE ACTION:</strong> The {self.h['name']} are currently battling the {self.a['name']}.
        <br><strong>Current Score:</strong> {self.a['name']} {self.a['score']} - {self.h['name']} {self.h['score']}</p>
        """

    def live_details(self):
        return f"""
        <div class="stat-box">
            <p><strong>Status:</strong> {self.g['status_detail']}</p>
            <p><strong>Venue:</strong> {self.g['venue']}</p>
        </div>
        <p>Updates are flowing in from {self.g['city']}. Check back for the final recap.</p>
        """

# --- MAIN LOGIC ---

def process_game(e, sport, league):
    c = e['competitions'][0]
    h = next((x for x in c['competitors'] if x['homeAway']=='home'), {})
    a = next((x for x in c['competitors'] if x['homeAway']=='away'), {})
    
    # Headlines
    headline_desc = None
    if 'headlines' in e and len(e['headlines']) > 0:
        headline_desc = e['headlines'][0].get('description') or e['headlines'][0].get('shortLinkText')

    # Leaders
    leaders = []
    if 'leaders' in c:
        for l in c['leaders']:
            if l.get('leaders'):
                ath = l['leaders'][0]['athlete']['displayName']
                val = l['leaders'][0]['displayValue']
                leaders.append(f"{ath}: {val}")
    
    # Line Scores (Quarter/Inning scores)
    h_lines = [x.get('value') for x in h.get('linescores', [])]
    a_lines = [x.get('value') for x in a.get('linescores', [])]

    # Odds
    odds_txt = "N/A"
    if c.get('odds'):
        odds_txt = c['odds'][0].get('details', 'N/A')

    return {
        "id": e['id'],
        "date": datetime.strptime(e['date'].replace("Z", ""), "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc),
        "time_display": datetime.fromisoformat(e['date'].replace("Z", "")).strftime("%I:%M %p"),
        "status_state": c['status']['type']['state'], 
        "status_detail": c['status']['type']['detail'],
        "venue": c.get('venue', {}).get('fullName', 'Stadium'),
        "city": c.get('venue', {}).get('address', {}).get('city', 'Unknown'),
        "odds": odds_txt,
        "headline_description": headline_desc,
        "leaders": leaders,
        "h_linescores": h_lines,
        "a_linescores": a_lines,
        "home": {
            "name": h['team']['displayName'],
            "abbrev": h['team'].get('abbreviation', h['team']['displayName'][:3].upper()),
            "score": h.get('score', '0'),
            "record": h.get('records', [{}])[0].get('summary', '0-0')
        },
        "away": {
            "name": a['team']['displayName'],
            "abbrev": a['team'].get('abbreviation', a['team']['displayName'][:3].upper()),
            "score": a.get('score', '0'),
            "record": a.get('records', [{}])[0].get('summary', '0-0')
        }
    }

def run_newsroom():
    print(f"  -> Scraping Global Wires ({WINDOW_DAYS} day window)...")
    
    sources = [
        ("basketball", "nba"), 
        ("football", "nfl"), 
        ("football", "college-football"), 
        ("basketball", "mens-college-basketball"),
        ("soccer", "eng.1"),
        ("soccer", "eng.2"),
        ("soccer", "esp.1"),
        ("cricket", None)
    ]
    
    sections = {}
    
    for sport, league in sources:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard" if league else f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard"
            
        data = fetch_json(url)
        if not data: continue
        
        for e in data.get('events', []):
            if not is_in_window(e['date']): continue
            
            # STRICT IDENTITY CHECK ONLY
            if is_relevant_game(e):
                g = process_game(e, sport, league or "global")
                engine = StoryEngine(g)
                lede, body = engine.generate_html()
                
                story = {
                    "headline": f"{g['away']['name']} vs. {g['home']['name']}",
                    "lede": lede,
                    "body": body,
                    "date_display": g['date'].strftime("%a, %b %d"),
                    "status": g['status_detail']
                }
                
                cat = (league or sport).replace("eng.1", "Premier League").replace("esp.1", "La Liga").upper()
                if "COLLEGE" in cat: cat = "NCAA"
                
                if cat not in sections: sections[cat] = []
                sections[cat].append(story)
                
    return sections

def publish_html(sections):
    print("  -> Generating HTML...")
    content = ""
    
    for cat, stories in sorted(sections.items()):
        stories.sort(key=lambda x: x['date_display'])
        grid_html = ""
        for s in stories:
            grid_html += f"""
            <article class="story-card">
                <div class="meta">{cat} • {s['date_display']}</div>
                <h3>{s['headline']}</h3>
                <div class="summary">
                    {s['lede']}
                </div>
                <details>
                    <summary>Read Full Dispatch</summary>
                    <div class="full-story">
                        {s['body']}
                    </div>
                </details>
            </article>
            """
        content += f"<h2 class='section-title'>{cat}</h2><div class='grid'>{grid_html}</div>"
        
    if not content: content = "<div class='empty-state'>No games involving your teams were found in this window.</div>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>The Tempe Torch</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lora:wght@400;500;700&family=Roboto+Condensed:wght@700&display=swap');
            
            :root {{
                --primary: #1a1a1a;
                --accent: #b71c1c;
                --bg: #f4f1ea;
                --card-bg: #ffffff;
                --text: #2c2c2c;
            }}

            body {{ background: var(--bg); color: var(--text); font-family: 'Lora', serif; margin: 0; padding: 20px; line-height: 1.6; }}
            
            header {{ text-align: center; border-bottom: 4px double var(--primary); margin-bottom: 40px; padding-bottom: 20px; }}
            h1 {{ font-family: 'Playfair Display', serif; font-size: 3.5rem; margin: 0; color: var(--primary); letter-spacing: -1px; }}
            .subhead {{ font-style: italic; color: #555; font-size: 1.1rem; margin-top: 5px; }}
            
            .section-title {{ 
                font-family: 'Roboto Condensed', sans-serif; 
                font-size: 1.5rem; 
                text-transform: uppercase; 
                border-bottom: 2px solid var(--accent); 
                color: var(--accent);
                margin: 40px 0 20px 0; 
            }}
            
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 30px; }}
            
            .story-card {{ 
                background: var(--card-bg); 
                padding: 25px; 
                border: 1px solid #ddd; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
                transition: transform 0.2s;
            }}
            .story-card:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
            
            .story-card h3 {{ font-family: 'Playfair Display', serif; font-size: 1.6rem; margin: 10px 0 15px 0; line-height: 1.2; }}
            .meta {{ font-family: 'Roboto Condensed', sans-serif; font-size: 0.8rem; text-transform: uppercase; color: #888; letter-spacing: 1px; }}
            
            .lede-text {{ font-size: 1.05rem; color: #333; }}
            .dateline {{ font-weight: bold; font-family: sans-serif; font-size: 0.8rem; color: #666; text-transform: uppercase; }}
            
            /* READ MORE TOGGLE */
            details {{ margin-top: 15px; border-top: 1px solid #eee; }}
            summary {{ 
                cursor: pointer; 
                font-family: 'Roboto Condensed', sans-serif; 
                font-weight: bold; 
                color: var(--accent); 
                padding: 15px 0; 
                list-style: none; 
                outline: none;
            }}
            summary::-webkit-details-marker {{ display: none; }}
            summary::after {{ content: " +"; }}
            details[open] summary::after {{ content: " -"; }}
            
            .full-story {{ animation: fadein 0.3s; font-size: 0.95rem; }}
            
            /* BOX SCORE & STATS */
            .box-score {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-family: sans-serif; font-size: 0.85rem; }}
            .box-score th {{ border-bottom: 2px solid #333; padding: 5px; background: #f9f9f9; }}
            .box-score td {{ border-bottom: 1px solid #eee; padding: 5px; text-align: center; }}
            .box-score td:first-child {{ text-align: left; font-weight: bold; }}
            
            .stat-box {{ background: #f9f9f9; padding: 15px; border-left: 3px solid #ccc; margin: 15px 0; }}
            .stat-box h4, .notebook h4 {{ margin: 0 0 10px 0; font-family: 'Roboto Condensed'; text-transform: uppercase; font-size: 0.9rem; }}
            .leader-list {{ padding-left: 20px; margin: 0; }}
            
            @keyframes fadein {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
            
            @media (max-width: 600px) {{
                h1 {{ font-size: 2.5rem; }}
                body {{ padding: 15px; }}
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>The Tempe Torch</h1>
            <div class="subhead">Geofenced Sports Wire • {datetime.now().strftime('%B %d, %Y')}</div>
        </header>
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
