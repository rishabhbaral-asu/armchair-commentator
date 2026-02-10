"""
Tempe Torch — Live Narrative Engine
Generates context-aware stories based on Game State (Pre, Live, Final).
"""

import json
import random
from datetime import datetime
from pathlib import Path

SCORES_PATH = Path("data/daily_scores.json")
STORIES_PATH = Path("data/daily_stories.json")

# --- 1. BOUNCER LISTS (Unchanged) ---
TARGET_STATES = {"CA", "AZ", "IL", "GA", "MD", "DC", "VA", "TX"}
TARGET_INTL = {"India", "USA", "United States", "USA Women", "India Women"}
TARGET_SOCCER_CLUBS = {"Fulham", "Leeds", "Leeds United", "Leverkusen", "Bayer Leverkusen", "Gladbach", "St. Pauli", "Barcelona", "Real Madrid", "PSG", "Paris Saint-Germain"}
TARGET_CRICKET_LEAGUES = {"ICC", "IPL", "MLC", "Indian Premier League", "Major League Cricket"}
MAJOR_FINALS = ["Super Bowl", "NBA Finals", "World Series", "Stanley Cup Final", "Championship"]

# --- 2. PINNED CONTENT (Monday Edition) ---
PINNED_STORIES = [
    {
        "id": "sb-recap", "type": "lead", "sport": "NFL • SUPER BOWL LX",
        "headline": "DEFENSE REIGNS SUPREME", "subhead": "Seahawks dismantle Patriots 29-13",
        "dateline": "SANTA CLARA, Calif.", 
        "body": "The dynasty talk was premature. The coronation was cancelled. In a defensive masterclass, the Seattle Seahawks defeated the New England Patriots 29-13 to win Super Bowl LX. Mike Macdonald's defense turned Drake Maye's dream season into a nightmare, recording seven sacks.\n\nSam Darnold was efficient, throwing for 215 yards and two touchdowns. Kenneth Walker III added 112 yards on the ground.",
        "image_url": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
        "game_data": { "home": "Seahawks", "home_score": "29", "home_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png", "away": "Patriots", "away_score": "13", "away_logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png", "status": "FINAL" },
        "box_score": { "title": "Super Bowl MVP", "headers": ["Player", "Stat", "Desc"], "rows": [["S. Darnold", "22/28", "2 TD"], ["K. Walker", "112", "Yards"]] }
    },
    {
        "id": "preview-suns", "type": "sidebar", "sport": "NBA • PREVIEW",
        "headline": "Clash of Styles", "subhead": "Suns host Lakers tonight",
        "dateline": "PHOENIX",
        "body": "Tonight at the Footprint Center, the Suns (32-20) host the Lakers (30-22). Phoenix enters as the league's top mid-range shooting team, while Los Angeles dominates the paint. All eyes will be on the Anthony Davis vs. Jusuf Nurkic matchup inside.",
        "game_data": { "home": "Suns", "home_score": "VS", "home_logo": "https://a.espncdn.com/i/teamlogos/nba/500/phx.png", "away": "Lakers", "away_score": "VS", "away_logo": "https://a.espncdn.com/i/teamlogos/nba/500/lal.png", "status": "8:00 PM" }
    }
]

INSIDE_FLAP_DATA = {
    "weather": {"temp": "65°F", "desc": "Clear.", "high": "72", "low": "48"},
    "quote": {"text": "Tonight, the only ghost out there was the history we just buried.", "author": "Sam Darnold"},
    "staff": ["Editor: R. Baral", "Data: ESPN API"],
    "date": "Monday, February 9, 2026"
}

# --- 3. DYNAMIC NARRATIVE ENGINE ---

def generate_dynamic_narrative(game):
    """
    Writes a story based on the EXACT state of the game.
    """
    home = game.get('home')
    away = game.get('away')
    venue = game.get('venue', 'Neutral Site')
    status = game.get('status', '') # e.g., "Final", "Top 3rd", "10:00 1st"
    state = game.get('state', '')   # pre, in, post
    leaders = game.get('leaders', [])
    
    # Get Scores safely
    try:
        h_s = int(game.get('home_score', 0))
        a_s = int(game.get('away_score', 0))
        margin = h_s - a_s
    except:
        h_s, a_s, margin = 0, 0, 0

    # A. PRE-GAME (The Setup)
    if state == 'pre':
        return (
            f"PREVIEW: The stage is set at {venue} as {home} prepares to host {away}. "
            f"Both teams are looking to make a statement in this matchup. "
            f"Analysts are highlighting the defensive battle as the key factor to watch. "
            f"Tip-off/Kickoff is scheduled for {status}."
        )

    # B. LIVE GAME (The Action)
    if state == 'in':
        # 1. Blowout Scenario
        if abs(margin) >= 15:
            leader = home if margin > 0 else away
            trailer = away if margin > 0 else home
            return (
                f"LIVE: It is all {leader} right now at {venue}. They have opened up a commanding {h_s}-{a_s} lead over {trailer}. "
                f"The offense has been clicking on all cylinders, while {trailer} struggles to find answers on the defensive end. "
                f"Current status: {status}."
            )
        
        # 2. Close Game Scenario
        elif abs(margin) <= 5:
            return (
                f"LIVE: We have a thriller developing at {venue}! {home} and {away} are trading blows in a tight contest. "
                f"The score is currently {h_s}-{a_s} as we play through the {status}. "
                f"Every possession matters right now as both teams look to seize momentum."
            )
        
        # 3. Standard Live Update
        else:
            leader = home if margin > 0 else away
            return (
                f"LIVE: Action is underway at {venue}. {leader} currently holds the advantage with a {h_s}-{a_s} lead. "
                f"There is still plenty of time left in the {status} for things to change, but {leader} is controlling the tempo so far."
            )

    # C. FINAL (The Recap)
    if state == 'post':
        winner = home if h_s > a_s else away
        loser = away if winner == home else home
        
        # Stat Line Logic
        stat_txt = "The team relied on a balanced attack to secure the victory."
        if leaders:
            l = leaders[0]
            stat_txt = f"They were sparked by {l['name']}, who finished with {l['stat']} ({l['desc']})."

        # Margin Logic
        if abs(margin) > 15:
            return (
                f"FINAL: {winner} dominated {loser} {h_s}-{a_s} at {venue}. "
                f"The game was effectively decided early, as {winner} surged ahead and never looked back. {stat_txt} "
                f"This result serves as a statement win for the squad."
            )
        elif abs(margin) <= 3:
            return (
                f"FINAL: In a game that went down to the wire, {winner} edged past {loser} {h_s}-{a_s}. "
                f"Fans at {venue} witnessed a classic that wasn't decided until the final moments. {stat_txt} "
                f"{loser} will look back at missed opportunities down the stretch."
            )
        else:
            return (
                f"FINAL: {winner} defeated {loser} {h_s}-{a_s} in {game['sport']} action at {venue}. "
                f"After a competitive start, {winner} executed down the stretch to pull away. {stat_txt} "
                f"The victory improves their standing as they look ahead to their next matchup."
            )

    return "Updates to follow."

def generate_grid_item(game):
    return {
        "id": f"game-{game.get('game_id', random.randint(1000,9999))}",
        "type": "grid",
        "sport": game['sport'],
        "headline": f"{game['away']} vs {game['home']}",
        "subhead": game['status'],
        "dateline": game['venue'],
        "body": generate_dynamic_narrative(game), # <--- The new engine
        "game_data": game,
        "box_score": None
    }

def main():
    live_stories = []
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            raw_data = json.load(f)
            # The fetcher has already done the heavy filtering
            for g in raw_data.get("games", []):
                # Simple Dedupe against pinned content
                if g['home'] not in ["Seahawks", "Suns"]:
                    live_stories.append(generate_grid_item(g))

    final_stories = PINNED_STORIES + live_stories
    output = { "meta": INSIDE_FLAP_DATA, "stories": final_stories }
    
    with open(STORIES_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(final_stories)} dynamic stories based on live states.")

if __name__ == "__main__":
    main()
