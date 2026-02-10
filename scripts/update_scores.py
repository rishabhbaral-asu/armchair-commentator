"""
Tempe Torch — Ultimate Data Fetcher
Fetches Schedule -> Deep Summary -> Odds, Records, & Cricket Specifics.
"""

import json
import requests
from datetime import datetime, timezone

OUTPUT_PATH = "data/daily_scores.json"
DATE_WINDOW_DAYS = 1 

# --- BOUNCER LOGIC ---
TARGET_STATES = {"CA", "AZ", "IL", "GA", "MD", "DC", "VA", "TX"}
TARGET_INTL = {"India", "USA", "United States", "USA Women", "India Women", "Australia", "England"}
TARGET_SOCCER_CLUBS = {"Fulham", "Leeds", "Leeds United", "Leverkusen", "Bayer Leverkusen", "Gladbach", "St. Pauli", "Barcelona", "Real Madrid", "PSG", "Paris Saint-Germain"}
MAJOR_FINALS = ["Super Bowl", "NBA Finals", "World Series", "Stanley Cup Final", "Championship", "Final"]

def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return None

def is_relevant_pre_check(event):
    try:
        date_str = event.get("date", "")
        if date_str:
            if date_str.endswith('Z'): date_str = date_str[:-1]
            dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            if abs((dt - datetime.now(timezone.utc)).days) > DATE_WINDOW_DAYS: return False

        name = event.get("name", "")
        short_name = event.get("shortName", "")
        search_text = (name + " " + short_name).lower()
        
        if any(k.lower() in search_text for k in MAJOR_FINALS): return True
        
        all_targets = TARGET_STATES.union(TARGET_INTL).union(TARGET_SOCCER_CLUBS)
        if any(t.lower() in search_text for t in all_targets): return True
        
        return False
    except:
        return False

def get_deep_game_data(sport, league, game_id):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={game_id}"
    data = fetch_json(url)
    if not data: return None
    
    header = data.get("header", {})
    game_info = data.get("gameInfo", {})
    comp = header.get("competitions", [{}])[0]
    
    # 1. Location
    venue = game_info.get("venue", {}).get("fullName") or \
            game_info.get("venue", {}).get("address", {}).get("city", "Neutral Site")
    
    # 2. Competitors & Records
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c["homeAway"] == "home"), {})
    away = next((c for c in competitors if c["homeAway"] == "away"), {})
    
    home_record = home.get("record", [{}])[0].get("summary", "")
    away_record = away.get("record", [{}])[0].get("summary", "")

    # 3. Betting Odds (The "Vegas" Angle)
    odds_text = ""
    if "pickcenter" in data:
        for pick in data["pickcenter"]:
            if "provider" in pick and pick["provider"]["name"] == "consensus":
                odds_text = pick.get("details", "") # e.g. "SEA -3.0"
                break
    
    # 4. Leaders / Top Performers
    leaders = []
    if "leaders" in comp:
        for l in comp["leaders"]:
            if "leaders" in l and len(l["leaders"]) > 0:
                athlete = l["leaders"][0]
                leaders.append({
                    "name": athlete["athlete"]["displayName"],
                    "stat": athlete["displayValue"],
                    "desc": l["displayName"]
                })
    
    # 5. Headline
    headline = ""
    notes = comp.get("notes", [])
    if notes and len(notes) > 0:
        headline = notes[0].get("headline", "")

    # CRICKET SPECIFIC SCORE HANDLING
    # Cricket scores come as strings like "161/9 (20)"
    home_score = home.get("score", "0")
    away_score = away.get("score", "0")

    return {
        "game_id": game_id,
        "sport": sport.upper(),
        "league": league,
        "date": comp.get("date"),
        "status": comp.get("status", {}).get("type", {}).get("detail", ""),
        "state": comp.get("status", {}).get("type", {}).get("state", ""),
        "venue": venue,
        "odds": odds_text,
        "headline": headline,
        
        "home": home.get("team", {}).get("displayName", "Home Team"),
        "home_score": home_score,
        "home_record": home_record,
        "home_logo": home.get("team", {}).get("logos", [{}])[0].get("href", ""),
        
        "away": away.get("team", {}).get("displayName", "Away Team"),
        "away_score": away_score,
        "away_record": away_record,
        "away_logo": away.get("team", {}).get("logos", [{}])[0].get("href", ""),
        
        "leaders": leaders
    }

def fetch_sports_data():
    processed_games = []
    
    sources = [
        ("football", "nfl"), ("basketball", "nba"), ("hockey", "nhl"),
        ("football", "college-football"), ("basketball", "mens-college-basketball"),
        ("baseball", "college-baseball"), ("soccer", "usa.nwsl"),
        ("soccer", "eng.1"), ("soccer", "ger.1"), ("soccer", "esp.1"),
        # CRICKET IS HERE!
        ("cricket", "competitions") 
    ]

    print("Scanning ESPN Schedule...")
    for sport, league in sources:
        scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        sb_data = fetch_json(scoreboard_url)
        
        if not sb_data: continue

        for event in sb_data.get("events", []):
            if is_relevant_pre_check(event):
                game_id = event["id"]
                print(f"  -> Deep fetching {event['name']} ({game_id})")
                deep_data = get_deep_game_data(sport, league, game_id)
                if deep_data:
                    processed_games.append(deep_data)

    return processed_games

def main():
    games = fetch_sports_data()
    output = { "updated": datetime.utcnow().isoformat(), "games": games }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(games)} DEEP DATA games -> {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
