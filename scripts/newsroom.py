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

# --- CRICKET ENGINE (BBC) ---
def fetch_bbc_cricket(whitelist):
    """
    Fetches live cricket scores from the BBC's public feed.
    This is much more reliable for tournaments than ESPN.
    """
    print("  -> Polling BBC Cricket Feed...")
    url = "https://push.api.bbci.co.uk/batch?t=%2Fdata%2Fbbc-morph-cricket-scores-lx-sports-data%2FendDate%2F{today}%2FstartDate%2F{today}%2FtodayDate%2F{today}%2Fversion%2F2.4.6?timeout=5"
    
    # BBC requires today's date in YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    final_url = url.format(today=today)

    dashboard = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(final_url, headers=headers, timeout=5)
        if resp.status_code != 200: return []
        
        data = resp.json()
        # The BBC data structure is nested: payload -> data -> stages
        payload = data['payload'][0]['body']
        
        for match_key, match in payload.get('matchData', []).get('matches', {}).items():
            # Basic info
            home_name = match.get('homeTeam', {}).get('name', 'Unknown')
            away_name = match.get('awayTeam', {}).get('name', 'Unknown')
            
            # Whitelist Check
            if whitelist:
                found = False
                for target in whitelist:
                    if target.lower() in home_name.lower() or target.lower() in away_name.lower():
                        found = True
                        break
                if not found: continue

            # Score Logic
            h_score = match.get('homeTeam', {}).get('scores', '0')
            a_score = match.get('awayTeam', {}).get('scores', '0')
            status = match.get('matchStatus', 'live').lower()
            
            # BBC Status to Our Standard
            if status == 'complete' or status == 'result': standard_status = 'post'
            elif status == 'live' or status == 'inprogress': standard_status = 'in'
            else: standard_status = 'pre'
            
            # Formatting the "Story"
            summary = match.get('matchSummaryText', '')
            
            game = {
                "id": f"bbc_{match_key}",
                "sport": "CRICKET",
                "dt": datetime.now(), # BBC doesn't always give clean start times, assume "today"
                "time_str": "TODAY",
                "status": standard_status,
                "clock": summary if standard_status == 'in' else "FINAL",
                "venue": match.get('venue', {}).get('name', 'The Oval'),
                "home": { "name": home_name, "score": h_score, "logo": "https://news.bbcimg.co.uk/view/3_0_0/high/news/img/furniture/site/sport/cricket/logo.png" },
                "away": { "name": away_name, "score": a_score, "logo": "https://news.bbcimg.co.uk/view/3_0_0/high/news/img/furniture/site/sport/cricket/logo.png" },
                "story_html": f"""
                <div class='story-container'>
                    <h2 class='story-headline'>{home_name} vs {away_name}</h2>
                    <p class='live-text'>{summary}</p>
                    <p class="final-score">{home_name}: {h_score} <br> {away_name}: {a_score}</p>
                </div>"""
            }
            dashboard.append(game)
            
    except Exception as e:
        print(f"⚠️ BBC Fetch Failed: {e}")
        
    return dashboard

# --- STANDARD ESPN FETCHER (UNCHANGED) ---

def load_whitelist():
    if not WHITELIST_PATH.exists(): return ["India", "England", "Australia", "Lakers", "Liverpool"]
    with open(WHITELIST_PATH, "r") as f: return [t.strip() for t in json.load(f)]

def is_approved_game(event, whitelist):
    if not whitelist: return True
    try:
        c = event['competitions'][0]
        teams = [c['competitors'][0]['team']['displayName'], c['competitors'][1]['team']['displayName']]
    except: return False
    for team_name in teams:
        for target in whitelist:
            if target.lower() in team_name.lower(): return True
    return False

def fetch_espn(whitelist):
    print("  -> Polling ESPN Wire...")
    sources = [
        ("soccer", "eng.1"), ("soccer", "esp.1"), ("soccer", "uefa.champions"),
        ("basketball", "nba"), ("football", "nfl"), ("baseball", "mlb")
    ]
    
    dashboard = []
    seen_ids = set()
    
    for sport, league in sources:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        try:
            data = requests.get(url, timeout=2).json()
            for e in data.get('events', []):
                if e['id'] in seen_ids: continue
                if not is_approved_game(e, whitelist): continue
                seen_ids.add(e['id'])
                
                c = e['competitions'][0]
                h = c['competitors'][0]
                a = c['competitors'][1]
                status = c['status']['type']['state']
                
                # Simple Story
                story = f"<div class='story-container'><h2 class='story-headline'>{h['team']['displayName']} vs {a['team']['displayName']}</h2><p>{c['status']['type']['detail']}</p></div>"

                game = {
                    "id": e['id'],
                    "sport": (league or sport).upper(),
                    "dt": datetime.now(), # Simplified for merging
                    "time_str": datetime.fromisoformat(e['date'].replace("Z","")).strftime("%I:%M %p"),
                    "status": status,
                    "clock": c['status']['type']['detail'],
                    "venue": "",
                    "home": { "name": h['team']['displayName'], "score": h.get('score','0'), "logo": h['team'].get('logo','') },
                    "away": { "name": a['team']['displayName'], "score": a.get('score','0'), "logo": a['team'].get('logo','') },
                    "story_html": story
                }
                dashboard.append(game)
        except: continue
    return dashboard

# --- MAIN LOOP ---

def render_dashboard(games):
    # Sort: Live games first
    games.sort(key=lambda x: (x['status'] != 'in', x['sport']))
    
    html_rows = ""
    for g in games:
        badge_color = "#10b981" if g['sport'] == "CRICKET" else "#666"
        status_class = "live" if g['status'] == 'in' else "final"
        
        html_rows += f"""
        <details class="match-card {status_class}">
            <summary class="match-summary">
                <div class="time-col">
                    {g['time_str']}<br>
                    <span style="font-size:0.6em; background:{badge_color}; color:#fff; padding:2px 4px; border-radius:3px;">{g['sport'][:9]}</span>
                </div>
                <div class="score-col">
                    <div class="team-row"><img src="{g['away']['logo']}" class="logo" onerror="this.style.display='none'"> {g['away']['name']} <span class="score">{g['away']['score']}</span></div>
                    <div class="team-row"><img src="{g['home']['logo']}" class="logo" onerror="this.style.display='none'"> {g['home']['name']} <span class="score">{g['home']['score']}</span></div>
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
            .header {{ background: #000; padding: 15px; border-bottom: 1px solid #333; position: sticky; top: 0; z-index: 100; }}
            h1 {{ margin: 0; font-size: 1.2rem; color: #fff; text-transform: uppercase; letter-spacing: 2px; }}
            .container {{ max-width: 650px; margin: 0 auto; padding: 10px; }}
            .match-card {{ background: #1a1a1a; margin-bottom: 12px; border: 1px solid #333; border-radius: 4px; overflow: hidden; }}
            .match-card.live {{ border-left: 5px solid #ef4444; }}
            .match-summary {{ display: flex; padding: 15px; cursor: pointer; align-items: center; background: #1e1e1e; font-family: -apple-system, sans-serif; }}
            .match-summary::-webkit-details-marker {{ display: none; }}
            .time-col {{ width: 60px; font-size: 0.75rem; color: #888; text-align: center; border-right: 1px solid #333; margin-right: 15px; }}
            .score-col {{ flex: 1; }}
            .team-row {{ display: flex; align-items: center; justify-content: space-between; margin: 4px 0; font-size: 1rem; }}
            .logo {{ width: 24px; height: 24px; margin-right: 10px; object-fit: contain; }}
            .score {{ font-weight: 700; }}
            .status-col {{ font-size: 0.7rem; color: #aaa; width: 70px; text-align: right; }}
            .article-content {{ padding: 20px; background: #161616; border-top: 1px solid #333; }}
            .story-headline {{ margin: 0 0 12px; font-size: 1.4rem; color: #fff; }}
        </style>
    </head>
    <body>
        <div class="header"><h1>Clubhouse Wire</h1></div>
        <div class="container">
            {html_rows or "<div style='text-align:center;padding:40px;color:#666;'>No games found.</div>"}
        </div>
    </body>
    </html>
    """
    with open(OUTPUT_HTML_PATH, "w", encoding='utf-8') as f: f.write(html)
    print(f"✅ Dashboard Updated with {len(games)} games.")

if __name__ == "__main__":
    if os.environ.get('CI') == 'true': 
        w = load_whitelist()
        render_dashboard(fetch_espn(w) + fetch_bbc_cricket(w))
    else:
        while True:
            w = load_whitelist()
            render_dashboard(fetch_espn(w) + fetch_bbc_cricket(w))
            time.sleep(REFRESH_RATE_MINUTES * 60)
