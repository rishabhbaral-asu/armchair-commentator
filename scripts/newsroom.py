import requests
import json
from datetime import datetime
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

# --- 2. LIVE SCHEDULE LOOKUP ENGINE ---
def get_up_next(team_id, sport, league):
    """Fetches the actual next game for a specific team via ESPN Team API."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/schedule"
    try:
        data = requests.get(url, timeout=5).json()
        now = datetime.now(pytz.utc)
        
        # Look for the first game with a 'scheduled' status occurring after 'now'
        for event in data.get("events", []):
            game_date = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc)
            if game_date > now:
                competitors = event["competitions"][0]["competitors"]
                # Determine if the team is home or away
                for team in competitors:
                    if team["id"] == team_id:
                        opponent = [t["team"]["displayName"] for t in competitors if t["id"] != team_id][0]
                        venue_type = "home" if team["homeAway"] == "home" else "away"
                        date_str = game_date.astimezone(pytz.timezone('US/Arizona')).strftime("%m/%d")
                        
                        if venue_type == "home":
                            return f"Up Next: {date_str} vs {opponent}."
                        else:
                            return f"Up Next: {date_str} at {opponent}."
    except:
        pass
    return "Up Next: Schedule pending."

# --- 3. AP STORY ENGINE ---
def craft_ap_story(event, sport, league):
    comp = event["competitions"][0]
    home = comp["competitors"][0]
    away = comp["competitors"][1]
    
    # 1. Dateline & Venue Info
    city = comp.get("venue", {}).get("address", {}).get("city", "FIELD")
    state = comp.get("venue", {}).get("address", {}).get("state", "ST")
    dateline = f"{city.upper()}, {state} (AP) — "
    
    # 2. Performance Research (Top Scorer)
    details = ""
    try:
        winner = home if home.get("winner") else away
        leader = winner["leaders"][0]["leaders"][0]
        name = leader["athlete"]["displayName"]
        val = leader["displayValue"]
        stat = winner["leaders"][0].get("displayName", "points").lower()
        details = f"{name} provided a spark with {val} {stat} for the {winner['team']['shortDisplayName']}. "
    except:
        details = f"The {away['team']['shortDisplayName']} and {home['team']['shortDisplayName']} met in a highly anticipated clash. "

    # 3. Dynamic "Up Next" Logic
    # We pull the next game for the 'featured' team (the one on our whitelist)
    # For simplicity, we'll pull it for the winner of this game
    winner_id = home["team"]["id"] if home.get("winner") else away["team"]["id"]
    next_game_blurb = get_up_next(winner_id, sport, league)

    return f"{dateline}{details}{next_game_blurb}"

# --- 4. DATA FETCH & HTML GENERATION (Integrated) ---
def get_espn_data(sport, league, whitelist, seen_ids):
    url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    results = []
    try:
        data = requests.get(url, timeout=10).json()
        for event in data.get("events", []):
            eid = event["id"]
            name = event.get("name", "").lower()
            if any(team in name for team in whitelist) and eid not in seen_ids:
                results.append({
                    "league": league.upper().replace("-", " "),
                    "score": f"{event['competitions'][0]['competitors'][1]['team']['shortDisplayName']} {event['competitions'][0]['competitors'][1].get('score','0')}, {event['competitions'][0]['competitors'][0]['team']['shortDisplayName']} {event['competitions'][0]['competitors'][0].get('score','0')}",
                    "ap_story": craft_ap_story(event, sport, league),
                    "status": event["status"]["type"]["detail"]
                })
                seen_ids.add(eid)
    except: pass
    return results

def main():
    whitelist = get_whitelist()
    all_games, seen = [], set()
    # Adding MLB and NBA back in for the 2026 season context
    leagues = [
        ("basketball", "mens-college-basketball"), 
        ("basketball", "nba"),
        ("baseball", "mlb")
    ]
    
    for s, l in leagues:
        all_games.extend(get_espn_data(s, l, whitelist, seen))

    # Generate HTML (Simplified for this example)
    now = datetime.now().strftime("%I:%M %p")
    print(f"--- THE ARMCHAIR COMMENTATOR ({now}) ---")
    for g in all_games:
        print(f"\n[{g['league']} - {g['status']}]")
        print(f"{g['score']}")
        print(f"{g['ap_story']}")

if __name__ == "__main__":
    main()
