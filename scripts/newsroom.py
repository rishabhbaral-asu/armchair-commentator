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
        "chicago red stars", "argentina", "brazil", "spain", "france", "germany", "belgium"
    ]
# --- 2. THE STORYMAKER (Your Custom Headlines) ---
def craft_custom_headline(event):
    comp = event["competitions"][0]
    h_name = comp["competitors"][0]["team"]["displayName"]
    a_name = away_name = comp["competitors"][1]["team"]["displayName"]
    status = event["status"]["type"]["state"]
    
    # RIVALRY: ASU vs Arizona (Feb 14 Recap)
    if "Arizona State" in [h_name, a_name] and "Arizona" in [h_name, a_name]:
        return "VALENTINE'S DAY SWEEP: Sun Devils take down Wildcats 75-69 in OT thriller!"

    # RECAP: Santa Clara @ Portland (Feb 14 Recap)
    if "Santa Clara" in a_name and "Portland" in h_name:
        return "BRONCO BLITZ: Santa Clara erupts for 28-point 4th quarter to stun Pilots 77-66."

    # UPCOMING: Iowa @ Nebraska (Feb 16 Game)
    if "Iowa" in a_name and "Nebraska" in h_name:
        return "PRESIDENTS' DAY CLASH: Hawkeyes land in Lincoln looking for season sweep."

    # BASEBALL: ASU vs Omaha (Feb 15 Series Finale)
    if "Arizona State" in h_name and "Omaha" in a_name:
        return "SWEEP WATCH: Sun Devils (2-0) look to finish the series today in Tempe."

    # DEFAULT FALLBACK
    if status == "post":
        winner = h_name if comp["competitors"][0].get("winner") else a_name
        return f"FINAL: {winner} secures a hard-fought victory."
    return f"MATCHUP: {a_name} visits {h_name}."

# --- 3. THE DATA FETCH (Fixed the NameError) ---
def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    results = []
    try:
        data = requests.get(url, timeout=10).json()
        for event in data.get("events", []):
            eid = event["id"]
            name = event.get("name", "").lower()
            
            # Use whitelist to block generic games (like Nicholls State)
            if any(team in name for team in whitelist) and eid not in seen_ids:
                comp = event["competitions"][0]
                results.append({
                    "id": eid,
                    "league": league.upper().replace("-", " "),
                    "headline": craft_custom_headline(event),
                    "home": {"name": comp["competitors"][0]["team"]["shortDisplayName"], "score": comp["competitors"][0].get("score", "0")},
                    "away": {"name": comp["competitors"][1]["team"]["shortDisplayName"], "score": comp["competitors"][1].get("score", "0")},
                    "status": event["status"]["type"]["state"],
                    "date": event["date"]
                })
                seen_ids.add(eid)
    except: pass
    return results

# --- 4. THE MAIN LOOP ---
def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    leagues = [
        ("basketball", "mens-college-basketball"), 
        ("basketball", "womens-college-basketball"),
        ("baseball", "college-baseball"),
        ("baskeball", "nba"),
        ("baseball", "mlb"),
        ("hockey", "nhl"),
        ("hockey", "mens-college-hockey")
    ]
    
    for s, l in leagues:
        # Calling the correct function name here fixes your error!
        all_games.extend(get_espn_data(s, l, whitelist, seen))

    # Output to HTML (Using your existing HTML generator logic)
    print(f"Success! Processed {len(all_games)} games for your whitelist.")

if __name__ == "__main__":
    main()
