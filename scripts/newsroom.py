import requests
import json
from datetime import datetime
import pytz
import os
import re
import time

# --- CONFIG ---
OUTPUT_FILE = "index.html"

def load_whitelist():
    # Directly using your provided list for accuracy
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
        "chicago red stars", "argentina", "brazil", "spain", "france", "germany", "belgium"
    ]

def is_match(event_name, whitelist):
    if not event_name: return False
    name_clean = event_name.lower()
    # Checks if any item in your whitelist exists as a standalone word in the game name
    for team in whitelist:
        if re.search(r'\b' + re.escape(team) + r'\b', name_clean):
            return True
    return False

def craft_ap_story(summary_json):
    header = summary_json.get("header", {})
    comp = header.get("competitions", [{}])[0]
    state = comp.get("status", {}).get("type", {}).get("state")
    teams = comp.get("competitors", [])
    
    # Try to get real ESPN recap
    for art in summary_json.get("news", {}).get("articles", []):
        if art.get("type") == "recap":
            return re.sub('<[^<]+?>', '', art.get("story", ""))

    if state == "post":
        winner = next((t for t in teams if t.get("winner")), teams[0])
        loser = next((t for t in teams if not t.get("winner")), teams[1])
        w_t, l_t = winner['team'], loser['team']
        return f"**{w_t['location'].upper()}** — The {w_t['displayName']} defeated the {l_t['displayName']} {winner['score']}-{loser['score']} in a key matchup tonight."
    
    return "WIRE DISPATCH — Action is currently underway or scheduled to begin shortly. Check back for the full post-game recap."

def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    # Use groups=50 for all NCAA, groups=default for Pro
    params = {"limit": "200", "cb": int(time.time())}
    if "college-" in league: params["groups"] = "50"

    games = []
    try:
        data = requests.get(url, params=params, timeout=10).json()
        for event in data.get("events", []):
            eid = str(event['id'])
            if eid in seen_ids: continue
            
            if is_match(event.get("name", ""), whitelist):
                sum_url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={eid}"
                summary = requests.get(sum_url).json()
                comp = event["competitions"][0]
                home, away = comp['competitors'][0], comp['competitors'][1]
                
                seen_ids.add(eid)
                games.append({
                    "id": eid, "sport": league.upper().replace("-", " "), 
                    "status": event["status"]["type"]["state"],
                    "home": {"name": home['team']['displayName'], "score": home.get("score", "0")},
                    "away": {"name": away['team']['displayName'], "score": away.get("score", "0")},
                    "story": craft_ap_story(summary),
                    "raw_date": event.get("date")
                })
    except: pass
    return games

def main():
    whitelist = load_whitelist()
    all_games = []
    seen = set()
    
    # Expanded list to cover your whitelist (Soccer, NFL, etc.)
    leagues = [
        ("basketball", "nba"), ("basketball", "mens-college-basketball"), ("basketball", "womens-college-basketball"),
        ("hockey", "nhl"), ("hockey", "mens-college-hockey"),
        ("baseball", "mlb"), ("baseball", "college-baseball"), ("baseball", "college-softball"),
        ("football", "nfl"), ("soccer", "usa.mls"), ("soccer", "eng.1"), ("soccer", "esp.1"), ("soccer", "ita.1"), ("soccer", "ger.1")
    ]
    
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))
    
    # Sort: Live games and finals at the top
    all_games.sort(key=lambda x: (x["status"] == "post", x["raw_date"]))
    
    # Generate the same HTML as before
    # (Omitted here for brevity, use the generate_html function from the previous version)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        # Pass all_games to your generate_html function here
        pass 

if __name__ == "__main__":
    main()
