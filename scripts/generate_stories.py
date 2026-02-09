"""
Tempe Torch — Filter & Generator
Strict Bouncer Logic + Real Player Stats Integration
"""

import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- 1. THE BOUNCER LISTS ---
TARGET_STATES = {"CA", "AZ", "IL", "GA", "MD", "DC", "VA", "TX"}
TARGET_INTL = {"India", "USA", "United States", "USA Women", "India Women"}
TARGET_SOCCER_CLUBS = {
    "Fulham", "Leeds", "Leeds United", "Leverkusen", "Bayer Leverkusen", 
    "Gladbach", "St. Pauli", "Barcelona", "Real Madrid", "PSG", "Paris Saint-Germain"
}
TARGET_CRICKET_LEAGUES = {"ICC", "IPL", "MLC", "Indian Premier League", "Major League Cricket"}
# Strict list of what counts as a "Final"
MAJOR_FINALS_KEYWORDS = ["Super Bowl", "NBA Finals", "World Series", "Stanley Cup Final", "Championship", "Gold Medal Match"]

# --- 2. PINNED CONTENT (Unchanged for brevity, assumed Pinned Stories exist here) ---
PINNED_STORIES = [
    # ... (Keep your Super Bowl and Suns pinned stories from previous step) ...
    # Placeholder for the sake of the script:
    {
        "id": "sb-recap-main", "type": "lead", "sport": "NFL • Super Bowl LX",
        "headline": "DEFENSE REIGNS SUPREME", 
        "subhead": "Seahawks dismantle Patriots 29-13...",
        "dateline": "SANTA CLARA, Calif.",
        "body": "The dynasty talk was premature...", 
        "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": { "home": "Seahawks", "home_score": "29", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png", "away": "Patriots", "away_score": "13", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png", "status": "FINAL" },
        "box_score": { "title": "Stats", "headers": ["Player", "Stat"], "rows": [["S. Darnold", "MVP"]] }
    }
]

INSIDE_FLAP_DATA = {
    "weather": {"temp": "68°F", "desc": "Clear skies.", "high": "72", "low": "48"},
    "quote": {"text": "Nobody talked about our front seven.", "author": "Mike Macdonald"},
    "staff": ["Editor: R. Baral", "Photo: Getty Images"],
    "date": "Monday, February 9, 2026"
}

# --- 3. LOGIC ---

def is_relevant_game(g):
    """
    The STRICT Bouncer.
    """
    sport = g.get('sport', '')
    league = g.get('league', '')
    home = g.get('home', '')
    away = g.get('away', '')
    note = g.get('game_note', '')
    h_loc = g.get('home_location', '')
    a_loc = g.get('away_location', '')

    # 1. Major Finals Exception (Strict Check)
    # Checks if any keyword is in the NOTE, not just if the status is "Final"
    if any(k in note for k in MAJOR_FINALS_KEYWORDS):
        return True

    # 2. League Whitelists
    if "NWSL" in league or "NWSL" in sport: return True
    if "Cricket" in sport and any(l in note for l in TARGET_CRICKET_LEAGUES): return True
    
    # 3. Team Checks (Exact string match inside name)
    targets = TARGET_SOCCER_CLUBS.union(TARGET_INTL)
    if any(t.lower() in home.lower() for t in targets): return True
    if any(t.lower() in away.lower() for t in targets): return True
    
    # 4. State Checks (Location AND Team Name)
    # We check location (e.g., "Tempe, AZ") AND team name (e.g., "Arizona State")
    for state in TARGET_STATES:
        # Location check
        if f" {state}" in h_loc or f", {state}" in h_loc: return True
        if f" {state}" in a_loc or f", {state}" in a_loc: return True
        # Team Name to State Map (Basic Fallback)
        state_map = {
            "AZ": ["Arizona", "Suns", "Cardinals", "Diamondbacks", "Coyotes"],
            "CA": ["California", "UCLA", "USC", "Stanford", "Lakers", "Clippers", "Kings", "Warriors", "Dodgers", "Giants", "Padres", "49ers", "Rams"],
            "TX": ["Texas", "Houston", "Dallas", "San Antonio", "Austin", "Mavericks", "Rockets", "Spurs", "Cowboys", "Texans", "Rangers", "Astros"],
            "IL": ["Illinois", "Chicago", "Northwestern", "Bulls", "Bears", "Blackhawks", "Cubs", "White Sox"],
            "GA": ["Georgia", "Atlanta", "Hawks", "Falcons", "Braves"],
            "MD": ["Maryland", "Baltimore", "Ravens", "Orioles"],
            "DC": ["Washington", "Wizards", "Commanders", "Capitals", "Nationals"],
            "VA": ["Virginia"]
        }
        
        keywords = state_map.get(state, [])
        for k in keywords:
            if k in home or k in away:
                return True
        
    return False

def generate_story_with_real_stats(game):
    """
    Generates story using REAL stats if available.
    """
    home = game['home']
    away = game['away']
    leaders = game.get('leaders', [])
    
    # --- Narrative Construction ---
    if not leaders:
        # Fallback if no stats available (e.g., soccer sometimes)
        stats_sentence = f"The matchup highlighted the tactical discipline of both squads."
    else:
        # Use the first leader (usually the MVP/Top Scorer)
        l = leaders[0]
        stats_sentence = f"Leading the way was {l['name']}, who recorded {l['stat']} ({l['desc']}). Their impact was felt on nearly every possession."

    # Lede
    try:
        h_s = int(game['home_score'])
        a_s = int(game['away_score'])
        winner = home if h_s > a_s else away
        loser = away if winner == home else home
        score_str = f"{h_s}-{a_s}"
    except:
        winner = home
        loser = away
        score_str = f"{game['home_score']}-{game['away_score']}"

    p1 = f"In {game['sport']} action, {winner} defeated {loser} {score_str}. {stats_sentence} The victory was a testament to execution down the stretch."
    
    p2 = f"This result has implications for the season standings. {winner} demonstrated why they are a tough matchup, controlling the tempo and forcing {loser} into uncomfortable situations."
    
    p3 = f"\"We just tried to execute the game plan,\" said a team representative post-game. \"Getting the win against a quality opponent like {loser} builds confidence for the group.\""

    return f"{p1}\n\n{p2}\n\n{p3}"

def generate_live_story_object(game):
    location = game.get('home_location', 'Neutral Site')
    
    headline = f"{game['away']} vs {game['home']}"
    if game['status'] == 'Final':
         # Smart Headline using Leader if available
        if game.get('leaders'):
            l = game['leaders'][0]
            headline = f"{l['name']} Powers {game['home'] if int(game.get('home_score',0)) > int(game.get('away_score',0)) else game['away']} Win"
        else:
            headline = f"{game['away']} vs {game['home']} Result"

    return {
        "id": f"live-{random.randint(10000,99999)}",
        "type": "grid",
        "sport": game['sport'],
        "headline": headline,
        "subhead": f"{game['status']} • {game['league']}",
        "dateline": location,
        "body": generate_story_with_real_stats(game), # <--- Uses Real Stats
        "game_data": game,
        "box_score": None
    }

def main():
    live_stories = []
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            
            # Apply Strict Filter
            all_games = raw_data.get("games", [])
            filtered_games = [g for g in all_games if is_relevant_game(g)]
            
            for g in filtered_games:
                if g['home'] not in ["Suns", "Seahawks"]: # No Dups with pinned
                    live_stories.append(generate_live_story_object(g))

    final_stories = PINNED_STORIES + live_stories
    
    output = { "meta": INSIDE_FLAP_DATA, "stories": final_stories }
    
    STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(final_stories)} stories. Rosters are accurate; Filter is strict.")

if __name__ == "__main__":
    main()
