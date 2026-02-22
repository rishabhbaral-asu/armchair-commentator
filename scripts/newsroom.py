import requests
import json
from datetime import datetime, timedelta
import pytz
import re
import os

# --- 1. CONFIG & FILES ---
OPENWEATHER_API_KEY = "ac08c1c364001a27b81d418f26e28315"
MST = pytz.timezone('US/Arizona')

def get_whitelist():
    """Pulls teams from whitelist.txt; handles empty or missing file gracefully."""
    if not os.path.exists("scripts/whitelist.txt"):
        return []
    with open("whitelist.txt", "r") as f:
        return [line.strip().lower() for line in f if line.strip()]

# --- 2. THE STORY ENGINE (UNIQUE & DYNAMIC) ---

def get_game_detail(event_id, sport, league):
    """Fetches the deep summary data for a specific event."""
    try:
        url = f"https://site.web.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={event_id}"
        return requests.get(url, timeout=5).json()
    except: return None

def craft_unique_story(event, sport, league):
    status_type = event["status"]["type"]["name"]
    eid = event["id"]
    comp = event["competitions"][0]
    home, away = comp["competitors"][0], comp["competitors"][1]
    
    # Fetch Deep Detail for Unique Stats
    detail = get_game_detail(eid, sport, league)
    
    # 1. THE FINAL RECAP (Editorial first, then Stat-Heavy fallback)
    if status_type == "STATUS_FINAL":
        # Try for professional editorial recap
        articles = detail.get("news", {}).get("articles", []) if detail else []
        if articles:
            return f"<b>{articles[0].get('headline').upper()}</b><br><br>{articles[0].get('description')}"
        
        # Fallback: Stat-driven unique recap
        win = home if home.get("winner") else away
        los = away if home.get("winner") else home
        
        # Pull unique team stats from the detail API
        def find_stat(team_id, stat_name):
            if not detail: return ""
            teams = detail.get("boxscore", {}).get("teams", [])
            for t in teams:
                if str(t["team"]["id"]) == str(team_id):
                    for s in t.get("statistics", []):
                        if s["name"] == stat_name: return s["displayValue"]
            return ""

        # Build a narrative based on sport-specific stats
        if sport == "basketball":
            w_fg = find_stat(win["team"]["id"], "fieldGoalPct")
            w_3pt = find_stat(win["team"]["id"], "threePointFieldGoalPct")
            story = f"<b>{win['team']['displayName'].upper()} SHARP FROM THE FLOOR</b><br><br>"
            story += f"The {win['team']['displayName']} shot a commanding {w_fg}% to outlast {los['team']['displayName']} {win['score']}-{los['score']}. "
            if w_3pt: story += f"The perimeter attack was lethal, converting {w_3pt}% from deep. "
        else:
            story = f"<b>{win['team']['displayName'].upper()} SECURES VICTORY</b><br><br>"
            story += f"In a physical {sport} contest, {win['team']['displayName']} found the edge late to defeat {los['team']['displayName']} {win['score']}-{los['score']}. "
            
        story += f"The win moves {win['team']['shortDisplayName']} into their next phase of the {league.upper()} season."
        return story

    # 2. THE LIVE WIRE (Real-time unique updates)
    if status_type == "STATUS_IN_PROGRESS":
        clock = event['status']['type']['detail']
        prob = detail.get("winprobability", [{}])[-1].get("homeWinPercentage", 0.5) if detail else 0.5
        leader = home if float(home['score']) > float(away['score']) else away
        
        story = f"<b>LIVE FROM {comp.get('venue', {}).get('fullName','').upper()}</b><br><br>"
        story += f"Current Action: {clock}. The {leader['team']['shortDisplayName']} currently hold the momentum. "
        if prob > 0.5: story += f"Win probability trackers currently favor the home side at {round(prob*100)}%."
        return story

    # 3. PRE-GAME PREVIEW (Countdown & Weather)
    time_ms = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST)
    diff = time_ms - datetime.now(MST)
    countdown = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m"
    city = comp.get("venue", {}).get("address", {}).get("city", "Site")
    
    story = f"<b>PREVIEW: {away['team']['shortDisplayName'].upper()} @ {home['team']['shortDisplayName'].upper()}</b><br><br>"
    story += f"<b>T-MINUS: {countdown}</b>. The {away['team']['displayName']} are preparing for a road test in {city}. "
    story += f"Local reports indicate {get_live_weather(city)} conditions for the scheduled start."
    return story

def get_live_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=imperial"
        res = requests.get(url, timeout=5).json()
        return f"{round(res['main']['temp'])}°F"
    except: return "Clear"

# --- 3. DATA FETCHING ---

def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    params = {"limit": "500", "dates": f"{datetime.now(MST).strftime('%Y%m%d')}-{(datetime.now(MST)+timedelta(days=3)).strftime('%Y%m%d')}"}
    if "college" in league: params["groups"] = "50"

    results = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            eid = event["id"]
            comp = event["competitions"][0]
            
            # Match whitelist
            match_found = False
            for t in comp["competitors"]:
                name_blob = f"{t['team'].get('displayName','')} {t['team'].get('shortDisplayName','')} {t['team'].get('name','')}".lower()
                if any(re.search(rf'\b{re.escape(w.lower())}\b', name_blob) for w in whitelist):
                    match_found = True
            
            if match_found and eid not in seen_ids:
                results.append({
                    "id": eid, "iso_date": event["date"], "sport_type": sport,
                    "home_logo": comp["competitors"][0]["team"].get("logo"),
                    "away_logo": comp["competitors"][1]["team"].get("logo"),
                    "home_name": comp["competitors"][0]["team"]["shortDisplayName"],
                    "away_name": comp["competitors"][1]["team"]["shortDisplayName"],
                    "home_score": comp["competitors"][0].get("score", "0"),
                    "away_score": comp["competitors"][1].get("score", "0"),
                    "status_text": event["status"]["type"]["detail"],
                    "story": craft_unique_story(event, sport, league)
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- 4. HTML GENERATION ---

def generate_html(games):
    html = """<!DOCTYPE html><html><head><style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@600&family=Roboto:wght@400;900&display=swap');
    body { background: #0b0d0f; color: #eee; font-family: 'Roboto', sans-serif; padding: 40px; margin: 0; }
    .container { max-width: 900px; margin: auto; }

    /* HOCKEY STYLE (NBC/TOP BAR) */
    .bug-hockey { display: flex; background: #1a1d23; border-top: 4px solid #cc0000; height: 50px; align-items: stretch; margin-top: 40px; }
    .hockey-status { background: #cc0000; color: #fff; padding: 0 15px; display: flex; align-items: center; font-family: 'Oswald'; font-size: 0.8em; }
    .hockey-team { flex: 1; display: flex; align-items: center; padding: 0 15px; font-weight: 900; font-size: 1.1em; text-transform: uppercase; }
    .hockey-score { background: #000; width: 50px; display: flex; align-items: center; justify-content: center; font-size: 1.6em; border-left: 1px solid #333; font-family: 'Oswald'; }

    /* NCAA/OTHER STYLE (ESPN/FLAT) */
    .bug-ncaa { display: flex; background: #fff; color: #111; height: 65px; align-items: stretch; margin-top: 40px; }
    .ncaa-team { flex: 1; display: flex; align-items: center; padding: 0 20px; font-size: 1.4em; font-weight: 900; text-transform: uppercase; }
    .ncaa-score { background: #111; color: #ffc627; width: 80px; display: flex; align-items: center; justify-content: center; font-size: 2.2em; font-weight: 900; font-family: 'Oswald'; }
    .ncaa-status { background: #eee; width: 110px; display: flex; align-items: center; justify-content: center; font-size: 0.8em; font-weight: bold; color: #555; text-align: center; border-left: 1px solid #ddd; }

    .wire-box { background: #fdfdfd; color: #222; padding: 35px; border-radius: 0 0 4px 4px; line-height: 1.7; font-size: 1.1em; margin-bottom: 50px; border-top: 1px solid #eee; }
    </style></head><body><div class="container">
    <h1 style="font-family:'Oswald'; border-left: 5px solid #ffc627; padding-left: 15px;">THE WIRE</h1>"""

    for g in games:
        if g['sport_type'] == "hockey":
            html += f"""<div class="bug-hockey">
                <div class="hockey-status">{g['status_text']}</div>
                <div class="hockey-team">{g['away_name']}</div><div class="hockey-score">{g['away_score']}</div>
                <div class="hockey-team">{g['home_name']}</div><div class="hockey-score">{g['home_score']}</div>
            </div>"""
        else:
            html += f"""<div class="bug-ncaa">
                <div class="ncaa-team">{g['away_name']}</div><div class="ncaa-score">{g['away_score']}</div>
                <div class="ncaa-team">{g['home_name']}</div><div class="ncaa-score">{g['home_score']}</div>
                <div class="ncaa-status">{g['status_text']}</div>
            </div>"""
        html += f'<div class="wire-box">{g["story"]}</div>'

    html += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "mens-college-basketball"), 
        ("hockey", "mens-college-hockey"), 
        ("soccer", "eng.1")
    ]
    for s, l in leagues: all_games.extend(get_espn_data(s, l, whitelist, seen))
    all_games.sort(key=lambda x: x['iso_date'])
    generate_html(all_games)

if __name__ == "__main__": main()
