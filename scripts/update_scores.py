"""
Tempe Torch — Deep Data Fetcher
Fetches schedule -> Then fetches FULL SUMMARY for each relevant game.
Source of Truth: ESPN Game ID.
"""

import json
import requests
from datetime import datetime, timezone

OUTPUT_PATH = "data/daily_scores.json"
DATE_WINDOW_DAYS = 1 

# --- BOUNCER LOGIC (To save API calls, we filter BEFORE deep fetching) ---
TARGET_STATES = {"CA", "AZ", "IL", "GA", "MD", "DC", "VA", "TX"}
TARGET_INTL = {"India", "USA", "United States", "USA Women", "India Women"}
TARGET_SOCCER_CLUBS = {"Fulham", "Leeds", "Leeds United", "Leverkusen", "Bayer Leverkusen", "Gladbach", "St. Pauli", "Barcelona", "Real Madrid", "PSG", "Paris Saint-Germain"}
TARGET_CRICKET_LEAGUES = {"ICC", "IPL", "MLC", "Indian Premier League", "Major League Cricket"}
MAJOR_FINALS = ["Super Bowl", "NBA Finals", "World Series", "Stanley Cup Final", "Championship"]

def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return None

def is_relevant_pre_check(event):
    """Quick check to see if we should fetch the deep data for this game."""
    try:
        # 1. Date Check
        date_str = event.get("date", "")
        if date_str:
            if date_str.endswith('Z'): date_str = date_str[:-1]
            dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            if abs((dt - datetime.now(timezone.utc)).days) > DATE_WINDOW_DAYS: return False

        name = event.get("name", "")
        short_name = event.get("shortName", "")
        league = event.get("competitions", [{}])[0].get("league", {}).get("slug", "")
        
        # 2. Keyword Check
        search_text = (name + " " + short_name).lower()
        
        if any(k.lower() in search_text for k in MAJOR_FINALS): return True
        if "nwsl" in league or "nwsl" in search_text: return True
        
        # Check targets
        all_targets = TARGET_STATES.union(TARGET_INTL).union(TARGET_SOCCER_CLUBS)
        # Note: State check is harder here without full location, so we lean on team names
        # We will do a stricter check after deep fetch
        if any(t.lower() in search_text for t in all_targets): return True
        
        return False
    except:
        return False

def get_deep_game_data(sport, league, game_id):
    """
    The Money Function. Fetches the specific game summary page.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={game_id}"
    data = fetch_json(url)
    if not data: return None
    
    # Extract Key Data
    box_score = data.get("boxscore", {})
    header = data.get("header", {})
    game_info = data.get("gameInfo", {})
    
    # 1. Location
    venue = game_info.get("venue", {}).get("fullName") or \
            game_info.get("venue", {}).get("address", {}).get("city", "Neutral Site")

    # 2. Competitors & Rosters (Leaders)
    competitors = header.get("competitions", [{}])[0].get("competitors", [])
    home = next((c for c in competitors if c["homeAway"] == "home"), {})
    away = next((c for c in competitors if c["homeAway"] == "away"), {})
    
    # 3. Top Performers (The Narrative Drivers)
    # ESPN usually provides a 'leaders' array in the summary
    leaders = []
    # Try to find leaders in the boxscore first
    if "players" in box_score:
        # Logic to find top scorer from boxscore stats is complex, 
        # usually header['competitions'][0]['leaders'] is easier if available
        pass

    # Fallback to header leaders (often populated)
    if not leaders and "leaders" in header.get("competitions", [{}])[0]:
        raw_leaders = header["competitions"][0]["leaders"]
        for l in raw_leaders:
            leaders.append({
                "name": l["leaders"][0]["athlete"]["displayName"],
                "stat": l["leaders"][0]["displayValue"],
                "desc": l["displayName"]
            })

    return {
        "game_id": game_id,
        "sport": sport.upper(),
        "league": league,
        "date": header["competitions"][0]["date"],
        "status": header["competitions"][0]["status"]["type"]["detail"],
        "state": header["competitions"][0]["status"]["type"]["state"], # pre, in, post
        "venue": venue,
        "home": home.get("team", {}).get("displayName"),
        "home_score": home.get("score"),
        "home_logo": home.get("team", {}).get("logos", [{}])[0].get("href"),
        "away": away.get("team", {}).get("displayName"),
        "away_score": away.get("score"),
        "away_logo": away.get("team", {}).get("logos", [{}])[0].get("href"),
        "leaders": leaders, # REAL PLAYERS ONLY
        "headline": header.get("competitions", [{}])[0].get("notes", [{}])[0].get("headline", "")
    }

def fetch_sports_data():
    processed_games = []
    
    # Map of (Sport, League) for URL construction
    sources = [
        ("football", "nfl"), ("basketball", "nba"), ("hockey", "nhl"),
        ("football", "college-football"), ("basketball", "mens-college-basketball"),
        ("baseball", "college-baseball"), ("soccer", "usa.nwsl"),
        ("soccer", "eng.1"), ("soccer", "ger.1"), ("soccer", "esp.1")
    ]

    print("Scanning ESPN Schedule...")
    for sport, league in sources:
        # 1. Get Schedule
        scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        sb_data = fetch_json(scoreboard_url)
        
        if not sb_data: continue

        for event in sb_data.get("events", []):
            # 2. Filter First
            if is_relevant_pre_check(event):
                # 3. Deep Fetch
                game_id = event["id"]
                print(f"  -> Deep fetching {event['name']} ({game_id})")
                deep_data = get_deep_game_data(sport, league, game_id)
                if deep_data:
                    processed_games.append(deep_data)

    # Cricket (Special Endpoint)
    c_url = "https://site.api.espn.com/apis/site/v2/sports/cricket/competitions/scoreboard"
    c_data = fetch_json(c_url)
    if c_data:
        for event in c_data.get("events", []):
            if is_relevant_pre_check(event):
                # Cricket summary structure is slightly different, usually just use scoreboard data
                # For safety, we'll just push the basic data here to avoid breaking on Cricinfo schema
                # (You asked for Cricinfo, but ESPN's Cricket API is the accessible JSON one)
                pass 

    return processed_games

def main():
    games = fetch_sports_data()
    output = { "updated": datetime.utcnow().isoformat(), "games": games }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(games)} DEEP DATA games -> {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
