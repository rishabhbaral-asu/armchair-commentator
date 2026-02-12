import json
import time
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_HTML_PATH = Path("index.html")
REFRESH_RATE_MINUTES = 15
WINDOW_DAYS_BACK = 14  # Look back 2 weeks (Catch recent past games)
WINDOW_DAYS_FWD = 7    # Look forward 1 week

# --- THE CLUBHOUSE (STRICT ADMITTANCE) ---
CLUBHOUSE = {
    # ARIZONA
    "Arizona Cardinals", "Phoenix Suns", "Arizona Diamondbacks", "Arizona State", 
    "Arizona Wildcats", "Phoenix Mercury", "Tucson", "Sun Devils",
    # CALIFORNIA
    "Lakers", "Clippers", "Warriors", "Sacramento Kings", 
    "Dodgers", "Giants", "Padres", "Angels",
    "Rams", "Chargers", "49ers",
    "USC", "UCLA", "Cal Bears", "Stanford",
    # TEXAS
    "Cowboys", "Texans", "Mavericks", "Rockets", "Spurs",
    "Rangers", "Astros", "Stars",
    "Longhorns", "Aggies", "Red Raiders", "Baylor", "TCU", "SMU", "Cougars",
    # ILLINOIS
    "Bears", "Bulls", "Blackhawks", "Cubs", "White Sox", "Fighting Illini", "Northwestern",
    # GEORGIA
    "Falcons", "Hawks", "Braves", "Atlanta United", "Bulldogs", "Yellow Jackets",
    # DMV
    "Commanders", "Wizards", "Capitals", "Nationals", "Ravens", "Orioles", "Terrapins", 
    "Cavaliers", "Hokies", "Hoyas",
    # INT'L SOCCER
    "Fulham", "Leeds", "Barcelona",
    # CRICKET (IPL + MLC + NATIONAL)
    "Super Kings", "Capitals", "Titans", "Knight Riders", "Super Giants", "Mumbai Indians", 
    "Punjab Kings", "Royals", "Royal Challengers", "Sunrisers",
    "Unicorns", "Orcas", "Freedom", "India", "United States", "USA", "Namibia"
}

# Teams/Keywords to strictly BLOCK (prevents "India" matching "Indiana Pacers")
BLOCKLIST = {"Pacers", "Hoosiers", "Fever", "Indianapolis"}

def is_clubhouse_team(name):
    # 1. Blocklist Check
    for bad in BLOCKLIST:
        if bad in name: return False
        
    # 2. Allowlist Check
    for member in CLUBHOUSE:
        if member.lower() in name.lower():
            return True
    return False

def is_championship_event(event):
    """
    Returns True if this is a major final (Super Bowl, World Series, etc)
    so we can watch it even if our teams aren't playing.
    """
    # Check headlines/notes for keywords
    search_text = ""
    if event.get('competitions'):
        notes = event['competitions'][0].get('notes', [])
        if notes: search_text += " " + str(notes[0].get('headline', ''))
        
    keywords = ["Super Bowl", "World Series", "NBA Finals", "Stanley Cup", "Championship Game", "Final"]
    
    # Simple check: If it's a "Final" in a major league, let it through
    if any(k in search_text for k in keywords):
        return True
    return False

# --- STORYTELLER ENGINE ---

class Storyteller:
    def __init__(self, game):
        self.g = game
        self.h = game['home']
        self.a = game['away']
        
    def write_preview(self):
        return f"""
        <div class="story-body">
            <div class="story-lede">
                <strong>PREVIEW:</strong> The {self.h['name']} prepare to host the {self.a['name']} 
                at {self.g['venue']}.
            </div>
            <div class="tale-tape">
                <h4>Tale of the Tape</h4>
                <ul>
                    <li><strong>Matchup:</strong> {self.a['name']} vs {self.h['name']}</li>
                    <li><strong>Venue:</strong> {self.g['venue']}</li>
                    <li><strong>Broadcast:</strong> {self.g['tv'] or "Check Local Listings"}</li>
                </ul>
            </div>
            <p>Both squads are looking to make a statement in this {self.g['sport']} clash.</p>
        </div>
        """

    def write_recap(self):
        # Determine winner
        try:
            h_s = int(self.h['score'])
            a_s = int(self.a['score'])
            winner = self.h['name'] if h_s > a_s else self.a['name']
            margin = abs(h_s - a_s)
            verb = "edged out" if margin < 10 else "dominated"
        except:
            winner = "The winner"
            verb = "defeated"

        # Build Box Score Table
        box_html = ""
        if self.h['lines'] and self.a['lines']:
            # Create header rows (1, 2, 3...)
            headers = "".join([f"<th>{i+1}</th>" for i in range(len(self.h['lines']))])
            h_row = "".join([f"<td>{x}</td>" for x in self.h['lines']])
            a_row = "".join([f"<td>{x}</td>" for x in self.a['lines']])
            
            box_html = f"""
            <div class="box-score-container">
                <table class="box-score">
                    <thead><tr><th>Team</th>{headers}<th>T</th></tr></thead>
                    <tbody>
                        <tr><td class="tm">{self.a['name']}</td>{a_row}<td class="tot">{self.a['score']}</td></tr>
                        <tr><td class="tm">{self.h['name']}</td>{h_row}<td class="tot">{self.h['score']}</td></tr>
                    </tbody>
                </table>
            </div>
            """

        return f"""
        <div class="story-body">
            <div class="story-lede">
                <strong>RECAP:</strong> {winner} {verb} the opposition with a final score of 
                {self.h['score']}-{self.a['score']}.
            </div>
            {box_html}
            <div class="notebook">
                <h4>Game Notes</h4>
                <p>{self.g['note'] or "No specific game notes were filed for this event."}</p>
            </div>
        </div>
        """

    def write_live(self):
        return f"""
        <div class="story-body">
            <div class="story-lede live-pulse-text">
                <strong>LIVE ACTION:</strong> This game is currently in progress.
            </div>
            <div class="tale-tape">
                <ul>
                    <li><strong>Clock:</strong> {self.g['clock']}</li>
                    <li><strong>TV:</strong> {self.g['tv']}</li>
                </ul>
            </div>
        </div>
        """

# --- DATA FETCHING ---

def get_az_time(utc_str):
    try:
        clean = utc_str.replace("Z", "")
        dt_utc = datetime.fromisoformat(clean)
        return dt_utc - timedelta(hours=7)
    except: return datetime.now()

def fetch_wire():
    print("  -> Scanning Global Wires...")
    sources = [
        ("basketball", "nba"), ("football", "nfl"), ("football", "college-football"),
        ("basketball", "mens-college-basketball"), ("baseball", "mlb"),
        ("soccer", "eng.1"), ("soccer", "esp.1"), ("soccer", "usa.1"),
        ("cricket", "ipl"), ("cricket", None) 
    ]
    
    dashboard = []
    seen_ids = set()

    for sport, league in sources:
        base = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard" if league else f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard"
        try:
            data = requests.get(base, timeout=4).json()
        except: continue
            
        for e in data.get('events', []):
            if e['id'] in seen_ids: continue
            
            # 1. Clubhouse & Championship Filter
            try:
                c = e['competitions'][0]
                h_tm = c['competitors'][0]['team']
                a_tm = c['competitors'][1]['team']
            except: continue

            # PASS if: Home is Clubhouse OR Away is Clubhouse OR It's a Major Final
            if not (is_clubhouse_team(h_tm['displayName']) or 
                    is_clubhouse_team(a_tm['displayName']) or 
                    is_championship_event(e)):
                continue

            seen_ids.add(e['id'])

            # 2. Window Check (Expanded)
            az_dt = get_az_time(e['date'])
            days_diff = (az_dt.date() - datetime.now().date()).days
            if days_diff < -WINDOW_DAYS_BACK or days_diff > WINDOW_DAYS_FWD:
                continue

            # 3. Parse Data
            status = c['status']['type']['state']
            note = c.get('notes', [{}])[0].get('headline', '') if c.get('notes') else ""
            
            # Linescores
            h_lines = [x.get('value') for x in c['competitors'][0].get('linescores', [])]
            a_lines = [x.get('value') for x in c['competitors'][1].get('linescores', [])]

            game = {
                "id": e['id'],
                "sport": (league or sport).upper(),
                "dt": az_dt,
                "date_str": az_dt.strftime("%a %b %d"),
                "time_str": az_dt.strftime("%I:%M %p"),
                "status": status,
                "clock": c['status']['type']['detail'],
                "venue": c.get('venue', {}).get('fullName', 'Unknown Venue'),
                "tv": c.get('broadcasts', [{}])[0].get('names', [''])[0] if c.get('broadcasts') else "",
                "note": note,
                "home": { "name": h_tm['displayName'], "score": c['competitors'][0].get('score',''), "logo": h_tm.get('logo',''), "lines": h_lines },
                "away": { "name": a_tm['displayName'], "score": c['competitors'][1].get('score',''), "logo": a_tm.get('logo',''), "lines": a_lines }
            }
            
            # Generate Story HTML
            story = Storyteller(game)
            if status == 'pre': game['story_html'] = story.write_preview()
            elif status == 'post': game['story_html'] = story.write_recap()
            else: game['story_html'] = story.write_live()
            
            dashboard.append(game)
            
    return dashboard

# --- DASHBOARD RENDERER ---

def render_dashboard(games):
    games.sort(key=lambda x: x['dt'], reverse=True) # Newest first usually better for mixed lists, or sort Ascending.
    # Let's sort Ascending (Oldest to Newest) so upcoming games are at bottom? 
    # Actually, for a news feed, usually we want "Today" near top. 
    # Let's sort by date descending (Newest first).
    
    html_rows = ""
    current_date = ""
    
    for g in games:
        # Date Header
        g_date = g['dt'].strftime("%A, %B %d")
        if g_date != current_date:
            html_rows += f"<div class='date-header'>{g_date}</div>"
            current_date = g_date
            
        status_class = "live" if g['status'] == 'in' else g['status']
        h_score = g['home']['score'] if g['status'] != 'pre' else ""
        a_score = g['away']['score'] if g['status'] != 'pre' else ""
        
        # Highlight logic
        h_cls = "my-team" if is_clubhouse_team(g['home']['name']) else ""
        a_cls = "my-team" if is_clubhouse_team(g['away']['name']) else ""

        html_rows += f"""
        <details class="match-card {status_class}">
            <summary class="match-summary">
                <div class="time-col">
                    <div class="time">{g['time_str']}</div>
                    <div class="league">{g['sport']}</div>
                </div>
                
                <div class="score-col">
                    <div class="team-row">
                        <img src="{g['away']['logo']}" class="logo" onerror="this.style.display='none'">
                        <span class="name {a_cls}">{g['away']['name']}</span>
                        <span class="score">{a_score}</span>
                    </div>
                    <div class="team-row">
                        <img src="{g['home']['logo']}" class="logo" onerror="this.style.display='none'">
                        <span class="name {h_cls}">{g['home']['name']}</span>
                        <span class="score">{h_score}</span>
                    </div>
                </div>
                
                <div class="status-col">
                    <div class="status-txt">{g['clock']}</div>
                    <div class="expand-icon">▼</div>
                </div>
            </summary>
            
            <div class="match-story">
                {g['story_html']}
            </div>
        </details>
        """

    if not html_rows: html_rows = "<div class='empty'>No games found.</div>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>The Clubhouse</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="300">
        <style>
            :root {{
                --bg: #121212; --card: #1e1e1e; --text: #e0e0e0;
                --accent: #bb86fc; --border: #333; --live: #cf6679;
            }}
            body {{ background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; margin: 0; padding: 0; padding-bottom: 50px; }}
            
            .header {{ background: #1f1f1f; padding: 20px; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 99; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
            h1 {{ margin: 0; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 2px; color: var(--accent); }}
            
            .container {{ max-width: 700px; margin: 0 auto; padding: 10px; }}
            .date-header {{ margin: 25px 0 10px; font-weight: bold; color: #888; border-bottom: 1px solid #333; padding-bottom: 5px; font-size: 0.9rem; text-transform: uppercase; }}
            
            /* CARD STYLES */
            .match-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 12px; overflow: hidden; transition: 0.2s; }}
            .match-card[open] {{ border-color: var(--accent); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
            .match-card.live {{ border-left: 4px solid var(--live); }}
            
            .match-summary {{ list-style: none; display: flex; padding: 15px; cursor: pointer; align-items: center; }}
            .match-summary::-webkit-details-marker {{ display: none; }}
            
            .time-col {{ width: 60px; text-align: center; border-right: 1px solid #333; margin-right: 15px; padding-right: 10px; flex-shrink: 0; }}
            .time {{ font-weight: bold; font-size: 0.85rem; }}
            .league {{ font-size: 0.65rem; color: #777; margin-top: 4px; }}
            
            .score-col {{ flex: 1; }}
            .team-row {{ display: flex; align-items: center; margin: 3px 0; justify-content: space-between; }}
            .logo {{ width: 22px; height: 22px; margin-right: 8px; object-fit: contain; }}
            .name {{ font-size: 0.95rem; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .name.my-team {{ font-weight: bold; color: #fff; }}
            .score {{ font-weight: bold; font-family: monospace; font-size: 1.1rem; }}
            
            .status-col {{ width: 90px; text-align: right; padding-left: 10px; border-left: 1px solid #333; margin-left: 10px; display: flex; flex-direction: column; align-items: flex-end; justify-content: center; }}
            .status-txt {{ font-size: 0.75rem; color: #888; }}
            .expand-icon {{ font-size: 0.7rem; color: #555; margin-top: 5px; transition: transform 0.2s; }}
            .match-card[open] .expand-icon {{ transform: rotate(180deg); }}
            
            /* STORY STYLES */
            .match-story {{ background: #252525; border-top: 1px solid #333; padding: 20px; animation: slideDown 0.2s; }}
            .story-lede {{ font-size: 1rem; line-height: 1.5; margin-bottom: 15px; border-left: 3px solid var(--accent); padding-left: 10px; }}
            .tale-tape li {{ margin-bottom: 5px; font-size: 0.9rem; color: #ccc; }}
            
            .box-score-container {{ overflow-x: auto; margin: 15px 0; }}
            .box-score {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; text-align: center; }}
            .box-score th {{ background: #333; padding: 6px; }}
            .box-score td {{ border-bottom: 1px solid #444; padding: 6px; }}
            .box-score .tm {{ text-align: left; font-weight: bold; color: #ddd; }}
            .box-score .tot {{ font-weight: bold; background: #2a2a2a; }}
            
            .notebook {{ background: #2a2a2a; padding: 15px; border-radius: 6px; margin-top: 15px; }}
            .notebook h4 {{ margin: 0 0 5px 0; font-size: 0.8rem; text-transform: uppercase; color: #888; }}
            .notebook p {{ margin: 0; font-size: 0.9rem; color: #ccc; line-height: 1.4; }}
            
            @keyframes slideDown {{ from {{ opacity: 0; transform: translateY(-5px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="container" style="padding:0">
                <h1>Clubhouse Wire</h1>
                <div style="font-size: 0.8rem; color:#777;">Tempe, AZ • {datetime.now().strftime("%I:%M %p")}</div>
            </div>
        </div>
        <div class="container">
            {html_rows}
        </div>
    </body>
    </html>
    """
    
    with open(OUTPUT_HTML_PATH, "w", encoding='utf-8') as f: f.write(html)
    print(f"✅ Published: {OUTPUT_HTML_PATH}")

if __name__ == "__main__":
    if os.environ.get('CI') == 'true':
        render_dashboard(fetch_wire())
    else:
        while True:
            render_dashboard(fetch_wire())
            print(f"Sleeping {REFRESH_RATE_MINUTES}m...")
            time.sleep(REFRESH_RATE_MINUTES * 60)
