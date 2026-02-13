import json
import time
import os
import requests
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_HTML_PATH = Path("index.html")
WHITELIST_PATH = Path("scripts/whitelist.json")
REFRESH_RATE_MINUTES = 5

# SETTINGS: How far to look?
HISTORY_DEPTH = 3   # Days in the past (for final scores)
FUTURE_DEPTH = 5    # Days in the future (for upcoming previews)

# --- HELPER: FUZZY MATCHING ---
def load_whitelist():
    if not WHITELIST_PATH.exists():
        # Default fallback if file missing
        return ["India", "Pakistan", "Australia", "England", "Lakers", "Liverpool", "Real Madrid"]
    with open(WHITELIST_PATH, "r") as f:
        return [t.strip() for t in json.load(f)]

def fuzzy_match(name, whitelist):
    if not whitelist: return True # If empty, show everything
    clean_name = name.lower()
    for item in whitelist:
        if item.lower() in clean_name: return True
    return False

# --- THE JOURNALIST (AP STYLE ENGINE) ---
class Storyteller:
    def __init__(self, game):
        self.g = game
        self.h = game['home']
        self.a = game['away']
        self.city = (game['city'] or "THE STADIUM").upper()
        self.venue = game['venue']
        self.sport = game['sport']

    def get_leader_text(self, team_data):
        try:
            leader = team_data.get('leaders', [{}])[0]
            player = leader.get('leaders', [{}])[0]
            name = player.get('athlete', {}).get('shortName', '')
            val = player.get('displayValue', player.get('value', '0'))
            if not name: return ""
            return f"{name} ({val})"
        except: return ""

    def write_recap(self):
        # Determine Winner
        try:
            h_s = int(re.sub(r'\D', '', str(self.h['score']).split('/')[0]))
            a_s = int(re.sub(r'\D', '', str(self.a['score']).split('/')[0]))
        except: h_s, a_s = 0, 0

        if h_s > a_s: w, l = self.h, self.a
        else: w, l = self.a, self.h

        # Generate Narrative
        lede = self.g.get('summary', '')
        if not lede:
            star = self.get_leader_text(w)
            if star: lede = f"{star} led the charge as {w['name']} defeated {l['name']}."
            else: lede = f"The {w['name']} secured a victory over {l['name']} in {self.city}."

        return f"""
        <div class='story-container'>
            <h2 class='story-headline'>{w['name']} Defeats {l['name']}</h2>
            <p><span class="dateline">{self.city}</span> — {lede}</p>
            <p class="final-score">Final: {w['name']} {w['score']}, {l['name']} {l['score']}</p>
        </div>"""

    def write_preview(self):
        return f"""
        <div class='story-container'>
            <h2 class='story-headline'>PREVIEW: {self.a['name']} at {self.h['name']}</h2>
            <div class="countdown-box">{self.g['time_str']}</div>
            <p><span class="dateline">{self.city}</span> — The {self.h['name']} host the {self.a['name']} at {self.venue}. 
            Both sides look to make a statement in this {self.sport} matchup.</p>
        </div>"""

    def write_live(self):
        narrative = self.g.get('summary', f"Action is underway at {self.venue}.")
        return f"""
        <div class='story-container'>
            <h2 class='story-headline'><span class='live-dot'>●</span> LIVE: {self.h['name']} vs {self.a['name']}</h2>
            <p class='live-text'>{narrative}</p>
            <p class="final-score">Current: {self.h['name']} {self.h['score']} - {self.a['name']} {self.a['score']}</p>
            <p class='game-clock'>{self.g['clock']}</p>
        </div>"""

    def write_body(self):
        if self.g['status'] == 'pre': return self.write_preview()
        elif self.g['status'] == 'in': return self.write_live()
        else: return self.write_recap()

# --- ENGINE 1: BBC CRICKET (Range Fix) ---
def fetch_bbc_cricket(whitelist):
    print("  -> 🏏 Polling BBC Cricket Feed...")
    
    # FIX: Use the expanded date window
    start_date = (datetime.now() - timedelta(days=HISTORY_DEPTH)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=FUTURE_DEPTH)).strftime("%Y-%m-%d")
    
    url = f"https://push.api.bbci.co.uk/batch?t=%2Fdata%2Fbbc-morph-cricket-scores-lx-sports-data%2FendDate%2F{end_date}%2FstartDate%2F{start_date}%2FtodayDate%2F{start_date}%2Fversion%2F2.4.6?timeout=5"
    
    dashboard = []
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if resp.status_code != 200: return []
        
        data = resp.json()
        try: matches = data['payload'][0]['body']['matchData']['matches']
        except: 
            try: matches = data['payload'][0]['body']['matchData'][0]['tournamentDatesWithEvents'][0]['round']['events']
            except: return []

        match_list = matches.values() if isinstance(matches, dict) else matches

        for m in match_list:
            h_name = m.get('homeTeam', {}).get('name', {}).get('first', 'Home')
            a_name = m.get('awayTeam', {}).get('name', {}).get('first', 'Away')
            
            if whitelist and not (fuzzy_match(h_name, whitelist) or fuzzy_match(a_name, whitelist)):
                continue

            status_str = m.get('eventStatus', 'fixture').lower()
            if status_str in ['live', 'inprogress']: status = 'in'
            elif status_str in ['result', 'post-event']: status = 'post'
            else: status = 'pre'

            # Date Parsing
            if 'startTime' in m:
                dt_obj = datetime.fromisoformat(m['startTime'].replace("Z", "+00:00"))
                local_dt = dt_obj - timedelta(hours=7) # AZ Time
            else: local_dt = datetime.now()

            game = {
                "id": f"bbc_{m.get('eventKey', '0')}",
                "sport": "CRICKET",
                "dt": local_dt, 
                "time_str": local_dt.strftime("%I:%M %p"),
                "status": status,
                "clock": "LIVE" if status == 'in' else "FINAL",
                "venue": m.get('venue', {}).get('name', {}).get('first', 'Cricket Ground'),
                "city": m.get('venue', {}).get('name', {}).get('first', '').split(' ')[-1],
                "summary": m.get('eventStatusNote', ''),
                "home": { 
                    "name": h_name, 
                    "score": m.get('homeTeam', {}).get('scores', {}).get('score', '0'), 
                    "logo": "https://news.bbcimg.co.uk/view/3_0_0/high/news/img/furniture/site/sport/cricket/logo.png"
                },
                "away": { 
                    "name": a_name, 
                    "score": m.get('awayTeam', {}).get('scores', {}).get('score', '0'), 
                    "logo": "https://news.bbcimg.co.uk/view/3_0_0/high/news/img/furniture/site/sport/cricket/logo.png"
                }
            }
            game['story_html'] = Storyteller(game).write_body()
            dashboard.append(game)

    except Exception as e: print(f"     ⚠️ BBC Error: {e}")
    return dashboard

# --- ENGINE 2: ESPN WIRE (Restored Sources) ---
def fetch_espn(whitelist):
    print("  -> 🏀 Polling ESPN Wire...")
    
    # RESTORED: The Full List from the Old Version
    sources = [
        ("soccer", "eng.1"), ("soccer", "esp.1"), ("soccer", "ger.1"), ("soccer", "fra.1"),
        ("soccer", "uefa.champions"), ("soccer", "uefa.europa"), ("soccer", "usa.1"), 
        ("soccer", "usa.nwsl"), ("soccer", "ind.isl"), ("soccer", "fifa.world"),
        ("cricket", "ipl"), ("cricket", "icc"), ("cricket", "international"), ("cricket", "icc.world.t20"),
        ("basketball", "nba"), ("football", "nfl"), ("baseball", "mlb"),
        ("football", "college-football"), ("basketball", "mens-college-basketball"),
        ("basketball", "womens-college-basketball")
    ]
    
    dashboard = []
    seen_ids = set()
    
    # RESTORED: The Wide Date Window
    dates = [datetime.now()]
    for i in range(1, HISTORY_DEPTH + 1): dates.append(datetime.now() - timedelta(days=i))
    for i in range(1, FUTURE_DEPTH + 1): dates.append(datetime.now() + timedelta(days=i))

    for sport, league in sources:
        for d in dates:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
            try:
                resp = requests.get(url, params={'limit': '900', 'dates': d.strftime("%Y%m%d")}, timeout=2)
                for e in resp.json().get('events', []):
                    if e['id'] in seen_ids: continue
                    
                    c = e['competitions'][0]
                    h_team = c['competitors'][0]['team']
                    a_team = c['competitors'][1]['team']
                    
                    if whitelist and not (fuzzy_match(h_team['displayName'], whitelist) or fuzzy_match(a_team['displayName'], whitelist)):
                        continue

                    seen_ids.add(e['id'])
                    
                    utc_str = e['date'].replace("Z", "")
                    dt_obj = datetime.fromisoformat(utc_str)
                    local_dt = dt_obj - timedelta(hours=7) # AZ Time

                    game = {
                        "id": e['id'],
                        "sport": (league or sport).upper().replace("COLLEGE-", "NCAA ").replace("ICC.WORLD.T20", "T20 WC"),
                        "dt": local_dt,
                        "time_str": local_dt.strftime("%I:%M %p"),
                        "status": c['status']['type']['state'],
                        "clock": c['status']['type']['detail'],
                        "venue": c.get('venue', {}).get('fullName', 'Stadium'),
                        "city": c.get('venue', {}).get('address', {}).get('city', ''),
                        "home": { 
                            "name": h_team['displayName'], 
                            "score": c['competitors'][0].get('score','0'), 
                            "logo": h_team.get('logo',''),
                            "leaders": c['competitors'][0].get('leaders', [])
                        },
                        "away": { 
                            "name": a_team['displayName'], 
                            "score": c['competitors'][1].get('score','0'), 
                            "logo": a_team.get('logo',''),
                            "leaders": c['competitors'][1].get('leaders', [])
                        }
                    }
                    game['story_html'] = Storyteller(game).write_body()
                    dashboard.append(game)
            except: continue
    return dashboard

# --- RENDERER (Restored Date Headers) ---
def render_dashboard(games):
    # Sort: Status then Date
    games.sort(key=lambda x: (x['status'] != 'in', x['dt']))
    
    html_rows = ""
    current_date_header = ""

    for g in games:
        # Create Date Header if date changes
        g_date = g['dt'].strftime("%A, %B %d")
        if g_date != current_date_header:
            html_rows += f"<div class='date-header'>{g_date}</div>"
            current_date_header = g_date

        bg = "#666"
        if "CRICKET" in g['sport']: bg = "#10b981"
        elif "NBA" in g['sport']: bg = "#f97316"
        elif "NFL" in g['sport']: bg = "#3b82f6"
        
        status_class = "live" if g['status'] == 'in' else "final" if g['status'] == 'post' else "pre"
        
        html_rows += f"""
        <details class="match-card {status_class}">
            <summary class="match-summary">
                <div class="time-col">
                    {g['time_str']}<br>
                    <span style="font-size:0.6em; background:{bg}; color:#fff; padding:2px 4px; border-radius:3px;">{g['sport'][:9]}</span>
                </div>
                <div class="score-col">
                    <div class="team-row"><img src="{g['away']['logo']}" class="logo" onerror="this.style.opacity=0"> {g['away']['name']} <span class="score">{g['away']['score']}</span></div>
                    <div class="team-row"><img src="{g['home']['logo']}" class="logo" onerror="this.style.opacity=0"> {g['home']['name']} <span class="score">{g['home']['score']}</span></div>
                </div>
                <div class="status-col">{g['clock']}</div>
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
        <meta http-equiv="refresh" content="300"> 
        <style>
            body {{ background: #111; color: #eee; font-family: "Georgia", serif; margin: 0; padding-bottom: 50px; }}
            .header {{ background: #000; padding: 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; position: sticky; top: 0; z-index: 100; font-family: -apple-system, sans-serif; }}
            h1 {{ margin: 0; font-size: 1.2rem; color: #fff; text-transform: uppercase; letter-spacing: 2px; font-weight: 800; }}
            #live-clock {{ font-family: monospace; font-size: 0.9rem; color: #888; }}
            .container {{ max-width: 650px; margin: 0 auto; padding: 10px; }}
            
            .date-header {{ margin: 25px 0 8px; color: #555; font-size: 0.8rem; border-bottom: 1px solid #222; text-transform: uppercase; letter-spacing: 1px; font-family: -apple-system, sans-serif; }}
            
            .match-card {{ background: #1a1a1a; margin-bottom: 12px; border: 1px solid #333; border-radius: 4px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
            .match-card.live {{ border-left: 5px solid #ef4444; }}
            .match-summary {{ display: flex; padding: 15px; cursor: pointer; align-items: center; background: #1e1e1e; font-family: -apple-system, sans-serif; }}
            .match-summary::-webkit-details-marker {{ display: none; }}
            
            .time-col {{ width: 60px; font-size: 0.75rem; color: #888; text-align: center; border-right: 1px solid #333; margin-right: 15px; }}
            .score-col {{ flex: 1; }}
            .team-row {{ display: flex; align-items: center; justify-content: space-between; margin: 4px 0; font-size: 1rem; }}
            .logo {{ width: 24px; height: 24px; margin-right: 10px; object-fit: contain; }}
            .score {{ font-weight: 700; font-variant-numeric: tabular-nums; }}
            .status-col {{ font-size: 0.7rem; color: #aaa; width: 70px; text-align: right; font-weight: 600; }}
            
            .article-content {{ padding: 20px; background: #161616; border-top: 1px solid #333; animation: fadeIn 0.3s ease; }}
            .story-headline {{ margin: 0 0 12px; font-size: 1.4rem; color: #fff; font-weight: bold; line-height: 1.2; font-family: "Georgia", serif; }}
            .dateline {{ font-weight: bold; color: #aaa; text-transform: uppercase; font-size: 0.85rem; font-family: -apple-system, sans-serif; }}
            .story-container p {{ line-height: 1.6; color: #ccc; margin-bottom: 10px; font-size: 1.05rem; }}
            .final-score {{ font-weight: bold; color: #fff; border-top: 1px solid #333; padding-top: 10px; margin-top: 15px; }}
            
            .countdown-box {{ background: #222; border: 1px solid #333; color: #3b82f6; padding: 12px; text-align: center; font-family: monospace; margin: 15px 0; border-radius: 4px; font-size: 1.1rem; }}
            .live-dot {{ color: #ef4444; animation: pulse 1.5s infinite; }}
            
            @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} 100% {{ opacity: 1; }} }}
            @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(-5px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        </style>
        <script>
            function updateClock() {{
                const now = new Date();
                const azTime = new Date(now.getTime() - (3600000 * 7));
                document.getElementById('live-clock').textContent = azTime.toLocaleTimeString([], {{hour: '2-digit', minute:'2-digit'}});
            }}
            setInterval(updateClock, 1000);
            window.onload = updateClock;
        </script>
    </head>
    <body>
        <div class="header">
            <h1>Clubhouse Wire</h1>
            <div id="live-clock">--:--</div>
        </div>
        <div class="container">
            {html_rows or "<div style='text-align:center;padding:40px;color:#666;font-style:italic'>No games found. Check Whitelist settings.</div>"}
        </div>
    </body>
    </html>
    """
    with open(OUTPUT_HTML_PATH, "w", encoding='utf-8') as f: f.write(html)
    print(f"✅ Dashboard Updated at {datetime.now()}")

if __name__ == "__main__":
    if os.environ.get('CI') == 'true': 
        whitelist = load_whitelist()
        render_dashboard(fetch_espn(whitelist) + fetch_bbc_cricket(whitelist))
    else:
        while True:
            whitelist = load_whitelist()
            render_dashboard(fetch_espn(whitelist) + fetch_bbc_cricket(whitelist))
            print(f"Sleeping {REFRESH_RATE_MINUTES}m...")
            time.sleep(REFRESH_RATE_MINUTES * 60)
