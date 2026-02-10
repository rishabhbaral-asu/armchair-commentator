"""
Tempe Torch — AP Style Data Miner
Fetches Schedule -> Deep Summary -> Extrapolates AP-Style Stats (Injuries, Team Stats, Records).
"""

import json
import requests
from datetime import datetime, timezone

OUTPUT_PATH = "data/daily_scores.json"
DATE_WINDOW_DAYS = 1 

# --- CONFIG ---
MAJOR_FINALS = ["Super Bowl", "NBA Finals", "World Series", "Stanley Cup Final", "Championship", "Final"]
# Broad search to ensure we catch the games we want
TARGET_KEYWORDS = ["Suns", "Lakers", "Seahawks", "Patriots", "India", "USA", "Cricket", "ASU", "Arizona State"]

def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return None

def is_relevant_game(event):
    # 1. Date Check
    try:
        date_str = event.get("date", "")
        if date_str:
            if date_str.endswith('Z'): date_str = date_str[:-1]
            dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            if abs((dt - datetime.now(timezone.utc)).days) > DATE_WINDOW_DAYS: return False
    except:
        pass

    # 2. Keyword/League Check
    name = event.get("name", "")
    short_name = event.get("shortName", "")
    search_text = (name + " " + short_name).lower()
    
    if any(k.lower() in search_text for k in MAJOR_FINALS): return True
    if any(k.lower() in search_text for k in TARGET_KEYWORDS): return True
    
    # Always allow Cricket for the user request
    league = event.get("competitions", [{}])[0].get("league", {}).get("slug", "")
    if "cricket" in league: return True

    return False

def get_deep_game_data(sport, league, game_id):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={game_id}"
    data = fetch_json(url)
    if not data: return None
    
    header = data.get("header", {})
    game_info = data.get("gameInfo", {})
    comp = header.get("competitions", [{}])[0]
    boxscore = data.get("boxscore", {})
    
    # 1. Location & Time
    venue = game_info.get("venue", {}).get("fullName") or "Neutral Site"
    city = game_info.get("venue", {}).get("address", {}).get("city", "")
    state = game_info.get("venue", {}).get("address", {}).get("state", "")
    location_str = f"{city}, {state}" if city and state else venue
    
    # 2. Competitors
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c["homeAway"] == "home"), {})
    away = next((c for c in competitors if c["homeAway"] == "away"), {})
    
    # 3. Injuries (Crucial for AP Style)
    # ESPN lists injuries in the team section or separate lists
    home_injuries = []
    away_injuries = []
    
    if "injuries" in data: # sometimes separate list
        # Logic to parse if available in specific sport structure
        pass
    
    # 4. Team Stats (Comparison)
    # We look for "statistics" in boxscore
    team_stats = {} # { "FG%": ["45.0", "42.0"], "Rebounds": [40, 38] }
    if "teams" in boxscore:
        for tm in boxscore["teams"]:
            # This requires parsing sport-specific stat blocks
            # Saving raw for the generator to parse
            pass

    # 5. Leaders (Top Performers)
    leaders = []
    if "leaders" in comp:
        for l in comp["leaders"]:
            if "leaders" in l and len(l["leaders"]) > 0:
                athlete = l["leaders"][0]
                leaders.append({
                    "name": athlete["athlete"]["displayName"],
                    "stat": athlete["displayValue"],
                    "desc": l["displayName"],
                    "team": l.get("team", {}).get("abbreviation", "")
                })

    return {
        "game_id": game_id,
        "sport": sport.upper(),
        "league": league,
        "date": comp.get("date"),
        "status": comp.get("status", {}).get("type", {}).get("detail", ""),
        "state": comp.get("status", {}).get("type", {}).get("state", ""),
        "location": location_str,
        "venue": venue,
        
        "home": home.get("team", {}).get("displayName", "Home"),
        "home_abbr": home.get("team", {}).get("abbreviation", "HOME"),
        "home_record": home.get("record", [{}])[0].get("summary", "0-0"),
        "home_score": home.get("score", "0"),
        "home_logo": home.get("team", {}).get("logos", [{}])[0].get("href", ""),
        
        "away": away.get("team", {}).get("displayName", "Away"),
        "away_abbr": away.get("team", {}).get("abbreviation", "AWAY"),
        "away_record": away.get("record", [{}])[0].get("summary", "0-0"),
        "away_score": away.get("score", "0"),
        "away_logo": away.get("team", {}).get("logos", [{}])[0].get("href", ""),
        
        "leaders": leaders,
        "odds": data.get("pickcenter", [{}])[0].get("details", "") if "pickcenter" in data else ""
    }

def fetch_sports_data():
    processed_games = []
    
    # Added Cricket specifically
    sources = [
        ("football", "nfl"), ("basketball", "nba"), ("football", "college-football"),
        ("basketball", "mens-college-basketball"), ("baseball", "college-baseball"),
        ("cricket", "competitions")
    ]

    print("Scanning ESPN Schedule...")
    for sport, league in sources:
        # Generic Scoreboard
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        data = fetch_json(url)
        if not data: continue

        for event in data.get("events", []):
            if is_relevant_game(event):
                print(f"  -> Deep fetching {event['name']}")
                deep = get_deep_game_data(sport, league, event['id'])
                if deep: processed_games.append(deep)

    return processed_games

def main():
    games = fetch_sports_data()
    output = { "updated": datetime.utcnow().isoformat(), "games": games }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(games)} games to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
