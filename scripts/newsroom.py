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
        "chicago red stars", "argentina", "brazil", "spain", "france", "germany", "belgium", "iowa"
    ]

# --- 2. THE RESEARCH ENGINES (Schedules & Weather) ---
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

def get_weather(city):
    """Placeholder for weather integration - easily expandable with OpenWeatherMap API"""
    return "Partly Cloudy" # In a real scenario, you'd fetch live data here

# --- 3. THE SMART STORY ENGINE ---
def craft_ap_story(event, sport, league):
    comp = event["competitions"][0]
    status = event["status"]["type"]["name"]
    home = comp["competitors"][0]
    away = comp["competitors"][1]
    eid = event["id"]
    
    city = comp.get("venue", {}).get("address", {}).get("city", "TEMPE")
    state = comp.get("venue", {}).get("address", {}).get("state", "AZ")
    dateline = f"**{city.upper()}, {state} (AP) — **"
    weather = get_weather(city)

    # A. PREGAME PREVIEW
    if status == "STATUS_SCHEDULED":
        time_obj = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc)
        local_time = time_obj.astimezone(pytz.timezone('US/Arizona')).strftime("%I:%M %p")
        return f"{dateline}The {away['team']['displayName']} prepare to face the {home['team']['displayName']} under {weather.lower()} skies. Tip-off is set for {local_time} MST. Both programs enter today's contest looking to secure a pivotal conference result."

    # B. POSTGAME RECAP
    winner = home if home.get("winner") else away
    loser = away if home.get("winner") else home
    
    try:
        # Check if leaders exist and have a valid value (not a season average)
        leader = winner["leaders"][0]["leaders"][0]
        name = leader["athlete"]["displayName"]
        val = leader["displayValue"]
        detail = f"{name} led the charge with {val} as the {winner['team']['shortDisplayName']} surged past {loser['team']['shortDisplayName']}."
    except:
        detail = f"The {winner['team']['shortDisplayName']} relied on a stout defensive effort to outlast {loser['team']['shortDisplayName']} at {comp.get('venue', {}).get('fullName', 'center court')}."

    w_next = get_up_next(winner["team"]["id"], sport, league, eid)
    return f"{dateline}{detail}<br><br><div class='up-next-box'><b>Up Next:</b> {winner['team']['shortDisplayName']} plays {w_next}.</div>"

# --- 4. DATA FETCH ---
def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    results = []
    try:
        data = requests.get(url, timeout=10).json()
        for event in data.get("events", []):
            eid = event["id"]
            name = event.get("name", "").lower()
            if any(team in name for team in whitelist) and eid not in seen_ids:
                comp = event["competitions"][0]
                st_type = event["status"]["type"]["name"]
                
                results.append({
                    "headline": event.get("name", "Game Update"),
                    "home_logo": comp["competitors"][0]["team"].get("logo"),
                    "away_logo": comp["competitors"][1]["team"].get("logo"),
                    "score_line": f"{comp['competitors'][1].get('score','0')} - {comp['competitors'][0].get('score','0')}" if st_type != "STATUS_SCHEDULED" else "PREGAME",
                    "away_name": comp["competitors"][1]["team"]["shortDisplayName"],
                    "home_name": comp["competitors"][0]["team"]["shortDisplayName"],
                    "ap_story": craft_ap_story(event, sport, league),
                    "status": event["status"]["type"]["detail"]
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- 5. THE MIDNIGHT NEWSROOM HTML ---
def generate_html(games):
    now = datetime.now(pytz.timezone('US/Arizona')).strftime("%B %d, %Y | %I:%M %p")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            :root {{
                --bg: #121212;
                --card-bg: #1e1e1e;
                --text: #e0e0e0;
                --accent: #ffc627; /* ASU GOLD */
                --border: #333;
            }}
            body {{ font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 40px; color: var(--text); }}
            .container {{ max-width: 800px; margin: auto; }}
            .masthead {{ text-align: center; border-bottom: 2px solid var(--accent); padding-bottom: 20px; margin-bottom: 40px; }}
            .masthead h1 {{ font-family: 'Playfair Display', serif; font-size: 3.5em; margin: 0; color: var(--accent); text-transform: uppercase; }}
            .card {{ background: var(--card-bg); border-radius: 12px; margin-bottom: 30px; border: 1px solid var(--border); overflow: hidden; }}
            .card-header {{ padding: 10px 20px; background: #252525; font-size: 0.8em; font-weight: bold; text-transform: uppercase; color: #888; display: flex; justify-content: space-between; }}
            .scoreboard {{ display: flex; align-items: center; justify-content: space-around; padding: 30px 20px; border-bottom: 1px solid var(--border); }}
            .team {{ text-align: center; width: 30%; }}
            .team img {{ height: 80px; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.5)); }}
            .team-name {{ display: block; margin-top: 10px; font-weight: bold; font-size: 1.1em; }}
            .score-display {{ font-size: 3em; font-weight: 900; color: var(--accent); }}
            .story-body {{ padding: 30px; line-height: 1.7; font-size: 1.1em; }}
            .up-next-box {{ background: #2a2a2a; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid var(--accent); font-size: 0.9em; }}
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    </head>
    <body>
        <div class="container">
            <div class="masthead">
                <h1>The Armchair Commentator</h1>
                <p>Digital Newsroom | {now} MST</p>
            </div>
    """
    for g in games:
        html_content += f"""
        <div class="card">
            <div class="card-header">
                <span>{g['headline']}</span>
                <span>{g['status']}</span>
            </div>
            <div class="scoreboard">
                <div class="team"><img src="{g['away_logo']}"><span class="team-name">{g['away_name']}</span></div>
                <div class="score-display">{g['score_line']}</div>
                <div class="team"><img src="{g['home_logo']}"><span class="team-name">{g['home_name']}</span></div>
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
        ("basketball", "womens-college-basketball"),
        ("baseball", "college-baseball"),
        ("basketball", "nba")
    ]
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    generate_html(all_games)

if __name__ == "__main__": main()
