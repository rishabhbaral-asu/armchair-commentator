"""
Tempe Torch — 3-Step Data Pipeline
1. SCRAPE: Fetch raw schedule from ESPN.
2. NORMALIZE: Clean up Venue/Team data (fix missing cities).
3. FILTER: The Bouncer (Geofence for locals, Keywords for globals).
"""

import json
import requests
from datetime import datetime, timezone

OUTPUT_PATH = "data/daily_scores.json"
DATE_WINDOW_DAYS = 1 

# --- CONFIGURATION ---

# A. GLOBAL WATCHLIST (Keywords to catch anywhere)
TARGET_KEYWORDS = [
    # LOCALS (Explicit)
    "Suns", "Cardinals", "Diamondbacks", "Coyotes", "ASU", "Arizona State", "Sun Devils", "Mercury",
    # RIVALS / INTEREST
    "Lakers", "Clippers", "Warriors", "Mavericks", "Spurs", "Rockets", "Thunder", "Nuggets",
    "Seahawks", "Patriots", "49ers", "Cowboys", "Chiefs",
    # INTERNATIONAL
    "India", "USA", "Cricket", "ICC", "T20"
]

# B. GEOFENCE (If it happens here, we cover it)
TARGET_CITIES = {"Tempe", "Phoenix", "Glendale", "Scottsdale", "Mesa", "Tucson", "Los Angeles", "Las Vegas"}
TARGET_STATES = {"AZ"}

# C. MAJOR EVENTS (Always cover)
MAJOR_FINALS = ["Super Bowl", "NBA Finals", "World Series", "Stanley Cup Final", "Championship", "Final"]

# D. VENUE RESOLVER (Fixes missing API data)
VENUE_MAP = {
    "Footprint Center": ("Phoenix", "AZ"),
    "Chase Field": ("Phoenix", "AZ"),
    "State Farm Stadium": ("Glendale", "AZ"),
    "Mullett Arena": ("Tempe", "AZ"),
    "Desert Financial Arena": ("Tempe", "AZ"),
    "Sun Devil Stadium": ("Tempe", "AZ"),
    "Mountain America Stadium": ("Tempe", "AZ"),
    "McKale Center": ("Tucson", "AZ"),
    "Madison Square Garden": ("New York", "NY"),
    "Crypto.com Arena": ("Los Angeles", "CA"),
    "SoFi Stadium": ("Inglewood", "CA"),
    "Wankhede Stadium": ("Mumbai", "India"),
    "Narendra Modi Stadium": ("Ahmedabad", "India")
}

def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return None

# --- STEP 1: SCRAPE (Get the Events) ---
def step_1_scrape_schedule():
    print("STEP 1: Scraping ESPN Schedule...")
    raw_events = []
    
    sources = [
        ("football", "nfl"), ("basketball", "nba"), ("football", "college-football"),
        ("basketball", "mens-college-basketball"), ("baseball", "college-baseball"),
        ("cricket", "competitions")
    ]

    for sport, league in sources:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        data = fetch_json(url)
        if not data: continue
        
        for e in data.get("events", []):
            # Attach sport/league for context in later steps
            e["_meta_sport"] = sport
            e["_meta_league"] = league
            raw_events.append(e)
            
    print(f"  -> Found {len(raw_events)} raw events.")
    return raw_events

# --- STEP 2: NORMALIZE (Find Venue/Teams) ---
def step_2_normalize(raw_event):
    """
    Extracts and cleans data so the Filter has an easy job.
    Resolves missing cities using VENUE_MAP.
    """
    # 1. Basic Info
    name = raw_event.get("name", "")
    short_name = raw_event.get("shortName", "")
    search_text = (name + " " + short_name).lower()
    
    # 2. Venue Logic (The Fix)
    comp = raw_event.get("competitions", [{}])[0]
    venue_obj = comp.get("venue", {})
    venue_name = venue_obj.get("fullName", "Unknown Venue")
    
    # Try API address first
    city = venue_obj.get("address", {}).get("city", "")
    state = venue_obj.get("address", {}).get("state", "")
    
    # Fallback to Map
    if not city and venue_name in VENUE_MAP:
        city, state = VENUE_MAP[venue_name]
        
    # 3. Teams
    competitors = comp.get("competitors", [])
    teams = []
    for c in competitors:
        teams.append(c.get("team", {}).get("displayName", ""))
        
    return {
        "id": raw_event["id"],
        "name": name,
        "search_text": search_text,
        "date": raw_event.get("date"),
        "venue": venue_name,
        "city": city,
        "state": state,
        "teams": teams,
        "sport": raw_event["_meta_sport"],
        "league": raw_event["_meta_league"],
        "raw": raw_event # Keep raw for deep fetch if needed
    }

# --- STEP 3: FILTER (The Bouncer) ---
def step_3_filter(candidate):
    """
    Decides if we write a story about this game.
    """
    # 1. Date Check (24hr window)
    try:
        date_str = candidate.get("date", "")
        if date_str:
            if date_str.endswith('Z'): date_str = date_str[:-1]
            dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            if abs((dt - datetime.now(timezone.utc)).days) > DATE_WINDOW_DAYS: 
                return False, "Old Game"
    except:
        pass

    # 2. Major Finals (Always allow)
    if any(k.lower() in candidate["search_text"] for k in MAJOR_FINALS):
        return True, "Major Final"

    # 3. Geofence (The "Local Newspaper" Rule)
    # If it's in our City/State, we cover it.
    if candidate["city"] in TARGET_CITIES:
        return True, f"Geofence Hit: {candidate['city']}"
    if candidate["state"] in TARGET_STATES:
        return True, f"Geofence Hit: {candidate['state']}"

    # 4. Keyword Watchlist (The "Fan Interest" Rule)
    # Catches Lakers in NY, India in London, etc.
    full_text = (candidate["search_text"] + " " + " ".join(candidate["teams"])).lower()
    for k in TARGET_KEYWORDS:
        if k.lower() in full_text:
            return True, f"Keyword Hit: {k}"

    return False, "Irrelevant"

# --- FINAL FETCH (Deep Data) ---
def fetch_deep_data(candidate):
    """
    The survivor of the filter gets the full deep-dive.
    """
    sport = candidate["sport"]
    league = candidate["league"]
    game_id = candidate["id"]
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={game_id}"
    data = fetch_json(url)
    if not data: return None
    
    header = data.get("header", {})
    comp = header.get("competitions", [{}])[0]
    
    # Competitors
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c["homeAway"] == "home"), {})
    away = next((c for c in competitors if c["homeAway"] == "away"), {})
    
    # Leaders
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
        "date": candidate["date"],
        "status": comp.get("status", {}).get("type", {}).get("detail", ""),
        "state": comp.get("status", {}).get("type", {}).get("state", ""),
        "venue": candidate["venue"],
        "location": f"{candidate['city']}, {candidate['state']}" if candidate['city'] else candidate['venue'],
        "odds": data.get("pickcenter", [{}])[0].get("details", "") if "pickcenter" in data else "",
        
        "home": home.get("team", {}).get("displayName", "Home"),
        "home_record": home.get("record", [{}])[0].get("summary", "0-0"),
        "home_rank": home.get("curatedRank", {}).get("current", None),
        "home_score": home.get("score", "0"),
        "home_logo": home.get("team", {}).get("logos", [{}])[0].get("href", ""),
        
        "away": away.get("team", {}).get("displayName", "Away"),
        "away_record": away.get("record", [{}])[0].get("summary", "0-0"),
        "away_rank": away.get("curatedRank", {}).get("current", None),
        "away_score": away.get("score", "0"),
        "away_logo": away.get("team", {}).get("logos", [{}])[0].get("href", ""),
        
        "leaders": leaders
    }

def main():
    # 1. Scrape
    raw_events = step_1_scrape_schedule()
    
    # 2. Normalize
    print("STEP 2: Normalizing Data...")
    candidates = [step_2_normalize(e) for e in raw_events]
    
    # 3. Filter
    print("STEP 3: Filtering (The Bouncer)...")
    final_games = []
    for c in candidates:
        keep, reason = step_3_filter(c)
        if keep:
            print(f"  [KEEP] {c['name']} ({reason})")
            deep = fetch_deep_data(c)
            if deep: final_games.append(deep)
    
    # Save
    output = { "updated": datetime.utcnow().isoformat(), "games": final_games }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"DONE. Saved {len(final_games)} games to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
