import json
import time
import os
import requests
import re
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_HTML_PATH = Path("index.html")
REFRESH_RATE_MINUTES = 10
WINDOW_DAYS_BACK = 30
WINDOW_DAYS_FWD = 14

# --- THE CLUBHOUSE ROSTER ---
CLUBHOUSE_KEYS = {
    # ARIZONA
    "Arizona Cardinals", "Suns", "Diamondbacks", "Coyotes", "Mercury",
    "Arizona State", "Sun Devils", "Arizona Wildcats", "Roadrunners",
    "Northern Arizona", "NAU", "Lumberjacks", "Grand Canyon", "GCU", "Lopes",
    "Arizona Christian", "Firestorm", "Phoenix Rising",

    # CALIFORNIA
    "Lakers", "Clippers", "Warriors", "Kings", 
    "Dodgers", "Giants", "Padres", "Angels",
    "Rams", "Chargers", "49ers",
    "USC", "UCLA", "Cal Bears", "Stanford",
    "Sharks", "Ducks", "Galaxy", "LA FC", "San Diego FC",
    "Angel City", "San Diego Wave", "Bay FC",

    # TEXAS
    "Cowboys", "Texans", "Mavericks", "Rockets", "Spurs",
    "Rangers", "Astros", "Stars",
    "Longhorns", "Texas A&M", "Texas Tech", "Baylor", 
    "TCU", "SMU", "Cougars", "Houston Dash", "UTEP",

    # ILLINOIS
    "Bears", "Bulls", "Blackhawks", "Cubs", "White Sox",
    "Illini", "Northwestern", "Red Stars",

    # GEORGIA
    "Falcons", "Hawks", "Braves", "Atlanta United",
    "Bulldogs", "Yellow Jackets",

    # DMV & PA
    "Commanders", "Wizards", "Capitals", "Nationals",
    "Ravens", "Orioles", "Terrapins", "Maryland",
    "Cavaliers", "Hokies", "Hoyas", "Spirit",
    "Penn State", "Nittany Lions", "Liberty",

    # PNW
    "Portland State", "Vikings",

    # SOCCER
    "Fulham", "Leeds", "Barcelona",

    # CRICKET
    "Super Kings", "Capitals", "Titans", "Knight Riders", 
    "Super Giants", "Mumbai Indians", "Punjab Kings", "Royals", 
    "Royal Challengers", "Sunrisers", "Unicorns", "Orcas", "Freedom"
}

SAFE_OVERRIDES = {
    "Arizona State", "Penn State", "Texas A&M", "Virginia Tech", 
    "Georgia Tech", "Texas Tech", "Golden State", "Portland State"
}

def is_clubhouse_team(name):
    clean_name = name.strip()
    
    if re.search(r"\b(India|Ind)\b", clean_name, re.IGNORECASE):
        if "Indiana" in clean_name: return False
        return True
    if re.search(r"\b(USA|United States|U\.S\.A\.|Namibia|Pakistan|Pak)\b", clean_name, re.IGNORECASE):
        return True

    if "Texas" in clean_name:
        if clean_name in ["Texas", "Texas Longhorns", "UT"]: return True
        for safe in SAFE_OVERRIDES:
            if safe in clean_name: return True
        if any(x in clean_name for x in ["State", "Tech", "A&M", "San Antonio", "Arlington", "El Paso"]):
             pass 

    for key in CLUBHOUSE_KEYS:
        if key.lower() in clean_name.lower():
            for safe in SAFE_OVERRIDES:
                if safe.lower() == key.lower(): return True
            if key == "India" and "Indiana" in clean_name: return False
            return True
    return False

def is_championship_event(event):
    search_text = event.get('name', '')
    if event.get('competitions'):
        notes = event['competitions'][0].get('notes', [])
        if notes: search_text += " " + str(notes[0].get('headline', ''))
    keywords = ["Super Bowl", "World Series", "NBA Finals", "Stanley Cup", "Final", "Championship"]
    return any(k.lower() in search_text.lower() for k in keywords)

# --- THE AP-STYLE REPORTER ---

class Storyteller:
    def __init__(self, game):
        self.g = game
        self.h = game['home']
        self.a = game['away']
        self.city = game['city'].upper() if game['city'] else "THE ARENA"
        
    def _get_record_str(self, team):
        return f"({team['record']})" if team['record'] else ""

    def _get_leader_text(self, team):
        # Converts leader data (e.g. "Booker 32 pts") into narrative text
        if not team['leader']: return None
        return f"{team['leader']['displayValue']} {team['leader']['displayName']}"

    def write_preview(self):
        # DATELINE
        dateline = f"<strong>{self.city}</strong> (AP) —"
        
        # OPENER
        h_rec = self._get_record_str(self.h)
        a_rec = self._get_record_str(self.a)
        
        lines = [
            f"The {self.h['name']} {h_rec} prepare to defend their home court against the visiting {self.a['name']} {a_rec}.",
            f"All eyes will be on {self.g['venue']} tonight as the {self.h['name']} {h_rec} host the {self.a['name']} {a_rec}.",
            f"The {self.a['name']} {a_rec} travel to {self.city} looking to spoil the party against the {self.h['name']} {h_rec}."
        ]
        opener = random.choice(lines)

        # BETTING CONTEXT
        odds_segment = ""
        if self.g['odds'] and self.g['odds'] != "Even":
            fav = "home" if "-" in self.g['odds'] and "favorites" not in self.g['odds'] else "away" 
            # Simplified logic: usually odds string is like "ARI -5.5"
            odds_segment = f" Vegas has set the line at {self.g['odds']}, with the Over/Under resting at {self.g['overunder']}."
        
        # CLOSER
        closer = f"Tip-off is scheduled for {self.g['time_str']} AZT."

        return f"""
        <div class="story-container">
            <h2 class="story-headline">{self.a['name']} at {self.h['name']}</h2>
            <div class="countdown-box" id="timer-{self.g['id']}" data-utc="{self.g['utc_ts']}">Loading...</div>
            <p>{dateline} {opener}{odds_segment} {closer}</p>
            <div class="metadata-grid">
                <div><strong>TV:</strong> {self.g['tv'] or 'Local'}</div>
                <div><strong>Venue:</strong> {self.g['venue']}</div>
            </div>
        </div>
        """

    def write_recap(self):
        try:
            h_s = int(self.h['score'] or 0)
            a_s = int(self.a['score'] or 0)
        except:
            return self.write_preview() # Fallback if score unavailable

        winner = self.h if h_s > a_s else self.a
        loser = self.a if h_s > a_s else self.h
        w_score = max(h_s, a_s)
        l_score = min(h_s, a_s)
        margin = w_score - l_score
        
        # VERB SELECTION
        if margin == 0: verb = "drew with"
        elif margin <= 3: verb = "narrowly escaped" if "CRICKET" not in self.g['sport'] else "defeated"
        elif margin <= 10: verb = "defeated"
        elif margin <= 20: verb = "handled"
        else: verb = "routed"

        # HEADLINE
        headline = f"{winner['name']} {verb} {loser['name']}, {w_score}-{l_score}"
        
        # DATELINE
        dateline = f"<strong>{self.city}</strong> (AP) —"

        # STAR PLAYER NARRATIVE
        hero_text = ""
        w_leader = self._get_leader_text(winner)
        if w_leader:
            hero_text = f"Behind a stellar performance from {w_leader}, the "
        else:
            hero_text = "The "

        # NARRATIVE CONSTRUCTION
        if margin < 5 and "CRICKET" not in self.g['sport']:
            narrative = f"{hero_text}{winner['name']} held on in the final moments to secure a {w_score}-{l_score} victory over the {loser['name']}."
        elif margin > 20:
            narrative = f"{hero_text}{winner['name']} dominated from start to finish, cruising to a {w_score}-{l_score} blowout win against the {loser['name']}."
        else:
            narrative = f"{hero_text}{winner['name']} {verb} the {loser['name']} {w_score}-{l_score} on {self.g['dt'].strftime('%A')}."

        # VENUE CONTEXT
        venue_text = f" The game was held at {self.g['venue']}."
        
        return f"""
        <div class="story-container">
            <h2 class="story-headline">{headline}</h2>
            <p>{dateline} {narrative}{venue_text}</p>
            <div class="metadata-grid">
                <div><strong>Winner:</strong> {winner['name']}</div>
                <div><strong>Top Performer:</strong> {w_leader or 'N/A'}</div>
            </div>
        </div>
        """

    def write_live(self):
        headline = f"LIVE: {self.a['name']} vs {self.h['name']}"
        
        leader_txt = ""
        if self.h['leader']: leader_txt += f"<br>Home Leader: {self._get_leader_text(self.h)}"
        if self.a['leader']: leader_txt += f"<br>Away Leader: {self._get_leader_text(self.a)}"

        return f"""
        <div class="story-container">
            <h2 class="story-headline"><span style="color:#ef4444">●</span> {headline}</h2>
            <p class="live-pulse-text" style="font-size: 1.2rem; margin: 10px 0;">
                {self.h['score']} - {self.a['score']}
            </p>
            <p><strong>CURRENT SITUATION:</strong> {self.g['clock']}</p>
            <p style="font-size: 0.85rem; color: #aaa;">
                Broadcasting on {self.g['tv'] or 'N/A'}.{leader_txt}
            </p>
        </div>
        """

    def write_body(self):
        if self.g['status'] == 'pre': return self.write_preview()
        elif self.g['status'] == 'in': return self.write_live()
        else: return self.write_recap()

# --- DATA FETCHING ---

def get_az_time(utc_str):
    try:
        clean = utc_str.replace("Z", "")
        dt_utc = datetime.fromisoformat(clean).replace(tzinfo=timezone.utc)
        dt_az = dt_utc - timedelta(hours=7)
        return dt_az, dt_utc.timestamp() * 1000
    except: 
        return datetime.now(), 0

def extract_leader(competitor):
    # Try to grab the top stat leader (Points, Passing Yards, etc.)
    try:
        if 'leaders' in competitor:
            # Usually leaders[-1] is points in basketball, or passing in NFL
            # We take the last one as it's often the 'main' stat category in ESPN's sort
            leader_cat = competitor['leaders'][-1]
            leader_player = leader_cat['leaders'][0]
            return {
                "displayName": leader_player['athlete']['displayName'],
                "displayValue": leader_player['displayValue'] # e.g. "32" or "250 yds"
            }
    except:
        pass
    return None

def fetch_wire():
    print("  -> Scanning Global Wires...")
    sources = [
        ("basketball", "nba"), ("football", "nfl"), ("baseball", "mlb"),
        ("football", "college-football"),
        ("basketball", "mens-college-basketball"), 
        ("basketball", "womens-college-basketball"), 
        ("baseball", "college-baseball"), 
        ("baseball", "college-softball"), 
        ("soccer", "eng.1"), ("soccer", "esp.1"), ("soccer", "usa.1"), ("soccer", "usa.nwsl"),
        ("cricket", "ipl"), ("cricket", "icc"), ("cricket", None)
    ]
    
    dashboard = []
    seen_ids = set()

    for sport, league in sources:
        base = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard" if league else f"https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard"
        try:
            data = requests.get(base, params={'limit': '900'}, timeout=5).json()
        except: continue
            
        for e in data.get('events', []):
            if e['id'] in seen_ids: continue
            
            try:
                c = e['competitions'][0]
                h_tm = c['competitors'][0]['team']
                a_tm = c['competitors'][1]['team']
            except: continue

            home_ok = is_clubhouse_team(h_tm['displayName'])
            away_ok = is_clubhouse_team(a_tm['displayName'])
            champ_ok = is_championship_event(e)
            
            if not (home_ok or away_ok or champ_ok):
                continue

            seen_ids.add(e['id'])
            az_dt, utc_ts = get_az_time(e['date'])
            days_diff = (az_dt.date() - datetime.now().date()).days
            if days_diff < -WINDOW_DAYS_BACK or days_diff > WINDOW_DAYS_FWD: continue

            status = c['status']['type']['state']
            
            # --- EXTRACTING RICH DATA FOR STORYTELLER ---
            h_rec = c['competitors'][0].get('records', [{}])[0].get('summary', '') if c['competitors'][0].get('records') else ''
            a_rec = c['competitors'][1].get('records', [{}])[0].get('summary', '') if c['competitors'][1].get('records') else ''
            
            h_leader = extract_leader(c['competitors'][0])
            a_leader = extract_leader(c['competitors'][1])
            
            city = c.get('venue', {}).get('address', {}).get('city', '')
            
            odds_txt = c['odds'][0].get('details', 'Even') if c.get('odds') else ""
            ou_txt = c['odds'][0].get('overUnder', '--') if c.get('odds') else ""

            sport_lbl = (league or sport).upper().replace("None", "INTL")
            sport_lbl = sport_lbl.replace("COLLEGE-", "NCAA ").replace("MENS-", "M ").replace("WOMENS-", "W ")

            game = {
                "id": e['id'],
                "sport": sport_lbl,
                "dt": az_dt,
                "utc_ts": utc_ts,
                "date_str": az_dt.strftime("%b %d"),
                "time_str": az_dt.strftime("%I:%M %p"),
                "status": status,
                "clock": c['status']['type']['detail'],
                "venue": c.get('venue', {}).get('fullName', 'Unknown Venue'),
                "city": city,
                "tv": c.get('broadcasts', [{}])[0].get('names', [''])[0] if c.get('broadcasts') else "",
                "note": c.get('notes', [{}])[0].get('headline', '') if c.get('notes') else "",
                "odds": odds_txt,
                "overunder": ou_txt,
                "home": { 
                    "name": h_tm['displayName'], 
                    "score": c['competitors'][0].get('score',''), 
                    "logo": h_tm.get('logo',''),
                    "record": h_rec,
                    "leader": h_leader
                },
                "away": { 
                    "name": a_tm['displayName'], 
                    "score": c['competitors'][1].get('score',''), 
                    "logo": a_tm.get('logo',''),
                    "record": a_rec,
                    "leader": a_leader
                }
            }
            
            story = Storyteller(game)
            game['story_html'] = story.write_body()
            dashboard.append(game)
            
    return dashboard

# --- RENDERER ---

def render_dashboard(games):
    live = [g for g in games if g['status'] == 'in']
    completed = [g for g in games if g['status'] == 'post']
    upcoming = [g for g in games if g['status'] == 'pre']
    
    live.sort(key=lambda x: x['dt'], reverse=True)
    completed.sort(key=lambda x: x['dt'], reverse=True)
    upcoming.sort(key=lambda x: x['dt'])
    
    sorted_games = live + completed + upcoming
    
    html_rows = ""
    current_date = ""
    
    for g in sorted_games:
        g_date = g['dt'].strftime("%A, %B %d")
        if g_date != current_date:
            html_rows += f"<div class='date-header'>{g_date}</div>"
            current_date = g_date
            
        status_class = "live" if g['status'] == 'in' else g['status']
        
        if g['status'] == 'pre':
            status_display = f"<span style='color:#ffd700'>{g['odds']}</span>" if g['odds'] else g['time_str']
        else:
            status_display = g['clock']

        h_cls = "my-team" if is_clubhouse_team(g['home']['name']) else ""
        a_cls = "my-team" if is_clubhouse_team(g['away']['name']) else ""
        h_score = g['home']['score'] if g['status'] != 'pre' else ""
        a_score = g['away']['score'] if g['status'] != 'pre' else ""

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
                    <div class="status-txt">{status_display}</div>
                    <div class="expand-btn">EXPAND</div>
                </div>
            </summary>
            
            <div class="article-content">
                {g['story_html']}
            </div>
        </details>
        """

    if not html_rows: html_rows = "<div class='empty'>No games on the wire.</div>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Clubhouse Wire</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="600">
        <style>
            :root {{ --bg: #0f0f0f; --card: #1a1a1a; --text: #eee; --accent: #3b82f6; --border: #333; --live: #ef4444; }}
            body {{ background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; margin: 0; }}
            
            .header {{ background: #111; padding: 15px; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 99; display: flex; justify-content: space-between; align-items: center; }}
            h1 {{ margin: 0; font-size: 1rem; text-transform: uppercase; letter-spacing: 1px; color: var(--accent); }}
            #live-clock {{ font-family: monospace; font-size: 0.9rem; color: #888; background: #222; padding: 4px 8px; border-radius: 4px; border: 1px solid #333; }}
            
            .container {{ max-width: 600px; margin: 0 auto; padding: 10px; padding-bottom: 50px; }}
            .date-header {{ margin: 25px 0 8px; color: #666; font-size: 0.75rem; font-weight: bold; text-transform: uppercase; border-bottom: 1px solid #222; }}
            
            .match-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 6px; margin-bottom: 10px; }}
            .match-card.live {{ border-left: 3px solid var(--live); }}
            .match-summary {{ list-style: none; display: flex; padding: 12px; align-items: center; cursor: pointer; }}
            .match-summary::-webkit-details-marker {{ display: none; }}
            
            .time-col {{ width: 50px; text-align: center; border-right: 1px solid #333; margin-right: 10px; padding-right: 5px; opacity: 0.7; }}
            .time {{ font-weight: bold; font-size: 0.75rem; }}
            .league {{ font-size: 0.55rem; margin-top: 2px; }}
            
            .score-col {{ flex: 1; }}
            .team-row {{ display: flex; align-items: center; margin: 2px 0; justify-content: space-between; }}
            .logo {{ width: 18px; height: 18px; margin-right: 8px; object-fit: contain; }}
            .name {{ font-size: 0.9rem; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .name.my-team {{ font-weight: bold; color: #fff; }}
            .score {{ font-weight: bold; font-family: monospace; font-size: 1rem; }}
            
            .status-col {{ width: 80px; text-align: right; border-left: 1px solid #333; margin-left: 8px; padding-left: 8px; display: flex; flex-direction: column; align-items: flex-end; justify-content: center; }}
            .status-txt {{ font-size: 0.65rem; color: #aaa; margin-bottom: 4px; font-weight: bold; }}
            .expand-btn {{ font-size: 0.55rem; background: #333; padding: 2px 5px; border-radius: 3px; color: #fff; }}
            
            .article-content {{ background: #222; padding: 15px; border-top: 1px solid #333; animation: fade 0.2s; }}
            .story-headline {{ margin: 0 0 10px; font-size: 1rem; color: #fff; }}
            .betting-line {{ background: #2a2a2a; border-left: 3px solid #ffd700; padding: 8px; margin-bottom: 10px; font-size: 0.85rem; color: #ddd; }}
            .odds-tag {{ font-weight: bold; color: #ffd700; font-size: 0.7rem; margin-right: 5px; }}
            
            .countdown-box {{ text-align: center; font-family: monospace; font-size: 1.1rem; color: var(--accent); margin-bottom: 10px; padding: 10px; background: #151515; border-radius: 4px; border: 1px solid #333; }}
            .metadata-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; border-top: 1px solid #333; padding-top: 10px; font-size: 0.75rem; color: #888; }}
            
            .live-pulse-text {{ color: var(--live); font-weight: bold; animation: pulse 1.5s infinite; }}
            @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
            @keyframes fade {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        </style>
        <script>
            function updateClock() {{
                const now = new Date();
                const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
                const azTime = new Date(utc - (3600000 * 7));
                let hours = azTime.getHours();
                const ampm = hours >= 12 ? 'PM' : 'AM';
                hours = hours % 12;
                hours = hours ? hours : 12; 
                const minutes = azTime.getMinutes().toString().padStart(2, '0');
                const seconds = azTime.getSeconds().toString().padStart(2, '0');
                document.getElementById('live-clock').textContent = hours + ':' + minutes + ':' + seconds + ' ' + ampm;
            }}
            
            function updateCountdowns() {{
                const nowUTC = new Date().getTime();
                document.querySelectorAll('.countdown-box').forEach(box => {{
                    const targetUTC = parseFloat(box.dataset.utc);
                    const diff = targetUTC - nowUTC;
                    
                    if (diff < 0) {{
                        box.innerHTML = "GAME TIME / FINISHED";
                        return;
                    }}
                    
                    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
                    const h = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                    const s = Math.floor((diff % (1000 * 60)) / 1000);
                    
                    if (d > 0) box.innerHTML = `T-MINUS: ${{d}}d ${{h}}h ${{m}}m`;
                    else box.innerHTML = `T-MINUS: ${{h}}h ${{m}}m ${{s}}s`;
                }});
            }}

            setInterval(updateClock, 1000);
            setInterval(updateCountdowns, 1000);
            window.onload = function() {{ updateClock(); updateCountdowns(); }};
        </script>
    </head>
    <body>
        <div class="header">
            <h1>Clubhouse Wire</h1>
            <div id="live-clock">--:--:--</div>
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
