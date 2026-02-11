"""
Tempe Torch — 3-Step Data Pipeline (Live Newsroom Edition)
Now runs continuously to keep the 'paper' fresh.
"""

import json
import time
import requests
from datetime import datetime, timezone

OUTPUT_PATH = "data/daily_scores.json"
DATE_WINDOW_DAYS = 1 
REFRESH_RATE_MINUTES = 10  # <--- NEW: Updates every 10 mins

# --- CONFIGURATION (Same as before) ---
TARGET_KEYWORDS = [
    "Suns", "Cardinals", "Diamondbacks", "Coyotes", "ASU", "Arizona State", "Sun Devils", "Mercury",
    "Lakers", "Clippers", "Warriors", "Mavericks", "Spurs", "Rockets", "Thunder", "Nuggets",
    "Seahawks", "Patriots", "49ers", "Cowboys", "Chiefs",
    "India", "USA", "Cricket", "ICC", "T20"
]

TARGET_CITIES = {"Tempe", "Phoenix", "Glendale", "Scottsdale", "Mesa", "Tucson", "Los Angeles", "Las Vegas"}
TARGET_STATES = {"AZ"}
MAJOR_FINALS = ["Super Bowl", "NBA Finals", "World Series", "Stanley Cup Final", "Championship", "Final"]

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

# --- STEP 1: SCRAPE ---
def step_1_scrape_schedule():
    print(f"--- NEWS CYCLE START: {datetime.now().strftime('%H:%M:%S')} ---")
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
            e["_meta_sport"] = sport
            e["_meta_league"] = league
            raw_events.append(e)
    return raw_events

# --- STEP 2: NORMALIZE ---
def step_2_normalize(raw_event):
    comp = raw_event.get("competitions", [{}])[0]
    venue_obj = comp.get("venue", {})
    venue_name = venue_obj.get("fullName", "Unknown Venue")
    city = venue_obj.get("address", {}).get("city", "")
    state = venue_obj.get("address", {}).get("state", "")
    
    if not city and venue_name in VENUE_MAP:
        city, state = VENUE_MAP[venue_name]
        
    teams = [c.get("team", {}).get("displayName", "") for c in comp.get("competitors", [])]
    
    return {
        "id": raw_event["id"],
        "name": raw_event.get("name", ""),
        "search_text": (raw_event.get("name", "") + " " + raw_event.get("shortName", "")).lower(),
        "date": raw_event.get("date"),
        "venue": venue_name,
        "city": city,
        "state": state,
        "teams": teams,
        "sport": raw_event["_meta_sport"],
        "league": raw_event["_meta_league"]
    }

# --- STEP 3: FILTER ---
def step_3_filter(candidate):
    try:
        date_str = candidate.get("date", "")
        if date_str:
            if date_str.endswith('Z'): date_str = date_str[:-1]
            dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            if abs((dt - datetime.now(timezone.utc)).days) > DATE_WINDOW_DAYS: 
                return False, "Old Game"
    except: pass

    if any(k.lower() in candidate["search_text"] for k in MAJOR_FINALS): return True, "Major Final"
    if candidate["city"] in TARGET_CITIES: return True, f"Geofence Hit: {candidate['city']}"
    if candidate["state"] in TARGET_STATES: return True, f"Geofence Hit: {candidate['state']}"

    full_text = (candidate["search_text"] + " " + " ".join(candidate["teams"])).lower()
    for k in TARGET_KEYWORDS:
        if k.lower() in full_text: return True, f"Keyword Hit: {k}"

    return False, "Irrelevant"

# --- DEEP DATA FETCH ---
def fetch_deep_data(candidate):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{candidate['sport']}/{candidate['league']}/summary?event={candidate['id']}"
    data = fetch_json(url)
    if not data: return None
    
    comp = data.get("header", {}).get("competitions", [{}])[0]
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c["homeAway"] == "home"), {})
    away = next((c for c in competitors if c["homeAway"] == "away"), {})
    
    leaders = []
    if "leaders" in comp:
        for l in comp["leaders"]:
            if "leaders" in l and len(l["leaders"]) > 0:
                ath = l["leaders"][0]
                leaders.append({
                    "name": ath["athlete"]["displayName"],
                    "stat": ath["displayValue"],
                    "desc": l["displayName"],
                    "team": l.get("team", {}).get("abbreviation", "")
                })

    return {
        "game_id": candidate["id"],
        "sport": candidate["sport"].upper(),
        "league": candidate["league"],
        "date": candidate["date"],
        "status": comp.get("status", {}).get("type", {}).get("detail", ""),
        "state": comp.get("status", {}).get("type", {}).get("state", ""),
        "venue": candidate["venue"],
        "location": f"{candidate['city']}, {candidate['state']}" if candidate['city'] else candidate['venue'],
        "home": home.get("team", {}).get("displayName", "Home"),
        "home_score": home.get("score", "0"),
        "home_logo": home.get("team", {}).get("logos", [{}])[0].get("href", ""),
        "away": away.get("team", {}).get("displayName", "Away"),
        "away_score": away.get("score", "0"),
        "away_logo": away.get("team", {}).get("logos", [{}])[0].get("href", ""),
        "leaders": leaders
    }

def run_news_cycle():
    """Single execution of the pipeline"""
    raw_events = step_1_scrape_schedule()
    candidates = [step_2_normalize(e) for e in raw_events]
    
    final_games = []
    print("  -> Filtering...")
    for c in candidates:
        keep, reason = step_3_filter(c)
        if keep:
            deep = fetch_deep_data(c)
            if deep: final_games.append(deep)
    
    output = { "updated": datetime.utcnow().isoformat(), "games": final_games }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  -> PUBLISHED: {len(final_games)} stories updated in {OUTPUT_PATH}")

def main():
    print(f"TEMPE TORCH NEWSROOM IS LIVE (Updates every {REFRESH_RATE_MINUTES} mins)")
    print("Press Ctrl+C to stop the presses.")
    
    try:
        while True:
            run_news_cycle()
            print(f"  -> Sleeping for {REFRESH_RATE_MINUTES} minutes...")
            time.sleep(REFRESH_RATE_MINUTES * 60)
    except KeyboardInterrupt:
        print("\nNewsroom shutting down. Goodbye!")

if __name__ == "__main__":
    main()
