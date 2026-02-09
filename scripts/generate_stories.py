"""
Tempe Torch — Filter & Generator
Applies strict "Bouncer" logic to the game grid.
"""

import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- 1. THE BOUNCER LISTS ---
# Only games matching these criteria get in.

TARGET_STATES = {"CA", "AZ", "IL", "GA", "MD", "DC", "VA", "TX"}

TARGET_INTL = {
    "India", "USA", "United States", "USA Women", "India Women", "United States Women"
}

TARGET_SOCCER_CLUBS = {
    "Fulham", "Leeds", "Leeds United",
    "Leverkusen", "Bayer Leverkusen", "Gladbach", "Borussia Monchengladbach", "St. Pauli",
    "Barcelona", "Real Madrid",
    "PSG", "Paris Saint-Germain"
}

TARGET_CRICKET_LEAGUES = {"ICC", "IPL", "MLC", "Indian Premier League", "Major League Cricket"}

ALWAYS_INCLUDE_LEAGUES = {"NWSL"}

# --- 2. PINNED CONTENT (Your Featured Stories) ---
# (Same as before, abbreviated for clarity)
PINNED_STORIES = [
    {
        "id": "sb-recap-main", "type": "lead", "sport": "NFL • Super Bowl LX",
        "headline": "DEFENSE REIGNS SUPREME", "subhead": "Seahawks dismantle Patriots 29-13...",
        "dateline": "SANTA CLARA, Calif.",
        "body": "The dynasty talk was premature...", "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": { "home": "Seahawks", "home_score": "29", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png", "away": "Patriots", "away_score": "13", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png", "status": "FINAL" }
    },
     {
        "id": "preview-suns-lakers", "type": "sidebar", "sport": "NBA • PREVIEW",
        "headline": "Clash of Styles", "subhead": "Suns host Lakers in pivotal West matchup",
        "body": "Tonight at the Footprint Center...", "game_data": { "home": "Suns", "home_score": "VS", "home_logo": "https://a.espncdn.com/i/teamlogos/nba/500/phx.png", "away": "Lakers", "away_score": "VS", "away_logo": "https://a.espncdn.com/i/teamlogos/nba/500/lal.png", "status": "8:00 PM" }
    }
]

INSIDE_FLAP_DATA = {
    "weather": {"temp": "68°F", "desc": "Clear skies.", "high": "72", "low": "48"},
    "quote": {"text": "Nobody talked about our front seven. I think they're talking now.", "author": "Mike Macdonald"},
    "staff": ["Editor: R. Baral", "Photo: Getty Images"],
    "date": "Monday, February 9, 2026"
}

# --- 3. FILTER LOGIC ---

def is_relevant_game(g):
    """
    The Bouncer Function.
    Returns True ONLY if the game meets the user's strict criteria.
    """
    sport = g.get('sport', '')
    league = g.get('league', '')
    home = g.get('home', '')
    away = g.get('away', '')
    note = g.get('game_note', '')

    # 1. EXCEPTION: All Major Finals
    # We look for keywords in the game note/headline
    if "Final" in note or "Championship" in note:
        # Simple check to ensure it's a "Major" sport (filtering out minor college sports finals if needed)
        # For now, we let all "Finals" through as requested
        return True

    # 2. League Whitelist (NWSL)
    if "NWSL" in league or "NWSL" in sport:
        return True

    # 3. Cricket Whitelist
    if "Cricket" in sport:
        # Check specific leagues
        if any(l in note for l in TARGET_CRICKET_LEAGUES): return True
        # Check teams (India/USA) handled below
    
    # 4. Team Name Checks (Soccer Clubs & Intl Teams)
    targets = TARGET_SOCCER_CLUBS.union(TARGET_INTL)
    if any(t.lower() in home.lower() for t in targets): return True
    if any(t.lower() in away.lower() for t in targets): return True

    # 5. State Location Checks
    # We check if the location string CONTAINS the state code (e.g., "Tempe, AZ")
    h_loc = g.get('home_location', '')
    a_loc = g.get('away_location', '')
    
    for state in TARGET_STATES:
        # We look for " AZ" or ", AZ" to avoid matching "Arkansas" with "AR" inside a word
        if f" {state}" in h_loc or f", {state}" in h_loc: return True
        if f" {state}" in a_loc or f", {state}" in a_loc: return True

    return False

def generate_live_story(game):
    return {
        "id": f"live-{random.randint(10000,99999)}",
        "type": "grid",
        "sport": game['sport'],
        "headline": f"{game['away']} vs {game['home']}",
        "subhead": f"{game['status']}",
        "body": "Live coverage provided by The Tempe Torch.",
        "game_data": game,
        "box_score": None
    }

def main():
    live_stories = []
    
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            
            # --- APPLY FILTER ---
            all_games = raw_data.get("games", [])
            filtered_games = [g for g in all_games if is_relevant_game(g)]
            
            # Convert to stories
            for g in filtered_games:
                # Avoid duplicates with pinned stories
                if g['home'] not in ["Suns", "Seahawks", "Colorado"]:
                    live_stories.append(generate_live_story(g))

    # Combine
    final_stories = PINNED_STORIES + live_stories

    output = {
        "meta": INSIDE_FLAP_DATA,
        "stories": final_stories
    }

    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Filtered {len(all_games)} raw games down to {len(live_stories)} relevant grid items.")

if __name__ == "__main__":
    main()
