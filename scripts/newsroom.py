import requests
import json
from datetime import datetime, timedelta
import pytz
import re

# --- 1. CONFIG ---
OPENWEATHER_API_KEY = "ac08c1c364001a27b81d418f26e28315"
MST = pytz.timezone('US/Arizona')

def get_whitelist():
    # Adjusted to ensure whole-word matching logic handles these correctly
    return [
        "arizona state", "asu", "maryland", "indiana", "illinois", 
        "iowa", "ucla", "usc", "leeds united", "texas", "hoosiers", 
        "illini", "sun devils", "terrapins"
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
    try:
        for stype in [2, 3]: # Regular and Postseason
            url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/schedule?seasontype={stype}"
            data = requests.get(url, timeout=5).json()
            future = [e for e in data.get("events", []) if e["status"]["type"]["name"] == "STATUS_SCHEDULED"]
            if future:
                nxt = future[0]
                dt = datetime.strptime(nxt["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST).strftime("%a, %b %d")
                opp = "TBD"
                for t in nxt["competitions"][0]["competitors"]:
                    if str(t["team"]["id"]) != str(team_id): opp = t["team"]["displayName"]
                return f"vs {opp} ({dt})"
    except: pass
    return "to return to action soon"

def craft_dynamic_story(event, sport, league):
    status_type = event["status"]["type"]["name"]
    comp = event["competitions"][0]
    home, away = comp["competitors"][0], comp["competitors"][1]
    
    city = comp.get("venue", {}).get("address", {}).get("city", "Unknown").upper()
    state = comp.get("venue", {}).get("address", {}).get("state", "ST")
    venue = comp.get("venue", {}).get("fullName", "the arena")
    
    # Deep Data Helpers
    def get_lead_athlete(team):
        try: return f"{team['leaders'][0]['leaders'][0]['athlete']['displayName']} ({team['leaders'][0]['leaders'][0]['displayValue']})"
        except: return None

    h_star, a_star = get_lead_athlete(home), get_lead_athlete(away)
    h_rec = next((r["summary"] for r in home.get("records", []) if r["type"] == "total"), "0-0")
    a_rec = next((r["summary"] for r in away.get("records", []) if r["type"] == "total"), "0-0")
    
    dateline = f"<b>{city}, {state} -- </b>"
    surface = "pitch" if sport == "soccer" else "ice" if sport == "hockey" else "hardwood"

    # --- FINAL RECAP ---
    if status_type == "STATUS_FINAL":
        win = home if home.get("winner") else away
        los = away if home.get("winner") else home
        w_star = get_lead_athlete(win)
        
        story = f"{dateline} {w_star if w_star else win['team']['displayName']} took control late as {win['team']['displayName']} "
        story += f"secured a {win['score']}-{los['score']} victory over {los['team']['displayName']} at {venue}.<br><br>"
        
        story += f"The {win['team']['shortDisplayName']} ({h_rec if win==home else a_rec}) dominated the {surface}, finding rhythm in the second half "
        story += f"to pull away from a resilient {los['team']['shortDisplayName']} squad. "
        
        if get_lead_athlete(los):
            story += f"{los['team']['shortDisplayName']} was paced by {get_lead_athlete(los)} in the losing effort. "
        
        story += f"The result marks a pivotal moment for {win['team']['shortDisplayName']} as they look to climb the {league.upper()} standings.<br><br>"
        story += f"<b>UP NEXT:</b> {home['team']['shortDisplayName']} is scheduled {get_up_next(home['team']['id'], sport, league)}, while {away['team']['shortDisplayName']} will prepare {get_up_next(away['team']['id'], sport, league)}."
        return story

    # --- LIVE UPDATE ---
    if status_type == "STATUS_IN_PROGRESS":
        clock = event['status']['type']['detail']
        leading = home if int(home['score']) > int(away['score']) else away
        diff = abs(int(home['score']) - int(away['score']))
        
        story = f"{dateline} The {leading['team']['shortDisplayName']} are currently maintaining a {diff}-point cushion over {away['team']['shortDisplayName'] if leading==home else home['team']['shortDisplayName']} "
        story += f"with {clock} remaining on the clock at {venue}.<br><br>"
        story += f"<b>Key Matchup:</b> {h_star if h_star else 'The home starters'} and {a_star if a_star else 'the visitors'} are trading blows in a physical {sport} contest. "
        story += f"The {home['team']['shortDisplayName']} are fighting to protect a {h_rec} home record."
        return story

    # --- PREVIEW ---
    time_ms = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST)
    return f"{dateline} The {away['team']['displayName']} ({a_rec}) travel to {city} for a high-stakes {league.upper()} matchup against {home['team']['displayName']} ({h_rec}). " \
           f"Atmospheric conditions at {venue} are currently {get_live_weather(city)}. Kickoff is scheduled for {time_ms.strftime('%I:%M %p')} MST."

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
                    "story": craft_dynamic_story(event, sport, league)
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- 4. HTML GENERATION ---

def generate_html(games):
    now_str = datetime.now(MST).strftime("%B %d, %Y • %I:%M %p MST")
    html = f"""<!DOCTYPE html><html><head><style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;700&family=Roboto:wght@400;900&display=swap');
    body {{ background: #0e1114; color: #fff; font-family: 'Roboto', sans-serif; padding: 40px; margin: 0; }}
    .container {{ max-width: 900px; margin: auto; }}
    
    /* SCOREBUG DESIGN */
    .scorebug {{ 
        display: flex; background: #1a1d23; border-bottom: 4px solid #ffc627; 
        box-shadow: 0 10px 20px rgba(0,0,0,0.5); overflow: hidden; height: 75px; align-items: stretch;
        margin-top: 40px;
    }}
    .sb-status {{ background: #000; color: #ffc627; padding: 0 20px; display: flex; align-items: center; font-family: 'Oswald'; font-size: 1.1em; text-transform: uppercase; min-width: 130px; justify-content: center; letter-spacing: 1px; }}
    .sb-team {{ display: flex; align-items: center; padding: 0 25px; flex: 1; gap: 15px; font-weight: 900; font-size: 1.5em; text-transform: uppercase; letter-spacing: -0.5px; }}
    .sb-team img {{ height: 45px; width: 45px; object-fit: contain; }}
    .sb-score {{ background: #2a2e35; width: 90px; display: flex; align-items: center; justify-content: center; font-size: 2.4em; font-weight: 900; border-left: 1px solid #3d424a; font-family: 'Oswald'; }}
    .sb-vs {{ background: #111; width: 45px; display: flex; align-items: center; justify-content: center; font-size: 0.8em; color: #555; font-weight: bold; }}

    /* WIRE DESIGN */
    .wire-container {{ background: #fdfdfd; color: #111; padding: 40px; margin-bottom: 20px; border-radius: 0 0 4px 4px; line-height: 1.8; font-size: 1.15em; box-shadow: 0 5px 15px rgba(0,0,0,0.3); }}
    .wire-header {{ font-family: 'Oswald'; text-transform: uppercase; border-bottom: 3px solid #111; margin-bottom: 20px; display: flex; justify-content: space-between; font-size: 0.9em; letter-spacing: 1px; }}
    .wire-footer {{ text-align: center; color: #888; font-size: 0.8em; margin-top: 50px; text-transform: uppercase; letter-spacing: 2px; }}
    </style></head><body><div class="container">
    <div style="border-left: 8px solid #ffc627; padding-left: 20px; margin-bottom: 40px;">
        <h1 style="margin:0; font-size: 3em; font-family: 'Oswald'; font-weight: 700;">THE WIRE <span style="color: #ffc627;">LIVE</span></h1>
        <p style="margin:0; color: #888; font-weight: bold;">{now_str}</p>
    </div>
    """
    for g in games:
        html += f"""
        <div class="scorebug">
            <div class="sb-status">{g['status_text']}</div>
            <div class="sb-team" style="justify-content: flex-end;">{g['away_name']} <img src="{g['away_logo']}"></div>
            <div class="sb-score">{g['away_score']}</div>
            <div class="sb-vs">VS</div>
            <div class="sb-score">{g['home_score']}</div>
            <div class="sb-team"><img src="{g['home_logo']}"> {g['home_name']}</div>
        </div>
        <div class="wire-container">
            <div class="wire-header"><span>ASSOCIATED PRESS BUREAU</span><span>{g['headline'].split(' ')[0]} UPDATE</span></div>
            {g['story']}
        </div>"""
    
    html += """<div class="wire-footer">End of Transmission • Powered by ESPN API</div></div></body></html>"""
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
    print(f"Update Success: {len(all_games)} matches identified.")

if __name__ == "__main__": main()
