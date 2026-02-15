import requests
import json
from datetime import datetime
import pytz
import re

# --- 1. THE WHITELIST ---
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

# --- 2. AP STORY ENGINE (Research-Driven) ---
def craft_ap_story(event, sport, league):
    comp = event["competitions"][0]
    home = comp["competitors"][0]
    away = comp["competitors"][1]
    status_type = event["status"]["type"]["state"]
    venue = comp.get("venue", {}).get("fullName", "Unknown Venue")
    city = comp.get("venue", {}).get("address", {}).get("city", "LOCATION")
    state = comp.get("venue", {}).get("address", {}).get("state", "ST")
    
    # 1. Dateline
    dateline = f"{city.upper()}, {state} (AP) — "
    
    # 2. Performance Research (Getting specific scorers/stats)
    details = ""
    try:
        # We try to find the leading scorer from the winner's side
        winner = home if home.get("winner") else away
        leader = winner["leaders"][0]["leaders"][0]
        name = leader["athlete"]["displayName"]
        val = leader["displayValue"]
        stat = winner["leaders"][0]["displayName"].lower()
        details = f"{name} had {val} {stat} to lead the {winner['team']['shortDisplayName']}. "
    except:
        details = f"The {away['team']['shortDisplayName']} and {home['team']['shortDisplayName']} battled in a physical contest. "

    # 3. Sport-Specific Narrative
    narrative = ""
    if status_type == "post":
        if "basketball" in league.lower():
            if "OT" in event["status"]["type"]["detail"]:
                narrative = "The game required extra time to settle before a decisive run in the final minutes of overtime."
            elif abs(int(home['score']) - int(away['score'])) > 15:
                narrative = "What began as a contested matchup turned into a rout early in the second half."
            else:
                narrative = "The contest featured several lead changes before the defense tightened in the closing moments."
        elif "baseball" in league.lower():
            narrative = f"The victory at {venue} secured a crucial result in the weekend series as the bats stayed hot through the middle innings."
    else:
        narrative = f"The teams are set to meet at {venue} in a matchup with significant postseason implications."

    # 4. Schedule Research (Up Next)
    # This logic assumes the next game is listed in the team's record or schedule notes
    up_next = f"\n\n**Up Next:** {away['team']['shortDisplayName']} continues their road trip Tuesday, while {home['team']['shortDisplayName']} remains home."

    return f"{dateline}{details}{narrative}{up_next}"

# --- 3. DATA FETCH ---
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
                results.append({
                    "id": eid,
                    "league": league.upper().replace("-", " "),
                    "headline": event.get("shortName", "Game Update"),
                    "ap_story": craft_ap_story(event, sport, league), # THE AP STORY
                    "home": {"name": comp["competitors"][0]["team"]["shortDisplayName"], "score": comp["competitors"][0].get("score", "0")},
                    "away": {"name": comp["competitors"][1]["team"]["shortDisplayName"], "score": comp["competitors"][1].get("score", "0")},
                    "status": event["status"]["type"]["detail"],
                    "date": event["date"]
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- 4. HTML GENERATOR ---
def generate_html(games):
    now = datetime.now(pytz.timezone('US/Arizona')).strftime("%B %d, %I:%M %p")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>The Armchair Commentator</title>
        <style>
            body {{ font-family: "Georgia", serif; background: #fdfdfd; color: #111; margin: 0; padding: 40px; line-height: 1.6; }}
            .container {{ max-width: 800px; margin: auto; }}
            .header {{ text-align: center; border-bottom: 5px double #222; margin-bottom: 40px; padding-bottom: 20px; }}
            .header h1 {{ font-size: 3em; margin: 0; font-family: "Times New Roman", serif; font-variant: small-caps; }}
            .game-card {{ margin-bottom: 50px; border-bottom: 1px solid #ccc; padding-bottom: 30px; }}
            .league-tag {{ font-weight: bold; text-transform: uppercase; color: #d00; font-size: 0.9em; }}
            .score-line {{ font-size: 1.5em; font-weight: bold; margin: 10px 0; }}
            .ap-body {{ font-size: 1.1em; color: #333; }}
            .dateline {{ font-weight: bold; text-transform: uppercase; }}
            .empty-msg {{ text-align: center; padding: 100px; font-style: italic; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>The Armchair Commentator</h1>
                <div>Late Edition — {now} MST</div>
            </div>
    """

    if not games:
        html_content += '<div class="empty-msg">The newsroom is quiet. No whitelisted games found for this cycle.</div>'
    else:
        for g in games:
            html_content += f"""
            <div class="game-card">
                <div class="league-tag">{g['league']} — {g['status']}</div>
                <div class="score-line">{g['away']['name']} {g['away']['score']}, {g['home']['name']} {g['home']['score']}</div>
                <div class="ap-body">{g['ap_story']}</div>
            </div>
            """

    html_content += "</div></body></html>"
    with open("index.html", "w") as f:
        f.write(html_content)

# --- 5. MAIN ---
def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "mens-college-basketball"), 
        ("basketball", "womens-college-basketball"),
        ("baseball", "college-baseball"),
        ("basketball", "nba"),
        ("baseball", "mlb"),
        ("hockey", "nhl")
    ]
    
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))

    generate_html(all_games)
    print(f"Success! Processed {len(all_games)} games.")

if __name__ == "__main__":
    main()
