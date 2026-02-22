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
        url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/schedule"
        data = requests.get(url, timeout=5).json()
        future = [e for e in data.get("events", []) if e["status"]["type"]["name"] == "STATUS_SCHEDULED"]
        if future:
            nxt = future[0]
            dt = datetime.strptime(nxt["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc).astimezone(MST).strftime("%a, %b %d")
            opp = next((t["team"]["displayName"] for t in nxt["competitions"][0]["competitors"] if t["team"]["id"] != team_id), "TBD")
            return f"vs {opp} ({dt})"
    except: pass
    return "Check Schedule"

def craft_dynamic_story(event, sport, league):
    status_type = event["status"]["type"]["name"]
    comp = event["competitions"][0]
    home, away = comp["competitors"][0], comp["competitors"][1]
    
    # Metadata
    city = comp.get("venue", {}).get("address", {}).get("city", "Unknown").upper()
    state = comp.get("venue", {}).get("address", {}).get("state", "ST")
    venue = comp.get("venue", {}).get("fullName", "the arena")
    
    # Leaders
    def get_lead(c):
        try: return f"{c['leaders'][0]['leaders'][0]['athlete']['displayName']} ({c['leaders'][0]['leaders'][0]['displayValue']})"
        except: return None

    h_lead, a_lead = get_lead(home), get_lead(away)
    h_rec = next((r["summary"] for r in home.get("records", []) if r["type"] == "total"), "0-0")
    a_rec = next((r["summary"] for r in away.get("records", []) if r["type"] == "total"), "0-0")

    # Dateline
    dateline = f"{city}, {state} -- "

    if status_type == "STATUS_FINAL":
        win = home if home.get("winner") else away
        los = away if home.get("winner") else home
        w_lead = get_lead(win)
        
        story = f"<b>{dateline}</b> {w_lead if w_lead else win['team']['displayName']} sparked the offense as {win['team']['displayName']} "
        story += f"dropped {los['team']['displayName']} {win['score']}-{los['score']} at {venue}.<br><br>"
        story += f"The win moves {win['team']['shortDisplayName']} to {h_rec if win==home else a_rec} on the season. "
        
        # Up Next Section
        story += f"<div style='margin-top:10px; font-size:0.9em; color:#888; border-top:1px solid #333; padding-top:8px;'>"
        story += f"<b>UP NEXT:</b> {home['team']['shortDisplayName']} {get_up_next(home['team']['id'], sport, league)} | "
        story += f"{away['team']['shortDisplayName']} {get_up_next(away['team']['id'], sport, league)}</div>"
        return story

    if status_type == "STATUS_IN_PROGRESS":
        return f"<b>{dateline}</b> Currently in {event['status']['type']['detail']}, the {away['team']['shortDisplayName']} and {home['team']['shortDisplayName']} are locked in a battle. {a_lead if a_lead else ''} has been the story for the visitors in {city}."

    return f"<b>{dateline}</b> The {away['team']['displayName']} ({a_rec}) visit {home['team']['displayName']} ({h_rec}) at {venue}. Kickoff/Tip-off is set for {city} local time."

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
            
            # Logic: Match whole words only to avoid India/Indiana mixups
            match_found = False
            for t in comp["competitors"]:
                names = [t["team"].get("displayName", "").lower(), t["team"].get("shortDisplayName", "").lower(), t["team"].get("name", "").lower()]
                for n in names:
                    for w in whitelist:
                        if re.search(rf'\b{re.escape(w.lower())}\b', n):
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

# --- 4. HTML GENERATION ---
def generate_html(games):
    now_dt = datetime.now(MST)
    html = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><style>
    :root {{ --bg: #0b0d0f; --card: #161a1e; --accent: #ffc627; --text: #eee; --dim: #888; }}
    body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 40px; }}
    .container {{ max-width: 850px; margin: auto; }}
    .card {{ background: var(--card); border-radius: 8px; margin-bottom: 25px; border-left: 5px solid var(--accent); overflow: hidden; }}
    .card-header {{ background: #222; padding: 10px 20px; font-size: 0.8em; color: var(--dim); border-bottom: 1px solid #333; }}
    .scoreboard {{ display: flex; align-items: center; padding: 20px; background: #1c2126; }}
    .team {{ display: flex; align-items: center; width: 45%; }}
    .team img {{ height: 45px; margin: 0 15px; }}
    .score {{ width: 10%; text-align: center; font-size: 2em; font-weight: 900; color: var(--accent); }}
    .story {{ padding: 25px; line-height: 1.6; color: #ccc; }}
    </style></head><body><div class="container">
    <h1 style="border-bottom: 2px solid var(--accent); padding-bottom:10px;">NEWSROOM WIRE <span style="font-size:0.4em; color:var(--dim); float:right;">{now_dt.strftime('%I:%M %p MST')}</span></h1>
    """
    for g in games:
        html += f"""
        <div class="card">
            <div class="card-header">{g['headline']} — {g['status_text']}</div>
            <div class="scoreboard">
                <div class="team" style="justify-content: flex-end;">{g['away_name']}<img src="{g['away_logo']}"></div>
                <div class="score">{g['away_score']}-{g['home_score']}</div>
                <div class="team"><img src="{g['home_logo']}">{g['home_name']}</div>
            </div>
            <div class="story">{g['story']}</div>
        </div>"""
    html += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "mens-college-basketball"), ("basketball", "womens-college-basketball"),
        ("basketball", "nba"), ("hockey", "nhl"), ("hockey", "mens-college-hockey"),
        ("baseball", "mlb"), ("football", "nfl"), ("football", "college-football"),
        ("soccer", "usa.mls"), ("soccer", "eng.1")
    ]
    for s, l in leagues: all_games.extend(get_espn_data(s, l, whitelist, seen))
    all_games.sort(key=lambda x: x['iso_date'])
    generate_html(all_games)
    print(f"Update Success: {len(all_games)} matches.")

if __name__ == "__main__": main()
