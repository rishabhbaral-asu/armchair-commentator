import requests
import json
from datetime import datetime, timedelta
import pytz
import re

# --- 1. CONFIG ---
OPENWEATHER_API_KEY = "ac08c1c364001a27b81d418f26e28315"
MST = pytz.timezone('US/Arizona')

def get_whitelist():
    return ["arizona state", "asu", "maryland", "indiana", "illinois", "iowa", "ucla", "usc", "leeds united", "texas", "louisiana"]

# --- 2. THE STORY ENGINE (AP WIRE DEPTH) ---

def get_game_recap(event_id, sport, league):
    """Fetches the actual professional editorial recap from ESPN."""
    try:
        url = f"https://site.web.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={event_id}"
        data = requests.get(url, timeout=5).json()
        articles = data.get("news", {}).get("articles", [])
        if articles:
            return f"<b>{articles[0].get('headline').upper()}</b><br><br>{articles[0].get('description')}"
    except: pass
    return None

def get_up_next(team_id, sport, league):
    try:
        for stype in [2, 3]:
            url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/schedule?seasontype={stype}"
            data = requests.get(url, timeout=5).json()
            future = [e for e in data.get("events", []) if e["status"]["type"]["name"] == "STATUS_SCHEDULED"]
            if future:
                nxt = future[0]
                dt = datetime.strptime(nxt["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST).strftime("%a, %b %d")
                opp = next((t["team"]["displayName"] for t in nxt["competitions"][0]["competitors"] if str(t["team"]["id"]) != str(team_id)), "TBD")
                return f"vs {opp} ({dt})"
    except: pass
    return "TBD"

def craft_dynamic_story(event, sport, league):
    status_type = event["status"]["type"]["name"]
    eid = event["id"]
    comp = event["competitions"][0]
    home, away = comp["competitors"][0], comp["competitors"][1]
    
    # 1. Try to get professional AP-style recap if game is over
    if status_type == "STATUS_FINAL":
        recap = get_game_recap(eid, sport, league)
        if recap: return recap

    # 2. Manual AP-style generation if no recap exists
    city = comp.get("venue", {}).get("address", {}).get("city", "Unknown").upper()
    state = comp.get("venue", {}).get("address", {}).get("state", "ST")
    venue = comp.get("venue", {}).get("fullName", "the arena")
    dateline = f"<b>{city}, {state} -- </b>"

    if status_type == "STATUS_FINAL":
        win = home if home.get("winner") else away
        los = away if home.get("winner") else home
        story = f"{dateline} The {win['team']['displayName']} used a second-half surge to dismantle {los['team']['displayName']} "
        story += f"in a {win['score']}-{los['score']} victory at {venue}.<br><br>"
        story += f"<b>UP NEXT:</b> {home['team']['shortDisplayName']} {get_up_next(home['team']['id'], sport, league)} | {away['team']['shortDisplayName']} {get_up_next(away['team']['id'], sport, league)}"
        return story

    if status_type == "STATUS_IN_PROGRESS":
        clock = event['status']['type']['detail']
        return f"{dateline} The {away['team']['shortDisplayName']} and {home['team']['shortDisplayName']} are currently locked in a physical {sport} battle at {venue}. Current clock: {clock}."

    # Pre-game Preview
    time_ms = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST)
    diff = time_ms - datetime.now(MST)
    countdown = f"{diff.days}d {diff.seconds//3600}h {(diff.seconds//60)%60}m"
    
    return f"{dateline} <b>COUNTDOWN: {countdown} TO KICKOFF.</b><br>The {away['team']['displayName']} prepare to face {home['team']['displayName']} at {venue}. Weather is currently {get_live_weather(city)}."

def get_live_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=imperial"
        res = requests.get(url, timeout=5).json()
        return f"{round(res['main']['temp'])}°F"
    except: return "Clear"

# --- 3. THE DATA FETCH ---

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
            
            match_found = False
            for t in comp["competitors"]:
                name_blob = f"{t['team'].get('displayName','')} {t['team'].get('shortDisplayName','')} {t['team'].get('name','')}".lower()
                if any(re.search(rf'\b{re.escape(w.lower())}\b', name_blob) for w in whitelist):
                    match_found = True
            
            if match_found and eid not in seen_ids:
                results.append({
                    "id": eid, "iso_date": event["date"], "sport_type": sport,
                    "headline": f"{event.get('name')}",
                    "home_logo": comp["competitors"][0]["team"].get("logo"),
                    "away_logo": comp["competitors"][1]["team"].get("logo"),
                    "home_name": comp["competitors"][0]["team"]["shortDisplayName"],
                    "away_name": comp["competitors"][1]["team"]["shortDisplayName"],
                    "home_score": comp["competitors"][0].get("score", "0"),
                    "away_score": comp["competitors"][1].get("score", "0"),
                    "status_text": event["status"]["type"]["detail"],
                    "status_type": event["status"]["type"]["name"],
                    "story": craft_dynamic_story(event, sport, league)
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- 4. HTML GENERATION ---

def generate_html(games):
    html = """<!DOCTYPE html><html><head><style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@600&family=Roboto:wght@400;900&display=swap');
    body { background: #0b0d0f; color: #eee; font-family: 'Roboto', sans-serif; padding: 40px; }
    .container { max-width: 900px; margin: auto; }

    /* HOCKEY STYLE (NBC) */
    .bug-hockey { display: flex; background: #1a1d23; border-top: 4px solid #cc0000; height: 55px; align-items: stretch; margin-top: 40px; box-shadow: 0 5px 15px rgba(0,0,0,0.5); }
    .hockey-status { background: #cc0000; color: #fff; padding: 0 15px; display: flex; align-items: center; font-family: 'Oswald'; font-size: 0.9em; }
    .hockey-team { flex: 1; display: flex; align-items: center; padding: 0 20px; font-weight: 900; font-size: 1.2em; text-transform: uppercase; }
    .hockey-score { background: #000; width: 60px; display: flex; align-items: center; justify-content: center; font-size: 1.8em; font-weight: 900; border-left: 1px solid #333; }

    /* NCAA/OTHER STYLE (ESPN) */
    .bug-ncaa { display: flex; background: #fff; color: #111; height: 70px; align-items: stretch; margin-top: 40px; }
    .ncaa-team { flex: 1; display: flex; align-items: center; padding: 0 20px; font-size: 1.5em; font-weight: 900; text-transform: uppercase; border-right: 1px solid #ddd; }
    .ncaa-score { background: #111; color: #ffc627; width: 80px; display: flex; align-items: center; justify-content: center; font-size: 2.5em; font-weight: 900; font-family: 'Oswald'; }
    .ncaa-status { background: #eee; width: 120px; display: flex; align-items: center; justify-content: center; font-size: 0.8em; font-weight: bold; color: #555; text-align: center; }

    .wire-box { background: #fdfdfd; color: #222; padding: 35px; border-radius: 0 0 4px 4px; line-height: 1.8; font-size: 1.1em; border-top: 1px solid #ddd; margin-bottom: 50px; }
    </style></head><body><div class="container">"""

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
    leagues = [("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey"), ("soccer", "eng.1")]
    for s, l in leagues: all_games.extend(get_espn_data(s, l, whitelist, seen))
    all_games.sort(key=lambda x: x['iso_date'])
    generate_html(all_games)

if __name__ == "__main__": main()
