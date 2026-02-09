"""
Tempe Torch — Unified Live Score Fetcher
Fetches ALL sports data but captures extra metadata for filtering later.
"""

import json
import requests
from datetime import datetime

OUTPUT_PATH = "data/daily_scores.json"

def fetch_json(url: str):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Fetch failed: {url} -> {e}")
        return None

def parse_espn_scoreboard(data, sport_label, league_name=None):
    games = []
    if not data or "events" not in data:
        return games

    for event in data["events"]:
        try:
            comp = event["competitions"][0]
            teams = comp["competitors"]
            
            home_data = next(t for t in teams if t["homeAway"] == "home")
            away_data = next(t for t in teams if t["homeAway"] == "away")
            
            # Capture Game Note (e.g., "Final", "Super Bowl", "Championship")
            game_note = event.get("name", "")
            if comp.get("notes"):
                game_note += " " + comp["notes"][0].get("headline", "")
            
            games.append({
                "sport": sport_label,
                "league": league_name or sport_label, # e.g., "NWSL"
                "date": event["date"],
                "status": event["status"]["type"]["detail"],
                "is_live": event["status"]["type"]["state"] == "in",
                "game_note": game_note, # Crucial for the "Finals" exception
                
                # HOME
                "home": home_data["team"]["displayName"],
                "home_abbr": home_data["team"].get("abbreviation", home_data["team"]["displayName"][:3].upper()),
                "home_logo": home_data["team"].get("logo", ""),
                "home_score": home_data.get("score", "0"),
                "home_location": home_data["team"].get("location", ""), 
                
                # AWAY
                "away": away_data["team"]["displayName"],
                "away_abbr": away_data["team"].get("abbreviation", away_data["team"]["displayName"][:3].upper()),
                "away_logo": away_data["team"].get("logo", ""),
                "away_score": away_data.get("score", "0"),
                "away_location": away_data["team"].get("location", ""), 
            })
        except Exception:
            continue

    return games

def fetch_sports_data():
    all_games = []
    
    # 1. EXPANDED ENDPOINTS (Covering all requested leagues)
    endpoints = [
        ("NFL", "football/nfl"),
        ("NBA", "basketball/nba"),
        ("NHL", "hockey/nhl"),
        ("NCAA Football", "football/college-football"),
        ("NCAA Men's BB", "basketball/mens-college-basketball"),
        ("NCAA Women's BB", "basketball/womens-college-basketball"),
        ("NCAA Baseball", "baseball/college-baseball"),
        ("NCAA Softball", "baseball/college-softball"),
        ("NCAA Hockey", "hockey/mens-college-hockey"),
        # Soccer Specifics
        ("Premier League", "soccer/eng.1"),
        ("Bundesliga", "soccer/ger.1"),
        ("La Liga", "soccer/esp.1"),
        ("Ligue 1", "soccer/fra.1"),
        ("Liga F", "soccer/esp.w.1"),
        ("NWSL", "soccer/usa.nwsl"), # Explicitly fetching NWSL
    ]

    print("Fetching ESPN Sports...")
    for label, slug in endpoints:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{slug}/scoreboard"
        data = fetch_json(url)
        all_games.extend(parse_espn_scoreboard(data, label, label))

    # Cricket (Special Handling)
    print("Fetching Cricket...")
    cric_data = fetch_json("https://site.api.espn.com/apis/site/v2/sports/cricket/competitions/scoreboard")
    all_games.extend(parse_espn_scoreboard(cric_data, "Cricket", "Cricket"))

    return all_games

def main():
    games = fetch_sports_data()
    output = { "updated": datetime.utcnow().isoformat(), "games": games }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(games)} raw games -> {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
