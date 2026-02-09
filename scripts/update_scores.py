"""
Tempe Torch — Score Fetcher
Fetches live scores, fetches REAL player stats, and filters by DATE (Today +/- 1 Day).
"""

import json
import requests
from datetime import datetime, timedelta
from dateutil import parser # Use dateutil for robust parsing if available, else standard datetime
import pytz

OUTPUT_PATH = "data/daily_scores.json"

# --- CONFIG: DATE WINDOW ---
# Only show games from yesterday, today, and tomorrow.
DATE_WINDOW_DAYS = 1 

def fetch_json(url: str):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Fetch failed: {url} -> {e}")
        return None

def is_date_relevant(date_str):
    """Returns True if the game is within the target window (Yesterday/Today/Tomorrow)"""
    try:
        # ESPN dates are UTC ISO strings (e.g. 2024-10-12T14:00Z)
        game_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
        now = datetime.now(pytz.UTC)
        
        # Calculate difference
        diff = game_date - now
        
        # Keep if within -24 hours to +48 hours (covers "yesterday" through "tomorrow")
        return abs(diff.days) <= DATE_WINDOW_DAYS
    except:
        # If date parsing fails, usually safer to exclude, or include if you want to be permissive
        return False

def parse_espn_scoreboard(data, sport_label, league_name=None):
    games = []
    if not data or "events" not in data:
        return games

    for event in data["events"]:
        try:
            # --- 1. STRICT DATE FILTER ---
            if not is_date_relevant(event["date"]):
                continue

            comp = event["competitions"][0]
            teams = comp["competitors"]
            
            home_data = next(t for t in teams if t["homeAway"] == "home")
            away_data = next(t for t in teams if t["homeAway"] == "away")
            
            # Fetch Leaders (Real Stats)
            leaders = []
            if "leaders" in comp:
                for leader_group in comp["leaders"]:
                    if "leaders" in leader_group and len(leader_group["leaders"]) > 0:
                        player = leader_group["leaders"][0]
                        leaders.append({
                            "name": player["athlete"]["displayName"],
                            "stat": player["displayValue"], 
                            "desc": leader_group["displayName"]
                        })
            
            # Game Note (Finals check)
            game_note = event.get("name", "")
            if comp.get("notes"):
                game_note += " " + " ".join([n.get("headline", "") for n in comp["notes"]])

            games.append({
                "sport": sport_label,
                "league": league_name or sport_label,
                "date": event["date"],
                "status": event["status"]["type"]["detail"],
                "is_live": event["status"]["type"]["state"] == "in",
                "game_note": game_note, 
                "leaders": leaders,
                
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
    
    # Endpoints
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
        ("Premier League", "soccer/eng.1"),
        ("Bundesliga", "soccer/ger.1"),
        ("La Liga", "soccer/esp.1"),
        ("Ligue 1", "soccer/fra.1"),
        ("Liga F", "soccer/esp.w.1"),
        ("NWSL", "soccer/usa.nwsl"),
    ]

    print("Fetching ESPN Sports...")
    for label, slug in endpoints:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{slug}/scoreboard"
        data = fetch_json(url)
        all_games.extend(parse_espn_scoreboard(data, label, label))

    print("Fetching Cricket...")
    cric_data = fetch_json("https://site.api.espn.com/apis/site/v2/sports/cricket/competitions/scoreboard")
    all_games.extend(parse_espn_scoreboard(cric_data, "Cricket", "Cricket"))

    return all_games

def main():
    games = fetch_sports_data()
    output = { "updated": datetime.utcnow().isoformat(), "games": games }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(games)} relevant games -> {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
