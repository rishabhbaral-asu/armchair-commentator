import requests
import json
from datetime import datetime, timedelta
import pytz
import re

# --- 1. CONFIG ---
OPENWEATHER_API_KEY = "ac08c1c364001a27b81d418f26e28315"
MST = pytz.timezone('US/Arizona')

def get_whitelist():
    return [
        "san francisco 49ers", "ac milan", "angel city", "anaheim angels", "arizona state", "asu", 
        "athletics", "atletico madrid", "austin fc", "bakersfield", "california", "cal poly", 
        "capitals", "arizona cardinals", "cal baptist", "la chargers", "chelsea", "la clippers", 
        "commanders", "coventry city", "dallas cowboys", "crystal palace", "arizona diamondbacks", 
        "dc united", "fc dallas", "houston dash", "la dodgers", "anaheim ducks", "east texas a&m", 
        "fresno state", "fulham", "fullerton", "san francisco giants", "new york giants", "gcu", 
        "houston dynamo", "juventus", "sacramento kings", "la kings", "la galaxy", "lafc", "india", 
        "la lakers", "united states", "lbsu", "leeds united", "leverkusen", "lyon", "m'gladbach", 
        "mainz", "marseille", "maryland", "dallas mavericks", "phoenix mercury", "phoenix suns", 
        "inter miami", "as monaco", "mystics", "washington nationals", "north texas", "norwich", 
        "nott'm forest", "orioles", "san diego padres", "parma", "psv", "la rams", "texas rangers", 
        "baltimore ravens", "saint mary's", "san diego", "san jose", "santa clara", "san jose sharks", 
        "la sparks", "washington spirit", "st. pauli", "dallas stars", "texas", "tolouse", "uc davis", 
        "uc irvine", "ucla", "usc", "uc riverside", "uc san diego", "ucsb", "utep", "valkyries", 
        "venezia", "golden state warriors", "san diego wave", "dallas wings", "wizards", "wrexham", 
        "chicago red stars", "argentina", "brazil", "spain", "france", "germany", "belgium",
        "indiana", "illinois", "iowa", "hoosiers", "illini"
    ]

# --- 2. ENGINES ---
def get_live_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=imperial"
        res = requests.get(url, timeout=5).json()
        if res.get("cod") == 200:
            return f"{round(res['main']['temp'])}°F and {res['weather'][0]['description']}"
    except: pass
    return "Variable Conditions"

def get_up_next(team_id, sport, league):
    """Aggressively finds the next game by checking multiple season types."""
    try:
        # Check Regular Season (2) and Postseason (3)
        for stype in [2, 3]:
            url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/schedule?seasontype={stype}"
            data = requests.get(url, timeout=5).json()
            events = data.get("events", [])
            # Find first game that is strictly in the future
            future = [e for e in events if e["status"]["type"]["name"] == "STATUS_SCHEDULED"]
            if future:
                nxt = future[0]
                dt = datetime.strptime(nxt["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST).strftime("%a, %b %d")
                # Identify opponent
                opp = "TBD"
                for t in nxt["competitions"][0]["competitors"]:
                    if str(t["team"]["id"]) != str(team_id):
                        opp = t["team"]["displayName"]
                return f"vs {opp} ({dt})"
    except: pass
    return "TBD"

def craft_dynamic_story(event, sport, league):
    status_type = event["status"]["type"]["name"]
    comp = event["competitions"][0]
    home, away = comp["competitors"][0], comp["competitors"][1]
    
    city = comp.get("venue", {}).get("address", {}).get("city", "Unknown").upper()
    state = comp.get("venue", {}).get("address", {}).get("state", "ST")
    venue = comp.get("venue", {}).get("fullName", "the arena")
    
    # Records
    h_rec = next((r["summary"] for r in home.get("records", []) if r["type"] == "total"), "0-0")
    a_rec = next((r["summary"] for r in away.get("records", []) if r["type"] == "total"), "0-0")

    # Sport vocab
    surface = "pitch" if sport == "soccer" else "ice" if sport == "hockey" else "hardwood"
    dateline = f"<b>{city}, {state} -- </b>"

    # --- FINAL RECAP ---
    if status_type == "STATUS_FINAL":
        win = home if home.get("winner") else away
        los = away if home.get("winner") else home
        story = f"{dateline} {win['team']['displayName']} sharpened their form on the {surface} Saturday, "
        story += f"securing a vital {win['score']}-{los['score']} victory over {los['team']['displayName']} at {venue}.<br><br>"
        story += f"The win moves {win['team']['shortDisplayName']} to {h_rec if win==home else a_rec} on the season. "
        
        # Up Next
        story += f"<div style='margin-top:12px; font-size:0.85em; color:#888; border-top:1px solid #443; padding-top:8px;'>"
        story += f"<b>UP NEXT:</b> {home['team']['shortDisplayName']} {get_up_next(home['team']['id'], sport, league)} | "
        story += f"{away['team']['shortDisplayName']} {get_up_next(away['team']['id'], sport, league)}</div>"
        return story

    # --- LIVE UPDATE ---
    if status_type == "STATUS_IN_PROGRESS":
        clock = event['status']['type']['detail']
        return f"{dateline} Action is currently in {clock} at {venue} where the {away['team']['shortDisplayName']} and {home['team']['shortDisplayName']} are locked in a battle. " \
               f"The {home['team']['shortDisplayName']} are looking to protect their home {surface} and improve their {h_rec} record."

    # --- PREGAME PREVIEW ---
    time_ms = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST)
    return f"{dateline} The {away['team']['displayName']} ({a_rec}) travel to face {home['team']['displayName']} ({h_rec}) at {venue}. " \
           f"Local weather in {city} is {get_live_weather(city)}. Kickoff is set for {time_ms.strftime('%I:%M %p')} MST."

# --- 3. DATA FETCH ---
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
            
            # Logic: Whitelist match with Whole Word check (India vs Indiana fix)
            match_found = False
            for t in comp["competitors"]:
                name_blob = f"{t['team'].get('displayName','')} {t['team'].get('shortDisplayName','')} {t['team'].get('name','')}".lower()
                if any(re.search(rf'\b{re.escape(w.lower())}\b', name_blob) for w in whitelist):
                    match_found = True
            
            if match_found and eid not in seen_ids:
                icons = {"basketball": "🏀", "hockey": "🏒", "baseball": "⚾", "football": "🏈", "soccer": "⚽"}
                results.append({
                    "id": eid, "iso_date": event["date"],
                    "headline": f"{icons.get(sport, '🏆')} {event.get('name')}",
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

def generate_html(games):
    now_str = datetime.now(MST).strftime("%B %d, %Y • %I:%M %p MST")
    html = f"""<!DOCTYPE html><html><head><style>
    :root {{ --bg: #0b0d0f; --card: #161a1e; --accent: #ffc627; --text: #eee; }}
    body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); color: var(--text); padding: 30px; line-height:1.5; }}
    .container {{ max-width: 800px; margin: auto; }}
    .card {{ background: var(--card); border-radius: 8px; margin-bottom: 25px; border-left: 5px solid var(--accent); padding: 0; overflow: hidden; }}
    .card-header {{ background: #222; padding: 10px 20px; font-size: 0.75em; text-transform: uppercase; color: #888; }}
    .score-area {{ display: flex; align-items: center; justify-content: space-between; padding: 20px 40px; background: #1c2126; }}
    .team-box {{ display: flex; align-items: center; gap: 15px; font-size: 1.2em; font-weight: bold; }}
    .score-box {{ font-size: 2.5em; font-weight: 900; color: var(--accent); }}
    .story-box {{ padding: 25px; color: #ccc; border-top: 1px solid #2d3238; }}
    </style></head><body><div class="container">
    <h1 style="margin-bottom:5px;">NEWSROOM WIRE</h1><p style="color:#888; margin-top:0;">{now_str}</p>
    """
    for g in games:
        html += f"""<div class="card">
            <div class="card-header">{g['headline']} — {g['status_text']}</div>
            <div class="score-area">
                <div class="team-box"><img src="{g['away_logo']}" height="40">{g['away_name']}</div>
                <div class="score-box">{g['away_score']} - {g['home_score']}</div>
                <div class="team-box">{g['home_name']}<img src="{g['home_logo']}" height="40"></div>
            </div>
            <div class="story-box">{g['story']}</div>
        </div>"""
    html += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "mens-college-basketball"), ("hockey", "mens-college-hockey"),
        ("soccer", "eng.1"), ("basketball", "nba"), ("football", "nfl")
    ]
    for s, l in leagues: all_games.extend(get_espn_data(s, l, whitelist, seen))
    all_games.sort(key=lambda x: x['iso_date'])
    generate_html(all_games)

if __name__ == "__main__": main()
