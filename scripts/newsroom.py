"""
THE TEMPE TORCH — NEWSROOM ENGINE
---------------------------------
Automated Pipeline:
1. FETCH: Scrapes ESPN for live scores & schedules.
2. FILTER: Applies Geofence (AZ/Local) & Keyword Watchlist.
3. WRITE: Generates AP-Style stories with narrative context.
4. PUBLISH: Updates 'daily_stories.json' for the frontend.
"""

import json
import time
import os
import random
import requests
from datetime import datetime, timezone
from pathlib import Path

# --- CONFIGURATION ---
SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")
REFRESH_RATE_MINUTES = 10

# 1. GEOFENCE (Local Coverage)
TARGET_CITIES = {"Tempe", "Phoenix", "Glendale", "Scottsdale", "Mesa", "Tucson", "Los Angeles", "Las Vegas", "New York"}
TARGET_STATES = {"AZ"}

# 2. WATCHLIST (Global Interest)
TARGET_KEYWORDS = [
    "Suns", "Cardinals", "Diamondbacks", "Coyotes", "ASU", "Arizona State", "Sun Devils", "Mercury",
    "Lakers", "Clippers", "Warriors", "Mavericks", "Spurs", "Rockets", "Thunder", "Nuggets",
    "Seahawks", "Patriots", "49ers", "Cowboys", "Chiefs",
    "India", "USA", "Cricket", "ICC", "T20"
]

# 3. EVENTS
MAJOR_FINALS = ["Super Bowl", "NBA Finals", "World Series", "Stanley Cup Final", "Championship", "Final"]

# 4. VENUE MAP (Fixes missing API data)
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
    "Wankhede Stadium": ("Mumbai", "India")
}

# --- PART 1: THE FETCHER ---

def fetch_json(url):
    try:
        r = requests.get(url, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def step_1_scrape():
    print("  [1/3] Scraping ESPN...")
    raw = []
    # Added Cricket specifically
    sources = [
        ("football", "nfl"), ("basketball", "nba"), ("football", "college-football"), 
        ("basketball", "mens-college-basketball"), ("cricket", "competitions")
    ]
    for sport, league in sources:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        data = fetch_json(url)
        if data:
            for e in data.get("events", []):
                e["_meta"] = {"sport": sport, "league": league}
                raw.append(e)
    return raw

def step_2_filter(events):
    print("  [2/3] Filtering & Geofencing...")
    kept_games = []
    
    for e in events:
        # Normalize Data
        name = e.get("name", "")
        comp = e.get("competitions", [{}])[0]
        venue = comp.get("venue", {})
        
        # Venue Resolution (The Fix)
        city = venue.get("address", {}).get("city", "")
        state = venue.get("address", {}).get("state", "")
        if not city and venue.get("fullName") in VENUE_MAP:
            city, state = VENUE_MAP[venue.get("fullName")]
            
        # Search Text
        search_text = (name + " " + e.get("shortName", "")).lower()
        teams = [c.get("team", {}).get("displayName", "") for c in comp.get("competitors", [])]
        full_text = (search_text + " " + " ".join(teams)).lower()

        # The Bouncer Logic
        is_relevant = False
        if any(k.lower() in search_text for k in MAJOR_FINALS): is_relevant = True
        elif city in TARGET_CITIES or state in TARGET_STATES: is_relevant = True
        else:
            for k in TARGET_KEYWORDS:
                if k.lower() in full_text: is_relevant = True
        
        if is_relevant:
            # Deep Fetch for Stats
            sport, league = e["_meta"]["sport"], e["_meta"]["league"]
            deep_url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary?event={e['id']}"
            deep = fetch_json(deep_url)
            if deep:
                kept_games.append(parse_game_data(deep, sport, league, city, state))
                
    return kept_games

def parse_game_data(data, sport, league, city, state):
    header = data.get("header", {})
    comp = header.get("competitions", [{}])[0]
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c["homeAway"] == "home"), {})
    away = next((c for c in competitors if c["homeAway"] == "away"), {})
    
    leaders = []
    if "leaders" in comp:
        for l in comp["leaders"]:
            if l.get("leaders"):
                ath = l["leaders"][0]
                leaders.append(f"{ath['athlete']['displayName']} ({ath['displayValue']})")

    return {
        "game_id": header.get("id"),
        "sport": f"{sport.upper()} • {league.upper()}",
        "date": comp.get("date"),
        "status": comp.get("status", {}).get("type", {}).get("detail", ""),
        "state": comp.get("status", {}).get("type", {}).get("state", ""), # pre/in/post
        "venue": data.get("gameInfo", {}).get("venue", {}).get("fullName", "Stadium"),
        "location": f"{city}, {state}" if city else "Neutral Site",
        "home": home.get("team", {}).get("displayName", "Home"),
        "home_score": home.get("score", "0"),
        "home_rec": home.get("record", [{}])[0].get("summary", ""),
        "home_rank": home.get("curatedRank", {}).get("current", 99),
        "away": away.get("team", {}).get("displayName", "Away"),
        "away_score": away.get("score", "0"),
        "away_rec": away.get("record", [{}])[0].get("summary", ""),
        "away_rank": away.get("curatedRank", {}).get("current", 99),
        "odds": data.get("pickcenter", [{}])[0].get("details", "") if data.get("pickcenter") else "",
        "leaders": leaders
    }

# --- PART 2: THE WRITER ---

# PINNED CONTENT (The Gold Standard Examples)
PINNED_STORIES = [
    {
        "id": "sb-recap", "type": "lead", "sport": "NFL • SUPER BOWL LX",
        "headline": "Seahawks 29, Patriots 13", 
        "subhead": "Seattle defense dominates New England to win Super Bowl LX",
        "dateline": "SANTA CLARA, Calif.", 
        "body": "The dynasty talk was premature. The coronation was cancelled. In a defensive masterclass that stifled one of the league's most potent offenses, the Seattle Seahawks defeated the New England Patriots 29-13 to win Super Bowl LX. Mike Macdonald's defense turned Drake Maye's dream season into a nightmare, recording seven sacks and forcing three turnovers.\n\n\"Nobody talked about our front seven,\" Macdonald said postgame. \"I think they're talking now.\"\n\nTOP PERFORMERS: Kenneth Walker III (SEA) 112 Rush Yds. Sam Darnold (SEA) 215 Yds, 2 TD.",
        "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": { "home": "Seahawks", "home_score": "29", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png", "away": "Patriots", "away_score": "13", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png", "status": "FINAL" },
        "box_score": None
    },
    {
        "id": "cricket-ind-usa", "type": "sidebar", "sport": "CRICKET • T20 WC",
        "headline": "India def. USA (7 wkts)",
        "subhead": "Yadav (84*) rescues hosts after early collapse",
        "dateline": "MUMBAI", 
        "body": "The cricketing world nearly witnessed the upset of the century. Chasing a modest target of 133, the powerhouse Indian lineup crumbled to 34/4 inside the powerplay, silenced by a spirited American bowling attack.\n\nEnter Suryakumar Yadav. The captain played a knock for the ages, abandoning his usual flamboyant style for a gritty, unbeaten 84 off 48 balls. He anchored partnerships with the lower order, slowly shifting the momentum back to the hosts before exploding in the final overs to secure victory by 7 wickets.\n\nTOP PERFORMERS: Suryakumar Yadav (IND) 84* (48). Arshdeep Singh (IND) 4/18.",
        "game_data": { "home": "India", "home_score": "161/3", "home_logo": "https://upload.wikimedia.org/wikipedia/en/4/41/Flag_of_India.svg", "away": "USA", "away_score": "132/8", "away_logo": "https://upload.wikimedia.org/wikipedia/commons/a/a4/Flag_of_the_United_States.svg", "status": "FINAL" },
        "box_score": None
    }
]

def generate_narrative(g):
    # 1. Context (Clash of Titans / David vs Goliath)
    context = ""
    if g['home_rank'] != 99 and g['away_rank'] != 99:
        context = f"A heavyweight clash features No. {g['away_rank']} {g['away']} visiting No. {g['home_rank']} {g['home']}."
    else:
        context = f"The {g['home']} look to defend their turf against the visiting {g['away']}."

    # 2. Bottom Line (The Hook)
    bottom_line = ""
    if g['state'] == 'pre':
        bottom_line = f"BOTTOM LINE: The {g['home']} ({g['home_rec']}) host the {g['away']} ({g['away_rec']}) in a pivotal matchup."
        if g['odds']: bottom_line += f" {g['home']} are favored by {g['odds']}."
    elif g['state'] == 'in':
        bottom_line = f"BOTTOM LINE: Live action from {g['venue']} as {g['home']} and {g['away']} trade blows."
    else:
        try:
            h_s, a_s = int(g['home_score']), int(g['away_score'])
            winner = g['home'] if h_s > a_s else g['away']
            bottom_line = f"BOTTOM LINE: The {winner} make a statement with a {h_s}-{a_s} victory."
        except:
             bottom_line = f"BOTTOM LINE: {g['home']} vs {g['away']} - Final."

    # 3. Performers
    stats = " ".join(g['leaders'][:2]) if g['leaders'] else "Stats to follow."
    
    return f"{g['location'].upper()} — {g['away']} vs. {g['home']}\n{g['venue']}; {g['status']}\n\n{bottom_line}\n\n{context}\n\nTOP PERFORMERS: {stats}"

def step_3_publish(games):
    print("  [3/3] Writing Stories...")
    stories = []
    
    for g in games:
        if g['home'] == "Seahawks": continue 
        if g['home'] == "India" and g['away'] == "USA": continue
        
        story = {
            "id": f"game-{g['game_id']}",
            "type": "grid",
            "sport": g['sport'],
            "headline": f"{g['away']} vs {g['home']}",
            "subhead": g['status'],
            "dateline": g['location'],
            "body": generate_narrative(g),
            "game_data": g,
            "box_score": None
        }
        stories.append(story)

    # Merge
    final_output = {
        "meta": {
            "weather": {"temp": "72°F", "desc": "Sunny"},
            "quote": {"text": "Nobody talked about our front seven. I think they're talking now.", "author": "Mike Macdonald"},
            "staff": ["Associated Press", "Tempe Torch Wire"],
            "date": datetime.now().strftime("%A, %B %d, %Y"),
            "last_updated": datetime.now().strftime("%I:%M %p")
        },
        "stories": PINNED_STORIES + stories
    }
    
    # Ensure directory exists
    STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(STORIES_PATH, "w") as f:
        json.dump(final_output, f, indent=2)
    print(f"  -> PUBLISHED: {len(stories)} new stories to {STORIES_PATH}")

# --- MAIN LOOP ---

def main():
    print(f"TEMPE TORCH NEWSROOM IS LIVE")
    
    # Check Environment
    is_github_action = os.environ.get('CI') == 'true'

    if is_github_action:
        print("--- RUNNING IN CI MODE (SINGLE PASS) ---")
        raw_events = step_1_scrape()
        live_games = step_2_filter(raw_events)
        step_3_publish(live_games)
        print("--- CI PASS COMPLETE ---")
    else:
        print(f"--- RUNNING IN LOCAL MODE (LOOPING) ---")
        print(f"Updating every {REFRESH_RATE_MINUTES} minutes...")
        try:
            while True:
                print(f"\n--- STARTING NEWS CYCLE: {datetime.now().strftime('%H:%M:%S')} ---")
                raw_events = step_1_scrape()
                live_games = step_2_filter(raw_events)
                step_3_publish(live_games)
                print(f"--- SLEEPING ---")
                time.sleep(REFRESH_RATE_MINUTES * 60)
        except KeyboardInterrupt:
            print("\nNewsroom shutting down.")

if __name__ == "__main__":
    main()
