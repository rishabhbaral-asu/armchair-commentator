import requests
import json
from datetime import datetime, timedelta
import pytz

# --- 1. CONFIG & WHITELIST ---
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
        "chicago red stars", "argentina", "brazil", "spain", "france", "germany", "belgium", "iowa",
        "indiana", "illinois" # Added these so your test game shows up!
    ]

OPENWEATHER_API_KEY = "ac08c1c364001a27b81d418f26e28315"

# --- 2. LIVE WEATHER ENGINE ---
def get_live_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=imperial"
        response = requests.get(url, timeout=5).json()
        if response.get("cod") == 200:
            temp = round(response["main"]["temp"])
            desc = response["weather"][0]["description"].capitalize()
            return f"{temp}°F and {desc}"
    except: pass
    return "Variable Conditions"

# --- 3. SCHEDULE RESEARCH ---
def get_up_next(team_id, sport, league, current_event_id):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/schedule"
    try:
        data = requests.get(url, timeout=5).json()
        now = datetime.now(pytz.utc)
        for event in data.get("events", []):
            if event["id"] == current_event_id: continue
            g_date = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc)
            if g_date > (now - timedelta(hours=2)):
                comp = event["competitions"][0]
                team_info = next(t for t in comp["competitors"] if t["id"] == team_id)
                opp = next(t["team"]["displayName"] for t in comp["competitors"] if t["id"] != team_id)
                venue = "home" if team_info["homeAway"] == "home" else "away"
                date_str = g_date.astimezone(pytz.timezone('US/Arizona')).strftime("%m/%d")
                return f"{date_str} {'vs' if venue == 'home' else 'at'} {opp}"
    except: pass
    return "TBD"

# --- 4. THE STORY ENGINE ---
def craft_ap_story(event, sport, league):
    comp = event["competitions"][0]
    status_name = event["status"]["type"]["name"]
    home, away = comp["competitors"][0], comp["competitors"][1]
    eid = event["id"]
    
    city = comp.get("venue", {}).get("address", {}).get("city", "Tempe")
    state = comp.get("venue", {}).get("address", {}).get("state", "AZ")
    dateline = f"**{city.upper()}, {state} (AP) — **"
    weather = get_live_weather(city)

    if status_name == "STATUS_SCHEDULED":
        time_obj = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc)
        local_time = time_obj.astimezone(pytz.timezone('US/Arizona')).strftime("%I:%M %p")
        return f"{dateline}The {away['team']['shortDisplayName']} face {home['team']['shortDisplayName']} today. Weather in {city} is currently {weather}. Tip-off: {local_time} MST."

    winner = home if home.get("winner") else away
    loser = away if home.get("winner") else home
    
    try:
        leader = winner["leaders"][0]["leaders"][0]
        name, val = leader["athlete"]["displayName"], leader["displayValue"]
        detail = f"{name} led the charge with {val} as the {winner['team']['shortDisplayName']} defeated {loser['team']['shortDisplayName']}."
    except:
        detail = f"The {winner['team']['shortDisplayName']} secured a win over {loser['team']['shortDisplayName']} in {city}."

    w_next = get_up_next(winner["team"]["id"], sport, league, eid)
    return f"{dateline}{detail}<br><br><div class='up-next-box'><b>Up Next:</b> {winner['team']['shortDisplayName']} ({w_next}).</div>"

# --- 5. THE UI & DATA FETCH ---
def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    results = []
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        for event in data.get("events", []):
            eid = event["id"]
            name = event.get("name", "").lower()
            
            # Use the passed 'whitelist' variable correctly
            if any(team in name for team in whitelist) and eid not in seen_ids:
                print(f"Match Found: {event.get('name')}") # Debug print
                comp = event["competitions"][0]
                st_name = event["status"]["type"]["name"]
                
                score_str = f"{comp['competitors'][1].get('score','0')} - {comp['competitors'][0].get('score','0')}"
                if st_name == "STATUS_SCHEDULED": score_str = "PREGAME"
                
                results.append({
                    "headline": event.get("name", "Game Update"),
                    "home_logo": comp["competitors"][0]["team"].get("logo"),
                    "away_logo": comp["competitors"][1]["team"].get("logo"),
                    "score_line": score_str,
                    "away_name": comp["competitors"][1]["team"]["shortDisplayName"],
                    "home_name": comp["competitors"][0]["team"]["shortDisplayName"],
                    "ap_story": craft_ap_story(event, sport, league),
                    "status": event["status"]["type"]["detail"]
                })
                seen_ids.add(eid)
    except Exception as e: 
        print(f"Error fetching {league}: {e}")
    return results

def generate_html(games):
    now = datetime.now(pytz.timezone('US/Arizona')).strftime("%B %d, %Y | %I:%M %p")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            :root {{ --bg: #0f1113; --card-bg: #1a1d21; --text: #ffffff; --accent: #ffc627; --dim: #a0a6ad; --border: #2d3238; }}
            body {{ font-family: 'Inter', sans-serif; background: var(--bg); margin: 0; padding: 40px; color: var(--text); }}
            .container {{ max-width: 800px; margin: auto; }}
            .masthead {{ text-align: center; border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 40px; }}
            .masthead h1 {{ font-family: serif; font-size: 3.5em; margin: 0; color: var(--accent); }}
            .card {{ background: var(--card-bg); border-radius: 16px; margin-bottom: 30px; border: 1px solid var(--border); overflow: hidden; }}
            .card-header {{ padding: 12px 25px; background: #24292e; font-size: 0.85em; font-weight: 800; color: var(--accent); display: flex; justify-content: space-between; }}
            .scoreboard {{ display: flex; align-items: center; justify-content: space-around; padding: 40px 20px; }}
            .team {{ text-align: center; width: 30%; }}
            .team img {{ height: 80px; }}
            .score-display {{ font-size: 3em; font-weight: 900; }}
            .story-body {{ padding: 35px; line-height: 1.8; font-size: 1.1em; border-top: 1px solid var(--border); }}
            .up-next-box {{ background: #121417; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 3px solid var(--accent); color: var(--dim); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="masthead"><h1>The Armchair Commentator</h1><p style="color:var(--dim);">{now} MST</p></div>
    """
    if not games:
        html_content += "<div style='text-align:center; padding: 50px;'><h3>No games found for your teams today.</h3></div>"
    
    for g in games:
        html_content += f"""
        <div class="card">
            <div class="card-header"><span>{g['headline']}</span><span>{g['status']}</span></div>
            <div class="scoreboard">
                <div class="team"><img src="{g['away_logo']}"><br><b>{g['away_name']}</b></div>
                <div class="score-display">{g['score_line']}</div>
                <div class="team"><img src="{g['home_logo']}"><br><b>{g['home_name']}</b></div>
            </div>
            <div class="story-body">{g['ap_story']}</div>
        </div>
        """
    html_content += "</div></body></html>"
    with open("index.html", "w") as f: f.write(html_content)

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "mens-college-basketball"), 
        ("basketball", "nba"), 
        ("baseball", "college-baseball")
    ]
    for s, l in leagues:
        # Fixed: passing 'whitelist' as the 3rd argument
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    
    generate_html(all_games)
    print(f"Success! Generated index.html with {len(all_games)} games.")

if __name__ == "__main__": main()
