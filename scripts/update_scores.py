"""
Tempe Torch — Unified Live Score Fetcher
Pulls live scores, extracts logos/locations, and outputs raw data.
"""

import json
import requests
from datetime import datetime

OUTPUT_PATH = "data/daily_scores.json"

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def fetch_json(url: str):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Fetch failed: {url} -> {e}")
        return None

# --------------------------------------------------
# GENERIC ESPN PARSER
# --------------------------------------------------

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
            
            # Extract status (e.g., "Final", "7:00 PM", "Live")
            status_state = event["status"]["type"]["state"] # pre, in, post
            status_detail = event["status"]["type"]["detail"]
            
            # Format time if game hasn't started
            if status_state == "pre":
                # API date is ISO string (e.g., 2023-10-25T23:00Z)
                dt = datetime.strptime(event["date"], "%Y-%m-%dT%H:%M:%SZ")
                # Simple formatted time (adjust logic for local timezone if needed)
                status_detail = dt.strftime("%I:%M %p")

            games.append({
                "sport": sport_label,
                "league": league_name or sport_label,
                "date": event["date"],
                "status": status_detail,
                "is_live": status_state == "in",
                
                # HOME TEAM
                "home": home_data["team"]["displayName"],
                "home_abbr": home_data["team"].get("abbreviation", home_data["team"]["displayName"][:3].upper()),
                "home_logo": home_data["team"].get("logo", ""),
                "home_score": home_data.get("score", "0"),
                "home_location": home_data["team"].get("location", ""), # Needed for State filtering
                
                # AWAY TEAM
                "away": away_data["team"]["displayName"],
                "away_abbr": away_data["team"].get("abbreviation", away_data["team"]["displayName"][:3].upper()),
                "away_logo": away_data["team"].get("logo", ""),
                "away_score": away_data.get("score", "0"),
                "away_location": away_data["team"].get("location", ""), 
            })
        except Exception as e:
            continue

    return games

# --------------------------------------------------
# FETCHERS
# --------------------------------------------------

def fetch_sports_data():
    all_games = []
    
    # Config: Map readable names to ESPN API endpoints
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
        # Soccer Leagues
        ("Premier League", "soccer/eng.1"),
        ("Bundesliga", "soccer/ger.1"),
        ("La Liga", "soccer/esp.1"),
        ("Ligue 1", "soccer/fra.1"),
        ("NWSL", "soccer/usa.nwsl"),
        ("Liga F", "soccer/esp.w.1"),
    ]

    print("Fetching ESPN Sports...")
    for label, slug in endpoints:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{slug}/scoreboard"
        data = fetch_json(url)
        all_games.extend(parse_espn_scoreboard(data, label))

    # Cricket (Special Handling)
    print("Fetching Cricket...")
    cric_data = fetch_json("https://site.api.espn.com/apis/site/v2/sports/cricket/competitions/scoreboard")
    # ESPN Cricket structure is similar enough to use the generic parser
    all_games.extend(parse_espn_scoreboard(cric_data, "Cricket"))

    return all_games

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    games = fetch_sports_data()
    
    output = {
        "updated": datetime.utcnow().isoformat(),
        "games": games,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved {len(games)} raw games -> {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
