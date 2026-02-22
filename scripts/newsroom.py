import requests
import json
from datetime import datetime, timedelta
import pytz
import re
import os

# --- 1. CONFIG & WHITELIST ---
MST = pytz.timezone('US/Arizona')
OPENWEATHER_API_KEY = "ac08c1c364001a27b81d418f26e28315"

def get_whitelist():
    if not os.path.exists("scripts/whitelist.txt"):
        return []
    with open("scripts/whitelist.txt", "r") as f:
        return [line.strip().lower() for line in f if line.strip()]

# --- 2. STORY ENGINE (GAME-MATCHED) ---

def get_game_detail(event_id, sport, league):
    try:
        url = f"https://site.web.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={event_id}"
        return requests.get(url, timeout=5).json()
    except: return None

def craft_unique_story(event, sport, league):
    status_type = event["status"]["type"]["name"]
    eid = event["id"]
    detail = get_game_detail(eid, sport, league)
    comp = event["competitions"][0]
    home, away = comp["competitors"][0], comp["competitors"][1]
    
    # Priority 1: Actual News Recap
    articles = detail.get("news", {}).get("articles", []) if detail else []
    if articles:
        headline = articles[0].get('headline', '').upper()
        description = articles[0].get('description', '')
        return f"<b>{headline}</b><br><br>{description}"

    # Priority 2: Stat-Heavy Fallback
    city = comp.get("venue", {}).get("address", {}).get("city", "Unknown").upper()
    venue = comp.get("venue", {}).get("fullName", "the arena")
    
    if status_type == "STATUS_FINAL":
        win = home if home.get("winner") else away
        los = away if home.get("winner") else home
        return f"<b>FINAL FROM {city}</b><br><br>The {win['team']['displayName']} secured a victory at {venue} tonight, defeating the {los['team']['displayName']} {win['score']}-{los['score']}."

    if status_type == "STATUS_IN_PROGRESS":
        return f"<b>LIVE UPDATE</b><br><br>Action is currently underway at {venue}. Both teams are fighting for position in the {league.upper()} standings."

    # Pre-game Preview with Countdown
    time_ms = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST)
    diff = time_ms - datetime.now(MST)
    countdown = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m"
    return f"<b>PREVIEW: {away['team']['shortDisplayName'].upper()} @ {home['team']['shortDisplayName'].upper()}</b><br><br><b>T-MINUS {countdown}</b>. Game time is set for {time_ms.strftime('%I:%M %p')} MST at {venue} in {city}."

# --- 3. DATA FETCHING ---

def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    today = datetime.now(MST).strftime('%Y%m%d')
    params = {"limit": "100", "dates": f"{today}-{(datetime.now(MST)+timedelta(days=2)).strftime('%Y%m%d')}"}
    if "college" in league: params["groups"] = "50"

    results = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            eid = event["id"]
            comp = event["competitions"][0]
            
            match = False
            for t in comp["competitors"]:
                name_blob = f"{t['team'].get('displayName','')} {t['team'].get('shortDisplayName','')} {t['team'].get('name','')}".lower()
                if any(re.search(rf'\b{re.escape(w)}\b', name_blob) for w in whitelist):
                    match = True
            
            if match and eid not in seen_ids:
                results.append({
                    "id": eid, "iso_date": event["date"], "sport_type": sport,
                    "home_name": comp["competitors"][0]["team"]["shortDisplayName"],
                    "away_name": comp["competitors"][1]["team"]["shortDisplayName"],
                    "home_logo": comp["competitors"][0]["team"].get("logo"),
                    "away_logo": comp["competitors"][1]["team"].get("logo"),
                    "home_score": comp["competitors"][0].get("score", "0"),
                    "away_score": comp["competitors"][1].get("score", "0"),
                    "status_text": event["status"]["type"]["detail"],
                    "story": craft_unique_story(event, sport, league)
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- 4. EXACT UI REPLICATION WITH LOGOS ---

def generate_html(games):
    html = """<!DOCTYPE html><html><head><style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@600&family=Roboto:wght@400;900&display=swap');
    body { background: #0b0d0f; color: #eee; font-family: 'Roboto', sans-serif; padding: 40px; margin: 0; }
    .container { max-width: 950px; margin: auto; }

    /* EXACT NBC NHL STYLE (Red Bar) */
    .bug-hockey { display: flex; background: #1a1d23; border-top: 4px solid #cc0000; height: 50px; align-items: stretch; margin-top: 40px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
    .hockey-status { background: #cc0000; color: #fff; padding: 0 15px; display: flex; align-items: center; font-family: 'Oswald'; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }
    .hockey-team { flex: 1; display: flex; align-items: center; padding: 0 15px; font-weight: 900; font-size: 1.1em; text-transform: uppercase; border-right: 1px solid #333; gap: 10px; }
    .hockey-team img { height: 30px; width: 30px; object-fit: contain; }
    .hockey-score { background: #000; width: 60px; display: flex; align-items: center; justify-content: center; font-size: 1.6em; font-family: 'Oswald'; }

    /* EXACT ESPN NCAA STYLE (High Contrast Yellow) */
    .bug-ncaa { display: flex; background: #fff; color: #111; height: 75px; align-items: stretch; margin-top: 40px; border-radius: 4px 4px 0 0; }
    .ncaa-team { flex: 1; display: flex; align-items: center; padding: 0 20px; font-size: 1.5em; font-weight: 900; text-transform: uppercase; gap: 12px; }
    .ncaa-team img { height: 45px; width: 45px; object-fit: contain; }
    .ncaa-score { background: #111; color: #ffc627; width: 95px; display: flex; align-items: center; justify-content: center; font-size: 2.5em; font-weight: 900; font-family: 'Oswald'; }
    .ncaa-status { background: #eee; width: 130px; display: flex; align-items: center; justify-content: center; font-size: 0.9em; font-weight: bold; color: #555; text-align: center; border-left: 1px solid #ddd; text-transform: uppercase; }

    .wire-box { background: #fdfdfd; color: #222; padding: 35px; border-radius: 0 0 4px 4px; line-height: 1.7; font-size: 1.1em; margin-bottom: 50px; border-top: 1px solid #eee; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
    </style></head><body><div class="container">
    <h1 style="font-family:'Oswald'; border-left: 6px solid #ffc627; padding-left: 20px; letter-spacing: 2px; font-size: 3em;">THE WIRE</h1>"""

    for g in games:
        if g['sport_type'] == "hockey":
            html += f"""<div class="bug-hockey">
                <div class="hockey-status">{g['status_text']}</div>
                <div class="hockey-team"><img src="{g['away_logo']}"> {g['away_name']}</div><div class="hockey-score">{g['away_score']}</div>
                <div class="hockey-team"><img src="{g['home_logo']}"> {g['home_name']}</div><div class="hockey-score">{g['home_score']}</div>
            </div>"""
        else:
            html += f"""<div class="bug-ncaa">
                <div class="ncaa-team"><img src="{g['away_logo']}"> {g['away_name']}</div><div class="ncaa-score">{g['away_score']}</div>
                <div class="ncaa-team"><img src="{g['home_logo']}"> {g['home_name']}</div><div class="ncaa-score">{g['home_score']}</div>
                <div class="ncaa-status">{g['status_text']}</div>
            </div>"""
        html += f'<div class="wire-box">{g["story"]}</div>'

    html += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey"), ("soccer", "eng.1")]
    for s, l in leagues: all_games.extend(get_espn_data(s, l, whitelist, seen))
    all_games.sort(key=lambda x: x['iso_date'])
    generate_html(all_games)

if __name__ == "__main__": main()
